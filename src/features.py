"""特征工程。铁律：先分组 → 再排序 → 再 shift；rolling 一律先 shift(1)。"""
import numpy as np
import pandas as pd

LAGS = (0, 1, 2, 4, 96, 192)

FEATURES = [
    "lag0", "lag1", "lag2", "lag4", "lag96", "lag192",
    "roll_mean_4", "roll_mean_96", "roll_std_96", "roll_max_96", "lag96_diff",
    "period_id", "period_sin", "period_cos", "dow", "is_weekend",
]
KEYS = ["trade_date", "delivery_time", "period_id"]


def build_features(market_df: pd.DataFrame, h: int = 1) -> pd.DataFrame:
    """单市场构造特征。

    行 = 预测起点 t0（本行时刻的价格已出清、可用）；y = price.shift(-h) 是目标。
    lag0 是 t0 时刻最新可得的价，lag1 是再往前一格，以此类推。
    因此 h=1 时 lag0 才是"上一时段价格"，是真正的 1 步惯性基准。
    """
    d = market_df.sort_values("delivery_time").reset_index(drop=True).copy()

    d["y"] = d["price"].shift(-h)

    for k in LAGS:
        d[f"lag{k}"] = d["price"].shift(k)

    past = d["price"].shift(1)                      # 排除当期，防目标泄漏
    d["roll_mean_4"] = past.rolling(4, min_periods=4).mean()
    d["roll_mean_96"] = past.rolling(96, min_periods=96).mean()
    d["roll_std_96"] = past.rolling(96, min_periods=96).std()
    d["roll_max_96"] = past.rolling(96, min_periods=96).max()
    d["lag96_diff"] = d["lag96"] - d["lag192"]

    t = d["delivery_time"]
    d["hour"] = t.dt.hour
    d["dow"] = t.dt.dayofweek
    d["is_weekend"] = (d["dow"] >= 5).astype(int)
    d["period_sin"] = np.sin(2 * np.pi * d["period_id"] / 96)
    d["period_cos"] = np.cos(2 * np.pi * d["period_id"] / 96)

    before = len(d)
    d = d.dropna(subset=FEATURES + ["y"]).reset_index(drop=True)
    print(f"[features] h={h} 丢弃 {before - len(d)} 行（lag96 热身 + 末尾 {h} 行），保留 {len(d)}")
    return d


def Xy(d: pd.DataFrame):
    return d[FEATURES], d["y"]
