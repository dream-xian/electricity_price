"""出图。中文用 PingFang SC；图一律存 reports/figures/ 且带编号。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import FIG_DIR

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def save(fig, name):
    path = FIG_DIR / name
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[plots] {path}")
    return path


def fig_price_series(df, market, name="fig01_price_series.png"):
    g = df[df.market_type == market].sort_values("delivery_time")
    fig, ax = plt.subplots(figsize=(14, 3.6))
    ax.plot(g["delivery_time"], g["price"], lw=0.4, color="#c0392b")
    ax.set_title(f"{market} 全期价格 (n={len(g)})")
    ax.set_ylabel("CNY/MWh")
    return save(fig, name)


def fig_daily_profile(df, name="fig02_daily_profile.png"):
    prof = df.groupby(["market_type", "period_id"])["price"].agg(["mean", "std"]).reset_index()
    fig, ax = plt.subplots(figsize=(12, 4))
    for m, style in (("DA", "-"), ("RT", "--")):
        p = prof[prof.market_type == m]
        ax.plot(p["period_id"], p["mean"], style, lw=1.6, label=f"{m} 均值")
        ax.fill_between(p["period_id"], p["mean"] - p["std"], p["mean"] + p["std"], alpha=0.12)
    ax.set_xlabel("period_id (1~96)")
    ax.set_ylabel("CNY/MWh")
    ax.set_title("日内 96 点均值 ± 1 标准差")
    ax.legend()
    return save(fig, name)


def fig_dist(df, name="fig03_price_dist.png"):
    fig, ax = plt.subplots(figsize=(9, 4))
    for m in ("DA", "RT"):
        df.loc[df.market_type == m, "price"].hist(bins=120, alpha=0.55, ax=ax, label=m)
    ax.set_yscale("log")
    ax.set_title("价格分布（对数纵轴，看右尾与负价）")
    ax.legend()
    return save(fig, name)


def fig_split(spans, market, name="fig04_split.png"):
    order = ["train", "valid", "test"]
    colors = {"train": "#2c6fbb", "valid": "#e6a23c", "test": "#c0392b"}
    fig, ax = plt.subplots(figsize=(11, 2.6))
    for i, k in enumerate(order):
        lo, hi, n = spans[k]
        if n:
            ax.barh(0, (hi - lo).days + 1, left=lo, height=0.5, color=colors[k], label=f"{k} ({n} 行)")
    ax.set_yticks([])
    ax.set_title(f"{market} 时间切分（白色缝隙 = 1 天 embargo）")
    ax.legend(loc="lower right")
    return save(fig, name)


def fig_error_by_period(res, market, name="fig07_error_by_period.png"):
    s = res.groupby("period_id")["abs_err"].mean()
    fig, ax = plt.subplots(figsize=(12, 3.6))
    ax.plot(s.index, s.values, lw=1.5, color="#7F77DD")
    ax.set_xlabel("period_id")
    ax.set_ylabel("MAE")
    ax.set_title(f"{market} 分时段平均绝对误差")
    return save(fig, name)


def fig_pred_vs_true(res, day, market, name="fig09_worst_day.png"):
    d = res[res["trade_date"] == day].sort_values("delivery_time")
    fig, ax = plt.subplots(figsize=(12, 3.6))
    ax.plot(d["delivery_time"], d["y"], lw=1.6, label="真实", color="#2c6fbb")
    ax.plot(d["delivery_time"], d["yhat"], lw=1.6, ls="--", label="预测", color="#c0392b")
    ax.set_title(f"{market} 误差最大单日 {np.datetime64(day, 'D')}")
    ax.set_ylabel("CNY/MWh")
    ax.legend()
    return save(fig, name)
