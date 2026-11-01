"""端到端：体检 → 特征 → 切分 → 基准+模型 → 对比表 → 存模型。"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import joblib
import numpy as np
import pandas as pd

import config as C
import data_io
import evaluate
import features as F
import models as M
import plots
import split as S


def run_market(df, market, h, model_names):
    print(f"\n===== {market} / h={h} =====")
    d = F.build_features(data_io.for_market(df, market), h=h)
    parts, spans = S.time_split(d)
    train, valid, test = parts["train"], parts["valid"], parts["test"]
    for k, v in spans.items():
        print(f"  {k:5s}: {str(v[0])[:10]} → {str(v[1])[:10]}  ({v[2]} 行)")

    Xtr, ytr = train[F.FEATURES], train["y"]
    Xva, yva = valid[F.FEATURES], valid["y"]
    Xte, yte = test[F.FEATURES], test["y"]

    prof = M.profile_table(train)
    mu = float(ytr.mean())

    rows, preds = [], {}
    for name, pred in [
        ("naive_mean", M.naive_mean(test, mu)),
        ("naive_profile", M.naive_profile(test, prof)),
        ("naive_lag0", M.naive_lag0(test)),
        ("naive_yday", M.naive_yday(test)),
        ("naive_lag1", M.naive_lag1(test)),
    ]:
        rows.append({"market": market, "h": h, "model": name, "fit_s": 0.0,
                     **evaluate.metrics(yte, pred)})
        preds[name] = pred

    fitted = {}
    for name in model_names:
        est = M.make_model(name)
        t0 = time.time()
        est.fit(Xtr, ytr)
        fit_s = time.time() - t0
        pred = est.predict(Xte)
        vpred = est.predict(Xva)
        vmae = evaluate.metrics(yva, vpred)["mae"]
        rows.append({"market": market, "h": h, "model": name, "fit_s": round(fit_s, 1),
                     **evaluate.metrics(yte, pred)})
        preds[name] = pred
        fitted[name] = est
        print(f"  [{name}] valid MAE={vmae:.1f}  test MAE={rows[-1]['mae']:.1f}  ({fit_s:.1f}s)")

    res = pd.DataFrame(rows).sort_values("mae")
    print(res.to_string(index=False))

    # 落盘：对比表
    out = C.TAB_DIR / f"model_comparison_{market}_h{h}.csv"
    res.to_csv(out, index=False)

    # 落盘：主模型 + 元数据
    best_name = min(fitted, key=lambda k: evaluate.metrics(yte, preds[k])["mae"])
    best = fitted[best_name]
    tag = f"{best_name}_{market.lower()}_h{h}"
    joblib.dump({"model": best, "features": F.FEATURES, "market": market, "h": h},
                C.MODEL_DIR / f"{tag}.joblib")
    print(f"  [save] {C.MODEL_DIR / f'{tag}.joblib'}")

    base = res[res.model == "naive_lag0"].iloc[0]
    meta = {
        "model": type(best).__name__,
        "market": market, "horizon": h,
        "features": F.FEATURES,
        "params": C.RF_PARAMS if best_name == "rf" else C.GBDT_PARAMS,
        "seed": C.SEED,
        "train_range": [str(spans["train"][0])[:10], str(spans["train"][1])[:10]],
        "test_range": [str(spans["test"][0])[:10], str(spans["test"][1])[:10]],
        "metrics": {k: round(v, 3) for k, v in evaluate.metrics(yte, preds[best_name]).items()},
        "baseline": {"name": "naive_lag0", "mae": round(float(base["mae"]), 3),
                     "rmse": round(float(base["rmse"]), 3)},
        "env": "electricity-price (Python 3.12)",
        "git_tag": "model-v1.0",
    }
    (C.MODEL_DIR / f"{tag}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")

    # 图
    plots.fig_split(spans, market, f"fig04_split_{market}.png")
    plots.fig_error_by_period(evaluate.add_residuals(test, preds[best_name]), market,
                              f"fig07_error_by_period_{market}.png")

    worst_day = (evaluate.add_residuals(test, preds[best_name])
                 .groupby("trade_date")["abs_err"].mean().idxmax())
    plots.fig_pred_vs_true(evaluate.add_residuals(test, preds[best_name]), worst_day, market,
                           f"fig09_worst_day_{market}.png")
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--market", default="both", choices=["DA", "RT", "both"])
    p.add_argument("--h", type=int, default=C.HORIZON_MAIN)
    p.add_argument("--model", default="ridge,rf,gbdt")
    args = p.parse_args()

    df = data_io.load_raw()
    print(data_io.check_data(df).to_string())

    plots.fig_price_series(df, "DA")
    plots.fig_daily_profile(df)
    plots.fig_dist(df)

    markets = C.MARKETS if args.market == "both" else [args.market]
    names = [s.strip() for s in args.model.split(",") if s.strip()]
    allres = pd.concat([run_market(df, m, args.h, names) for m in markets])
    allres.to_csv(C.TAB_DIR / f"model_comparison_all_h{args.h}.csv", index=False)
    print("\n", allres.sort_values(["market", "mae"]).to_string(index=False))


if __name__ == "__main__":
    main()
