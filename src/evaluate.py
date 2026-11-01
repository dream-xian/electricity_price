"""指标、误差分解、成对 bootstrap 显著性检验。"""
import numpy as np
import pandas as pd


def metrics(y, yhat) -> dict:
    y = np.asarray(y, float)
    yhat = np.asarray(yhat, float)
    err = yhat - y
    return {
        "mae": float(np.abs(err).mean()),
        "rmse": float(np.sqrt((err ** 2).mean())),
        "wape": float(np.abs(err).sum() / np.abs(y).sum()),   # 有负价，不能用 MAPE
    }


def add_residuals(d: pd.DataFrame, yhat) -> pd.DataFrame:
    out = d.copy()
    out["yhat"] = np.asarray(yhat, float)
    out["err"] = out["yhat"] - out["y"]
    out["abs_err"] = out["err"].abs()
    return out


def error_by_period(res): return res.groupby("period_id")["abs_err"].mean()
def error_by_dow(res):    return res.groupby("dow")["abs_err"].mean()


def error_by_bucket(res, q=10):
    b = pd.qcut(res["y"], q, labels=False, duplicates="drop")
    return res.groupby(b)["abs_err"].agg(["mean", "count"])


def error_by_vol(res, q=5):
    b = pd.qcut(res["roll_std_96"], q, labels=False, duplicates="drop")
    return res.groupby(b)["abs_err"].agg(["mean", "count"])


def bootstrap_diff(e1, e2, n=2000, seed=42):
    """成对 bootstrap：两个模型逐样本绝对误差之差是否显著不为 0。"""
    rng = np.random.default_rng(seed)
    d = np.abs(np.asarray(e1, float)) - np.abs(np.asarray(e2, float))
    bs = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(n)])
    return float(d.mean()), tuple(float(x) for x in np.percentile(bs, [2.5, 97.5]))
