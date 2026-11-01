"""按天顺序切分 + embargo。绝不 random_state 打乱。"""
import numpy as np
import pandas as pd

from config import EMBARGO_DAYS, TEST_FRAC, VALID_FRAC


def time_split(d: pd.DataFrame, test_frac=TEST_FRAC, valid_frac=VALID_FRAC,
               embargo_days=EMBARGO_DAYS):
    """返回 (parts, spans)。parts 是 train/valid/test 三段 DataFrame。"""
    days = np.sort(d["trade_date"].unique())
    n = len(days)
    n_test = max(1, int(round(n * test_frac)))
    n_valid = max(1, int(round(n * valid_frac)))

    test_days = days[n - n_test:]
    valid_days = days[n - n_test - n_valid: n - n_test]
    train_days = days[: n - n_test - n_valid]

    if embargo_days > 0:
        train_days = train_days[:-embargo_days]
        valid_days = valid_days[: max(0, len(valid_days) - embargo_days)]

    parts = {
        "train": d[d["trade_date"].isin(train_days)].reset_index(drop=True),
        "valid": d[d["trade_date"].isin(valid_days)].reset_index(drop=True),
        "test": d[d["trade_date"].isin(test_days)].reset_index(drop=True),
    }
    spans = {}
    for k, v in parts.items():
        if len(v):
            spans[k] = (v["trade_date"].min(), v["trade_date"].max(), len(v))
        else:
            spans[k] = (pd.NaT, pd.NaT, 0)
    return parts, spans
