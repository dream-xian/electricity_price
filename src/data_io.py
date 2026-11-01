"""读取与数据体检。原始 CSV 只读，任何加工都在内存里做。"""
import pandas as pd

from config import DATA


def load_raw(path=DATA) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["delivery_time"] = (
        pd.to_datetime(df["delivery_time"], utc=True).dt.tz_convert("Asia/Shanghai")
    )
    return df.sort_values(["market_type", "delivery_time"]).reset_index(drop=True)


def for_market(df: pd.DataFrame, market: str) -> pd.DataFrame:
    g = df[df["market_type"] == market]
    return g.sort_values("delivery_time").reset_index(drop=True)


def check_data(df: pd.DataFrame) -> pd.DataFrame:
    """六项体检，返回一张表（直接进报告第 2 章）。"""
    rows = []
    for m, g in df.groupby("market_type"):
        g = g.sort_values("delivery_time")
        per_day = g.groupby("trade_date").size()
        gap = g["delivery_time"].diff().dropna()
        expect_pid = g["delivery_time"].dt.hour * 4 + g["delivery_time"].dt.minute // 15 + 1
        rows.append({
            "rows": len(g),
            "days": g["trade_date"].nunique(),
            "date_min": g["trade_date"].min().date(),
            "date_max": g["trade_date"].max().date(),
            "per_day_values": sorted(per_day.unique().tolist()),
            "dup_ts": int(g.duplicated("delivery_time").sum()),
            "na_price": int(g["price"].isna().sum()),
            "gap_not_15min": int((gap != pd.Timedelta("15min")).sum()),
            "pid_mismatch": int((expect_pid != g["period_id"]).sum()),
            "neg_price": int((g["price"] < 0).sum()),
            "ge_1000": int((g["price"] >= 1000).sum()),
        })
    return pd.DataFrame(rows, index=pd.Index(df.groupby("market_type").groups.keys(), name="market"))


def daily_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """DA/RT 按 (日期, 时段) 对齐，用于价差分析。只有 21792 对。"""
    piv = df.pivot_table(index=["trade_date", "period_id"], columns="market_type", values="price")
    piv = piv.dropna(subset=["DA", "RT"]).reset_index()
    piv["spread"] = piv["RT"] - piv["DA"]
    return piv
