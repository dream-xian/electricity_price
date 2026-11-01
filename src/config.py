"""全局配置：路径、种子、超参。随机种子只在这里定义一次。"""
from pathlib import Path

# ---- 路径 ----
# 以本文件位置反推仓库根目录，与「在哪个目录下敲命令」无关
ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data/student_dataset.csv"
FIG_DIR = ROOT / "reports/figures"
TAB_DIR = ROOT / "reports/tables"
MODEL_DIR = ROOT / "models"
OUT_DIR = ROOT / "outputs"

for _p in (FIG_DIR, TAB_DIR, MODEL_DIR, OUT_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ---- 复现 ----
SEED = 42

# ---- 任务定义 ----
MARKETS = ["DA", "RT"]
HORIZON_MAIN = 1     # 主任务：下一 15 分钟
HORIZON_ALT = 96     # 对照任务：次日同一时段
TEST_FRAC = 0.20     # 最后 20% 的天做测试
VALID_FRAC = 0.20    # 训练段末尾再切 20% 做验证
EMBARGO_DAYS = 1     # 切点之间空 1 天

# ---- 模型超参 ----
RF_PARAMS = dict(n_estimators=400, min_samples_leaf=5, max_features=0.5, n_jobs=-1, random_state=SEED)
GBDT_PARAMS = dict(max_iter=400, learning_rate=0.05, max_depth=4, l2_regularization=1.0,
                   early_stopping=True, validation_fraction=0.15, random_state=SEED)
