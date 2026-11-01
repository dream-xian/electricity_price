import sys, platform
import numpy as np, pandas as pd, matplotlib, sklearn, joblib

print("Python :", sys.version.split()[0], "|", platform.machine())
print("numpy  :", np.__version__, "| pandas:", pd.__version__)
print("sklearn:", sklearn.__version__, "| mpl:", matplotlib.__version__)

df = pd.read_csv("data/student_dataset.csv")
df["delivery_time"] = pd.to_datetime(df["delivery_time"], utc=True).dt.tz_convert("Asia/Shanghai")
print("shape  :", df.shape)
print(df.groupby("market_type")["price"].agg(["count", "mean"]))
print("OK" if df.shape == (58944, 5) else "FAIL")
