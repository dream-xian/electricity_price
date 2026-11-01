"""四个基准 + 三个模型。基准必须和模型同表比较。"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from config import GBDT_PARAMS, RF_PARAMS, SEED


# ---------------- 基准 ----------------
def naive_lag0(d):   return d["lag0"].to_numpy(float)   # t0 最新价，真正的 1 步惯性
def naive_lag1(d):   return d["lag1"].to_numpy(float)   # 再往前一格
def naive_yday(d):   return d["lag96"].to_numpy(float)
def naive_profile(d, prof): return d["period_id"].map(prof).to_numpy(float)
def naive_mean(d, mu):      return np.full(len(d), mu, float)


def profile_table(train: pd.DataFrame) -> pd.Series:
    """训练集 96 点均值曲线（只在训练集上算，防泄漏）。"""
    return train.groupby("period_id")["y"].mean()


# ---------------- 模型 ----------------
def make_ridge():
    return Pipeline([
        ("sc", StandardScaler()),
        ("m", RidgeCV(alphas=np.logspace(-2, 3, 20), cv=TimeSeriesSplit(n_splits=5))),
    ])


def make_rf():
    return RandomForestRegressor(**RF_PARAMS)


def make_gbdt():
    return HistGradientBoostingRegressor(**GBDT_PARAMS)


def make_model(name: str):
    return {"ridge": make_ridge, "rf": make_rf, "gbdt": make_gbdt}[name]()
