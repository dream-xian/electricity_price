# 《明天的电价会是多少？》从 0 到 1 实施手册（v2，对齐团队规范）

> 面向零基础同学。本文档只讲**怎么做、为什么这么做**，不替你交作业。
> 文中所有数字都是我先跑一遍你的数据得到的**真实量级参考**，用来帮你判断"我的模型是不是坏了"。

**v2 相对 v1 的变化**：已按 `CONTRIBUTING.md`（项目规范：Conda 环境、Git 版本控制与提交要求）重写环境与工程部分——
统一用 **Conda 环境 `electricity-price`**（废弃 v1 的 uv/venv 方案）、采用规范的仓库目录、引入分支与提交规范、
报告改为规范的 9 章结构并把「发现与学习」提到核心位置。

---

## 0. 先看清这件事：你到底在交付什么

### 0.1 任务拆解（把 8 条要求翻译成 8 个可验收产物）

| 任务书要求 | 你实际要做出的东西 | 验收标准（自己打勾用） |
|---|---|---|
| ① 读取数据、了解字段、检查连续性 | 一张「数据体检表」+ 一段文字结论 | 能说清 5 个字段、2 个市场的行数/日期范围/每天 96 点 |
| ② 画 DA/RT 曲线 | 4 张图（全期、单日放大、日内 96 点均值、分布直方图） | 看图能讲出"中午低谷、晚高峰、RT 更抖" |
| ③ 选预测目标与跨度 | 一段 200 字的"任务定义" + 一张信息集说明 | 说清预测时点 t0 有哪些数可用、预测哪一刻 |
| ④ 特征构造 | 特征清单表（含"预测时点是否可用"一列） | 每个特征都能回答"它什么时候能拿到" |
| ⑤ 选模型 + 参照方法 | 至少 3 个基准 + 2 个模型 | 有 naive 基准，模型必须和基准比 |
| ⑥ 按时间切分、比 MAE/RMSE | 模型对比表 + 切分示意图 | 无随机打乱、无跨切点泄漏 |
| ⑦ 误差分析 | 4 张误差分解图 + 结论 | 能指出"哪类时段错得最多、为什么" |
| ⑧ 总结与限制 | 一页纸结论 | 含"本实验不能证明什么" |

**关键认知**：这门课考的不是"你把 MAE 压到多低"，而是**你有没有把问题定义清楚、有没有诚实地说清结果能证明什么、不能证明什么**。
`CONTRIBUTING.md` 把「发现与学习」定为报告核心章节、要求篇幅不少于正文三分之一，就是这个意思。

### 0.2 先记住数据的三个物理事实（后面所有设计都由它推出）

我先跑了一遍你的 `student_dataset.csv`：

| 市场 | 行数 | 天数 | 匿名日期范围 | 均值 | 中位数 | 标准差 | 最小 | 最大 | 负价数 | ≥1000 的数 |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| DA（日前） | 37,152 | 387 | 2024-07-02 ~ 2025-07-23 | 345.9 | 319.1 | 136.4 | -50.0 | 1798.7 | 264 | 35 |
| RT（实时） | 21,792 | 227 | 2024-12-08 ~ 2025-07-22 | 395.3 | 342.1 | 237.8 | -50.0 | 1791.2 | 602 | 641 |

- **事实 1：RT 的窗口完全落在 DA 窗口内部**（RT 227 天 ⊂ DA 387 天）。两者可做时段对齐比较（共 21,792 对），但**不能拼成一条 58,944 点的序列**——这是任务书和规范 §4.1(3) 的双重硬约束。
- **事实 2：RT 比 DA 更"野"**。RT 标准差 237.8 vs DA 136.4；RT 尖峰（≥1000）641 条，是 DA 的 18 倍；负价 602 vs 264。原因见 §3.1。
- **事实 3：价格有强自相关**。相邻 15 分钟相关系数 DA=0.933、RT=0.860。这意味着**"上一刻价格"就是极强的预测器**，任何模型打不过它，说明实现有问题（或特征漏了它）。

### 0.3 一句最重要的提醒

> **朴素持续性基准（用上一时段价格预测下一时段）在你的数据上 DA 的 MAE 只有 23.0、RT 只有 53.9。**
> 如果你的随机森林跑出 80，那不是"模型不够好"，是**特征里没给它 `lag1`**，或者**切分/排序出错了**。
> 正确心态：**把 lag1 基准当成必须打败的对手，打不过就老实写"本模型未能优于朴素基准，原因如下"。**
> 规范 §4.3 明确要求记录"反直觉或失败的结果"——这种诚实的负结果本身就是得分点。

### 0.4 与团队规范的对接表（照这张表交作业不会漏项）

| 规范条款 | 具体要求 | 本文对应 | 你的动作 |
|---|---|---|---|
| §1 目录约定 | `src/ notebooks/ models/ reports/ data/(不提交) outputs/(不提交)` | §1.2 | 按模板建目录，课程数据目录**不放进仓库** |
| §2.1 Conda | 环境名 `electricity-price`，依赖全写 `environment.yml`，禁在 base 装包 | §1.3、附录 A | `conda init zsh` → `conda env create -f environment.yml` |
| §2.3 可复现 | 随机种子显式写出；notebook 重启内核后可全跑通 | §1.5、§7.7 | 种子进 `src/config.py` |
| §3.1 分支 | `feat/ fix/ exp/ report/ docs/`，禁止直推 main | §1.4 | 每个阶段开一个短分支 |
| §3.2 提交范围 | 只提交 模型/源代码/报告 三类 | §1.4、附录 B.1 | `.gitignore` 先写好再 `git add` |
| §3.3 提交信息 | Conventional Commits，含 `exp` `model` `report` | §1.4、附录 B.4 | 抄模板改 |
| §3.4 粒度与标签 | 一提交一变更；打 `model-v1.0` `report-v1.0` | §1.4、§11 | 关键节点打标签 |
| §4.2 报告结构 | 9 章固定结构 | §9.1 | 报告骨架直接照抄 |
| §4.3 发现与学习 | ≥1/3 篇幅，≥3 条发现 + 3 条学习，须有图/指标支撑 | §9.2 | **这是全文最花时间的部分** |
| §5 提交前检查 | 9 项清单 | 附录 B.5 | 每次提交前过一遍 |

---

## 1. 环境与工程骨架（1 天）

### 1.1 技术选型

| 选择 | 选它 | 为什么 |
|---|---|---|
| **Conda（环境名 `electricity-price`）** | ✅ 必须 | 规范 §2.1 硬性要求。团队要能 `conda env create -f environment.yml` 一键复现 |
| Python **3.12** | ✅ | 生态最稳。你机器上 Homebrew 的 3.14 太新，科学计算轮子常滞后 |
| pandas / numpy | ✅ | 表格 + 时间序列的事实标准 |
| matplotlib / seaborn | ✅ | 够用、可控、出图直接进 `reports/figures/` |
| scikit-learn | ✅ | 线性回归、随机森林、梯度提升、指标、切分全在里面 |
| joblib | ✅ | 规范要求模型落盘为 `models/*.joblib` |
| statsmodels（可选） | ⚠️ 加分 | 做 ACF/PACF 图、Diebold-Mariano 检验时才需要 |
| Prophet / LSTM / Transformer | ❌ 不建议 | 只有 5 列、无外生变量、样本量小。深度模型几乎必然过拟合，且你解释不了它 |
| XGBoost / LightGBM（可选） | ⚠️ 加分 | 想冲分再加，且要先 `brew install libomp`；sklearn 的 `HistGradientBoostingRegressor` 已够用 |

### 1.2 仓库目录（按规范 §1，与课程数据目录**物理分开**）

```
~/Projects/electricity-price/          ← 你的仓库（纳入 Git）
├── environment.yml                    # Conda 环境定义（提交）
├── .gitignore                         # 见附录 B.1（提交）
├── README.md                          # 怎么跑（提交）
├── src/                               # 源代码（提交）
│   ├── config.py                      # 路径、SEED、超参
│   ├── io.py                          # 读数据 + 体检
│   ├── features.py                    # 特征工程（核心）
│   ├── split.py                       # 时间切分
│   ├── models.py                      # 基准 + 模型定义
│   ├── evaluate.py                    # 指标 + 误差分解
│   └── plots.py                       # 画图（含中文字体设置）
├── notebooks/                         # 探索性分析（提交，属于源代码）
│   ├── 01_eda.ipynb
│   ├── 02_features.ipynb
│   ├── 03_models.ipynb
│   └── 04_errors.ipynb
├── models/                            # 最终模型 + 元数据（提交）
│   ├── rf_v1.joblib
│   └── rf_v1.meta.json
├── reports/                           # 报告与图表（提交）
│   ├── final_report.md
│   └── figures/
├── data/                              # 数据（不提交，已 gitignore）
│   └── student_dataset.csv            # 从课程目录拷来，仅本地
├── outputs/                           # 临时输出、日志、缓存（不提交）
└── docs/                              # 环境说明等（提交）
    └── IMPLEMENTATION_PLAN.md         # 就是本文档，建好仓库后搬过来

~/Downloads/electricity_price_course_data/   ← 课程原始数据（不进 Git，只读）
```

**四个必须理解的点：**

1. **仓库和课程数据目录要分开。** 规范 §1 明说"课程提供的 `electricity_price_course_data/` 视为原始数据目录，不纳入版本控制"。所以不要在这个目录里 `git init`。
2. **`data/` 里放一份数据副本**（本地拷贝，被 gitignore）。好处：所有脚本用相对路径 `data/student_dataset.csv`，换机器只要重新拷一次就能跑。
3. **不要用软链接指向课程目录**。软链里带绝对路径，一旦提交就违反规范 §2.1(4)"不得提交含绝对路径的配置文件"，而且队友拉下来就是断链。
4. **`outputs/` 和 `reports/figures/` 分工要清楚**：中间产物、日志、调参试跑图 → `outputs/`（不提交）；**要进报告的图** → 一律存 `reports/figures/`（提交）。v1 里我把图画到 `outputs/figures/`，那是错的——报告引用的图必须随报告一起提交，否则队友/老师拿到仓库看不到图。

### 1.3 环境：Conda + `environment.yml`

规范要求"项目使用独立 Conda 环境，环境名统一为 `electricity-price`，禁止在 `base` 环境中安装项目依赖"。
完整步骤、`environment.yml` 全文、以及**你这台机器上会遇到的三个 conda 专有报错**，都在 **附录 A**。

一句话版（细节务必回看附录 A）：

```bash
conda init zsh                    # 你的机器还没初始化过，必须先跑这一步
exec zsh                          # 重开 shell 让 conda activate 生效
cd ~/Projects/electricity-price
conda env create -f environment.yml
conda activate electricity-price
```

### 1.4 Git 工作流（规范 §3，照做即可）

#### 分支

`main` 永远可运行、可复现；开发一律走短生命周期分支：

| 分支前缀 | 用在哪 | 你的实际用法 |
|---|---|---|
| `feat/` | 新增功能或特征 | `feat/data-check`、`feat/features-lag` |
| `fix/` | 修缺陷、修泄漏、修切分 | `fix/time-split-leakage` |
| `exp/` | 模型/参数/特征组合实验 | `exp/rf-depth`、`exp/gbdt-quantile` |
| `report/` | 报告撰写与修订 | `report/draft`、`report/error-analysis` |
| `docs/` | 文档与环境说明 | `docs/environment`、`docs/readme` |

合并前先变基，保持历史线性（规范 §3.1(3)）：

```bash
git fetch origin
git rebase origin/main
```

**个人项目没有远端也要养成习惯**：至少在本地开分支，做完再 `git checkout main && git merge --ff-only feat/xxx`。
好处很实在——实验做砸了，`git checkout main` 一句话回到干净状态，不用手工删文件。

#### 提交信息（Conventional Commits）

```
<type>(<scope>): <subject>

<body>

<footer>
```

- `type` 只能用：`feat` `fix` `exp` `model` `report` `refactor` `docs` `chore`
- `scope` 建议：`data` `features` `split` `model` `eval` `report`
- `subject` 祈使语气、≤50 字符、句末不加句号
- `body` 写"为什么改、改了什么、影响如何"；**涉及模型必须写 MAE/RMSE 及对比基线**

四类真实示例（对应你的四个阶段，附录 B.4 有更多）：

```
feat(data): 增加数据体检脚本与连续性校验

校验每日 96 点、15 分钟间隔、时段号自洽、重复时间戳。
DA 37152 行 / RT 21792 行，全部通过，未做任何插值或删点。

feat(features): 分市场构造滞后与滚动特征

按 market_type 分组后排序再 shift，避免跨市场污染。
rolling 统一 shift(1)，排除当期，防止目标泄漏。
lag96 前 96 行 NaN 直接丢弃，不插值。

exp(rf): 对比 min_samples_leaf 取 5 与 20

固定 SEED=42，按天切分 + 1 天 embargo。
leaf=5 在验证集 MAE 更优（DA 24.1 vs 25.8），采用 leaf=5。

model(rf): 保存随机森林最终模型与评估结果

DA 测试集 MAE=..., RMSE=...；RT 测试集 MAE=..., RMSE=...。
对比 lag1 基线（23.0 / 53.9）...。
```

#### 提交粒度

- **一次提交只做一件事**。不要"加了特征 + 改了切分 + 更新了报告"混在一起。
- **依赖变更单独提交**（规范 §2.3），提交信息用 `chore(deps):`，并说明原因。
- **禁止** `WIP`、`临时保存`、`最终版`、`改了一下` 这类信息。
- 提交前 `git status` + `git diff` 看一遍，**按文件显式 `git add`**，不要 `git add .`——`git add .` 是误提交数据/缓存的头号原因。

#### 标签（关键节点必须打）

```bash
git tag -a model-v1.0 -m "随机森林最终模型与评估结果"
git tag -a report-v1.0 -m "课程报告提交版"
git push origin --tags        # 有远端时
```

### 1.5 三条工程纪律

```python
# src/config.py
SEED = 42
MARKETS = ["DA", "RT"]
DATA = "data/student_dataset.csv"
FIG = "reports/figures"
TMP = "outputs"
TEST_FRAC = 0.2      # 按天数切，最后 20% 天做测试
VALID_FRAC = 0.2     # 训练段末尾再切 20% 做验证
```

1. **随机种子只在一个地方定义**，所有随机处都传 `random_state=SEED`。规范 §2.3 要求"随机种子须在代码或配置中显式写出"——写在 `config.py` 就是标准答案。
2. **原始 CSV 只读**。加工全部在内存或 `outputs/` 里做。删了原始数据你得重新找老师要。
3. **每个 notebook 开头重新 import + 重新读数据**，不依赖上一个 notebook 的内存变量。规范 §2.3 要求"重启内核后全部运行无错误"，这一条能直接保证你过。

---

## 2. 第一步：数据体检（0.5 天）

### 2.1 要做什么

不是"读进来画个图"，而是**用代码证明这份数据是干净的，并把证据写成一张表**。这个产物进报告的**第 2 章**。

### 2.2 代码骨架

```python
import pandas as pd, numpy as np

df = pd.read_csv("data/student_dataset.csv")
df["trade_date"] = pd.to_datetime(df["trade_date"])
df["delivery_time"] = pd.to_datetime(df["delivery_time"], utc=True).dt.tz_convert("Asia/Shanghai")

# ① 规模与覆盖
print(df.shape)                                   # (58944, 5)
print(df.groupby("market_type")["trade_date"].agg(["count","min","max","nunique"]))

# ② 每天是否 96 点
per_day = df.groupby(["market_type","trade_date"]).size()
print(per_day.value_counts())                     # 期望只有 96 这一种值

# ③ 重复与缺失
print(df.duplicated(["market_type","delivery_time"]).sum())   # 期望 0
print(df["price"].isna().sum())                               # 期望 0

# ④ 15 分钟间隔是否连续
for m, g in df.groupby("market_type"):
    gap = g.sort_values("delivery_time")["delivery_time"].diff().dropna()
    print(m, gap.value_counts().head())

# ⑤ 时段号与时间是否自洽
chk = df.assign(hour=df["delivery_time"].dt.hour, minute=df["delivery_time"].dt.minute)
chk["expect_pid"] = chk["hour"]*4 + chk["minute"]//15 + 1
print((chk["expect_pid"] != chk["period_id"]).sum())          # 期望 0

# ⑥ 价格分布形态（负价、零、尖峰）
print(df.groupby("market_type")["price"].describe(percentiles=[.01,.05,.5,.95,.99]))
```

### 2.3 原理：为什么要先体检，而不是先建模

1. **时间序列模型的正确性建立在"等间隔、无缺失、有序"之上**。`shift(1)` 隐含假设"上一行就是上一刻"。若中间断了一天，`shift(1)` 拿到的是昨天的价，你以为拿到 15 分钟前的价，特征语义就错了，而且**不报错**——静默错误最可怕。
2. **`period_id` 与 `delivery_time` 的自洽性检查，是发现"数据被重排过"的唯一手段**。这份数据是脱敏减 364 天生成的，理论上自洽，但必须验一遍，因为这决定你能否放心用 `period_id` 当特征。
3. **负价和尖峰数量要先数出来**，它们是后面误差分析的分组依据。264 条负价、641 条 RT 尖峰，这些数字要写进报告。

### 2.4 交付：数据体检表（照抄这个格式）

| 检查项 | 方法 | DA 结果 | RT 结果 | 结论 |
|---|---|---|---|---|
| 记录数 | `shape` | 37,152 | 21,792 | 与 README 一致 |
| 日期覆盖 | `nunique` | 387 天 | 227 天 | 连续无缺口 |
| 每日时段数 | `groupby().size()` | 全部 96 | 全部 96 | 等间隔 |
| 重复时间戳 | `duplicated()` | 0 | 0 | 无重复 |
| 缺失价格 | `isna()` | 0 | 0 | 无需插值 |
| 15 分钟间隔 | `diff()` | 全部 15min | 全部 15min | 无断档 |
| 时段号自洽 | 反算 | 0 处不符 | 0 处不符 | `period_id` 可信 |
| 负价 / ≥1000 | 计数 | 264 / 35 | 602 / 641 | 保留，作为分析分组 |

**注意**：报告里写"检查通过"不够，要写"我用什么方法检查的"。规范 §4.1(5) 要求所有结论有代码依据。

---

## 3. 第二步：EDA（1 天）

### 3.1 先补一点电力市场业务原理，这决定你怎么看图

这是本任务"金融/业务视角"的部分，写进报告能明显拉开差距：

- **DA（日前市场）**：提前一天对次日 96 个时段集中竞价出清。参与者有一整天研究负荷预测、机组检修、燃料成本，所以**价格平滑、可预测性高**（DA 标准差只有 136 的原因）。
- **RT（实时市场）**：交付时刻附近的平衡市场，修正"实际 − 计划"的偏差。偏差由**预测误差本身**驱动，所以 RT 天然更抖（标准差 237、尖峰 18 倍于 DA）。
- **负价怎么来的**：新能源大发 + 机组最小技术出力限制 + 下调空间不足。中午光伏出力高、负荷低，就可能出现负价。你的数据 DA 中午 12 点均值 251，是全天最低——**这个"午间低谷"就是新能源渗透的指纹**。
- **尖峰怎么来的**：晚高峰负荷爬坡 + 机组启动慢 + 阻塞。数据晚 19 点 DA 均值 487、RT 554，全天最高。
- **DA-RT 价差**（21,792 对）：均值 +15.6、中位数 −5.4、标准差 172.4，范围 −1135 ~ +1321。**中位数为负、均值为正**说明多数时候 RT 略低于 DA，但少数极端时段 RT 暴涨把均值拉正——典型**重尾右偏**。记住这个形状，它决定了后面为什么 MAE 比 RMSE 稳。

### 3.2 图 1-2：全期价格曲线

```python
fig, axes = plt.subplots(2, 1, figsize=(14, 7))
for ax, m in zip(axes, ["DA", "RT"]):
    g = df[df.market_type == m].sort_values("delivery_time")
    ax.plot(g.delivery_time, g.price, lw=0.4, color="#c0392b" if m=="DA" else "#2c6fbb")
    ax.set_title(f"{m} 全期价格 (n={len(g)})"); ax.set_ylabel("CNY/MWh")
fig.savefig("reports/figures/fig01_price_series.png", dpi=300, bbox_inches="tight")
```

**看图要看什么**（这是评分点）：
- 有没有**水平漂移**（季节性）→ 决定要不要做差分或加趋势特征
- 有没有**方差聚集**（一段时期特别抖）→ 决定要不要加滚动波动率特征
- 尖峰是**孤立点**还是**成簇**（连续几个时段都高）→ 成簇说明事件驱动，孤立点更像报价异常
- 负价集中在**什么时段**（大概率中午）

### 3.3 图 3：单日放大（挑 3 天：最平稳 / 最高尖峰 / 负价最多）

```python
peak_day = df[df.market_type=="DA"].loc[lambda d: d.price.idxmax(), "trade_date"]
```
**为什么必须画单日**：全期图看不出"日内形状"，而日内形状是你构造 `period_id`、`sin/cos` 特征的**全部依据**。业务上这叫"负荷曲线形态"，是电价预测的核心先验。

### 3.4 图 4：96 点日内均值曲线（最重要的一张）

```python
prof = df.groupby(["market_type","period_id"])["price"].agg(["mean","std"]).reset_index()
```
你会看到：**凌晨 0-1 点次高（DA 378/361）、中午 12 点最低（251）、晚 19 点最高（487）**。
这张图直接说明两件事：
1. `period_id` 必须是特征（它与价格是强非线性关系，不单调）；
2. 线性模型若不给 `sin/cos` 编码，只能学到"平均趋势"，学不到"中午凹下去"。

### 3.5 图 5：分布直方图 + 分位数表

```python
df[df.market_type=="DA"].price.hist(bins=120)
print(df.groupby("market_type").price.quantile([.01,.05,.25,.5,.75,.95,.99]))
```
**必须看到的**：分布**右偏 + 长尾**（DA 中位数 319 但最大 1798），左尾拖到 −50。
**技术后果**（报告里一定要写）：右偏长尾 → 用 L2 损失（RMSE）时模型被少数尖峰"拽"着走；用 L1 损失（MAE）时模型实际在拟合**条件中位数**。所以**同一模型优化 MAE 和优化 RMSE 会得到不同预测**，这不是 bug，是统计性质。

### 3.6 图 6：自相关（ACF）

不装 statsmodels 也能算：

```python
def acf(x, nlags=200):
    x = np.asarray(x, float); x = x - x.mean()
    return np.array([np.corrcoef(x[:-k], x[k:])[0,1] for k in range(1, nlags)])
```
**你会看到**：lag=1 极高（0.93/0.86），lag=96 处有明显**次峰**（昨日同时段）。
**这是选特征的直接证据**。报告可这样写："ACF 在 lag 96 出现次峰，说明存在日周期，故构造 lag96；lag1 相关性最高，说明短时惯性主导，故 lag1 为核心特征。"

### 3.7 图 7：DA vs RT 价差时序 + 分布

```python
piv = df.pivot_table(index=["trade_date","period_id"], columns="market_type", values="price").dropna()
piv["spread"] = piv["RT"] - piv["DA"]
```
**看什么**：价差在什么时段最大（大概率晚高峰）、什么时候为负（中午）。
**为什么值得单独画**：这是报告里"两市场行为差异"的量化证据，也是"RT 需要更强非线性能力"的理由。

---

## 4. 第三步：定义预测任务（0.5 天，但决定成败）

### 4.1 一个预测任务必须回答 4 个问题

| 问题 | 你的答案（建议） |
|---|---|
| **预测什么** | y = 某市场某时段的 `price`（CNY/MWh） |
| **预测时点 t0 在哪** | t0 = 目标时段开始前（h=1 时为前一时段结束时） |
| **预测跨度 h** | 主任务 h=1（下一时段）；对照任务 h=96（次日同一时段） |
| **t0 时刻有哪些数可用** | 只能用 t0 之前的 `price`（教学假设，见 4.3）+ 时间字段 |

### 4.2 跨度怎么选：任务书第 3 条，必须给理由

**推荐主任务 h=1，对照 h=96。** 三层理由：

1. **信息论层面**：h=1 时 t0 距目标只隔 15 分钟，`lag1` 相关 0.933/0.860，任务"可学"。h=96 时隔了一整天，中间 96 个点全未知，信息量骤降——**难度差异本身就是有价值的结论**。
2. **业务层面**：h=1 对应"实时滚动报价/储能调度"，h=96 对应"日前申报"。标题《明天的电价》听起来像 h=96，但**数据里没有负荷、新能源、天气**，任何声称能做好 h=96 的结果都不可信。诚实做法是：主任务做 h=1 把方法论走通，再用 h=96 说明"跨度一拉长，误差涨多少、为什么"。
3. **可证伪层面**：h=1 有强基准（lag1，DA MAE 23.0），你能明确回答"我的模型有没有超过它"。h=96 的基准是"昨日同时段"（DA MAE 55.9），同样可证伪。

**如果老师明确要求"预测明天"**，就把 h=96 做主线、h=1 做附录，但要写清楚："在无外生变量条件下，次日预测误差主要来自日内形态的随机漂移，模型只能复现平均形态，不能预测事件性尖峰。" 这句话本身就是好结论。

### 4.3 必须写进报告的"可用性假设"（最重要的一段话）

数据没有 `publication_time`，所以：

> **教学假设**：假设 t0 时刻之前的所有价格均已发布且可观测。这是教学简化，本数据无法证明真实市场中 DA/RT 价格在预测截止时刻的发布状态，因此本实验误差不能直接外推到生产环境。

**为什么必须写**：任务书、README、审计报告三处都强调这点。写上不加分，不写**一定扣分**（老师把它写进任务书就是为了看谁注意到）。

**一个更站得住的讨论**（加分项）：预测 RT(t) 时把 DA(t) 当特征——DA 市场**提前一天出清**，DA(t) 在交付日之前已公布，这是本数据里唯一能讲通可用性的论证。但须注明：这是**跨市场特征**，不等于把两条序列合并建模（规范禁止的是后者）。

### 4.4 交付：任务定义卡（写成一页，进报告第 1 章）

```
目标变量： price（CNY/MWh），按 market_type 分别建模
预测跨度： 主 h=1（下一 15 分钟），对照 h=96（次日同时段）
预测时点： t0 = 目标时段起点 - h*15min
可用信息： price 在 t0 前的历史值 + 日历字段（hour, period_id, dow）
          （+ 可选：DA(t) 作为 RT(t) 的特征，附可用性论证）
不可用信息： 负荷、风电、光伏、天气、检修、阻塞、报价量 —— 数据中不存在，禁止伪造
评价口径： MAE 为主，RMSE 为辅，WAPE 做跨市场可比
```

---

## 5. 第四步：特征工程（1.5 天，全项目最核心）

### 5.1 铁律：先分组，再排序，再 shift

```python
def build_features(market_df, h=1):
    d = market_df.sort_values("delivery_time").reset_index(drop=True).copy()
    # ---- 目标 ----
    d["y"] = d["price"].shift(-h)          # 未来 h 步
    # ---- 滞后 ----
    for k in [1, 2, 4, 96, 192]:
        d[f"lag{k}"] = d["price"].shift(k)
    # ---- 滚动（必须再 shift(1)，否则包含当期 = 泄漏）----
    d["roll_mean_4"]  = d["price"].shift(1).rolling(4,  min_periods=4).mean()
    d["roll_mean_96"] = d["price"].shift(1).rolling(96, min_periods=96).mean()
    d["roll_std_96"]  = d["price"].shift(1).rolling(96, min_periods=96).std()
    d["roll_max_96"]  = d["price"].shift(1).rolling(96, min_periods=96).max()
    d["lag96_diff"]   = d["lag96"] - d["lag192"]     # 日间动量
    # ---- 日历 ----
    t = d["delivery_time"]
    d["hour"]       = t.dt.hour
    d["dow"]        = t.dt.dayofweek
    d["is_weekend"] = (d["dow"] >= 5).astype(int)
    d["period_sin"] = np.sin(2*np.pi*d["period_id"]/96)
    d["period_cos"] = np.cos(2*np.pi*d["period_id"]/96)
    d["dow_sin"]    = np.sin(2*np.pi*d["dow"]/7)
    d["dow_cos"]    = np.cos(2*np.pi*d["dow"]/7)
    return d
```

**四个细节，每个都是真实会踩的坑**：

1. **`sort_values` 必须在 `shift` 之前**，且要在 `groupby("market_type")` **之后**调用。若先 shift 再分组，RT 第一行会拿到 DA 最后一行的价格——**不报错，静默污染**。
2. **`rolling` 之后必须 `shift(1)`**。`rolling(4).mean()` 默认包含"当期"，而"当期"就是你要预测的那一期，这叫**目标泄漏（target leakage）**，是新手模型"分数好得不真实"的头号原因。
3. **`period_id` 与 `hour` 有共线性**。线性模型里留一套即可（建议 `period_sin/cos` + `period_id`），不要同时留 `hour` 和 `period_id`，否则系数不可解释。树模型无所谓。
4. **`lag96` 会产生前 96 行 NaN**。不要插值，直接 `dropna()`。理由：插值等于**编造历史**，且用全量数据插值会把测试期信息漏进训练期。

### 5.2 特征清单表（报告第 3 章必须有这张表）

| 特征 | 构造 | 捕捉什么 | t0 可用？ | 风险 |
|---|---|---|---|---|
| `lag1` | price(t-1) | 15 分钟惯性 | ✅（教学假设） | 若假设不成立则全盘失效 |
| `lag2, lag4` | price(t-2), price(t-4) | 短期趋势（30/60 分钟） | ✅ | 与 lag1 高度共线 |
| `lag96` | price(t-96) | 昨日同时段（日周期） | ✅ | 跨日，风险最低 |
| `lag192` | price(t-192) | 前日同时段（周内趋势） | ✅ | 弱，可作对照 |
| `roll_mean_4` | 前 1 小时均值 | 局部水平 | ✅ | 平滑后丢尖峰信息 |
| `roll_std_96` | 前 24h 标准差 | **波动率/不确定性** | ✅ | 对负价敏感 |
| `roll_max_96` | 前 24h 最高 | 尖峰记忆 | ✅ | 对异常值极敏感 |
| `lag96_diff` | lag96 − lag192 | 日间动量 | ✅ | 噪声放大 |
| `period_id` | 原字段 | 日内形态（非线性） | ✅ | 与 hour 冗余 |
| `period_sin/cos` | 三角编码 | 周期的**连续**表示 | ✅ | 线性模型必需品（见 5.3） |
| `dow`, `is_weekend` | 派生 | 周内效应 | ✅ | 只有 13 个月，周效应估计不稳 |
| `month`（谨慎） | 派生 | 季节 | ⚠️ | **脱敏后节假日错位**，季节含义可疑，建议只做敏感性实验 |
| `DA(t)`（可选） | 直接取 | RT 的市场基准 | ⚠️ 需论证 | 跨市场，务必单列实验并说明 |

### 5.3 原理：为什么用 `sin/cos` 编码而不是直接给 `period_id`

`period_id` 取值 1~96，线性模型里只有一个系数 β，等于假设"价格随 period_id 线性上升"。但真实形态是**中午凹、晚上凸**（12 点 251，19 点 487），线性拟合不出来。
`sin(2πk/96)` 与 `cos(2πk/96)` 组合，可在平面上**表示任意相位的周期波形**——这是傅里叶级数取一阶项。加二阶（`sin(4πk/96)`）就能表示双峰。**这就是"用两个特征表达 96 个虚拟变量"的技术手段，本质是降维 + 保留周期性。**

树模型不需要（能自己切分），但给了也无害。

### 5.4 原理：为什么 `dow` 不能直接喂线性模型

`dow` 是 0~6 的类别，不是数值。线性模型会把"周日=6"理解成"比周一贵 6 倍"，毫无意义。三个选项：
- 独热编码（7 列，可解释，推荐给线性模型）
- 三角编码（2 列，假设周内平滑变化，最省参数）
- 直接给树模型（树能自己切）

**怎么选**：样本量小（DA 37k、RT 21k）时**参数越少越稳**。建议三角编码 + `is_weekend`。

### 5.5 交付：`src/features.py` + 特征清单表 + 每个特征的可用性依据

---

## 6. 第五步：时间切分（0.5 天，最容易翻车）

### 6.1 铁律：绝不 `train_test_split(random_state=...)`

```python
# 错误：随机打乱会让模型"看到未来"
# 正确：按天切，最后 20% 的天做测试
days = sorted(df["trade_date"].unique())
n = len(days)
test_days  = days[int(n*0.80):]
valid_days = days[int(n*0.64):int(n*0.80)]
train_days = days[:int(n*0.64)]
```

**为什么随机切分是致命的**：电价相邻 15 分钟相关性 0.93。随机切分后测试集的"邻居"几乎都在训练集里，模型只要记住邻居就能"预测"，MAE 会低到离谱（比如 5），但这个数**毫无意义**——真实部署时未来一定是空的。这叫**数据泄漏**，是时间序列第一大罪。规范 §3.3 甚至把"数据泄漏或错误切分"列为 `fix` 类型的典型场景，说明这是重点考察项。

### 6.2 必须留 gap（purge / embargo）

**原理**：特征里有 `lag96`（昨天同时段）、`roll_std_96`（过去 24h）。若训练集最后一天是 D、测试集第一天是 D+1，那么 D+1 的 `lag96` 正好是 D 的价格——**D 的价格在训练集里**。这不算严格泄漏（预测时确实能拿到），但会让训练/测试边界模糊，评估偏乐观。

**做法**：训练段与测试段之间**空 1 天**（h=96 时不够，要空 `ceil(h/96)` 天）。报告里写："设置 1 天 embargo，确保特征窗口不跨切点。"

### 6.3 加一层滚动前推验证（walk-forward）

单次切分的评估有运气成分（正好切在平稳期或动荡期）。更稳的是**滚动前推**：

```
折 1: [------训练 60%------][验证 10%]
折 2: [-------训练 70%-------][验证 10%]
折 3: [--------训练 80%--------][验证 10%]
折 4: [---------训练 90%---------][验证 10%]
```

```python
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=4, gap=96)   # gap 以样本数计，96 = 1 天
```
**报告里报"4 折验证 MAE = 23.1 ± 1.8"比报单个数更有说服力**——方差本身说明模型稳不稳。

### 6.4 切分示意图（画一张，进报告第 4 章）

用 matplotlib 画三条彩色横条表示 train/valid/test 的时间范围，标注切点日期与 embargo 区间。这张图能一秒说服读者"你没有作弊"。

---

## 7. 第六步：基准与模型（1.5 天）

### 7.1 必须先建 4 个基准（没有基准的模型比较没有说服力）

```python
def naive_lag1(d):              return d["lag1"]                  # 上一时段
def naive_yday(d):              return d["lag96"]                 # 昨日同时段
def naive_profile(d, prof):     return d["period_id"].map(prof)   # 训练集 96 点均值
def naive_mean(d, mu):          return np.full(len(d), mu)        # 全局均值
```

**我实测的量级**（最后 20% 天做测试）：

| 基准 | DA MAE | DA RMSE | RT MAE | RT RMSE |
|---|---:|---:|---:|---:|
| 全局均值 | 101.5 | 144.0 | 107.7 | 180.3 |
| 96 点均值曲线 | 100.4 | 135.0 | 110.0 | 173.7 |
| 昨日同时段 | 55.9 | 87.6 | 121.5 | 199.4 |
| **上一时段（lag1）** | **23.0** | **44.8** | **53.9** | **106.0** |

**读这张表的三个结论**（直接进报告）：
1. **"96 点均值曲线"几乎等于"全局均值"**（100.4 vs 101.5）——说明**日内形态本身解释力有限**，价格的水平漂移才是主要变异来源。这是个反直觉但有价值的发现，正好是规范 §4.3 要的"反直觉结果"。
2. **DA 上 lag1 远好于昨日同时段（23.0 vs 55.9）**；RT 上 lag1 仍更好（53.9 vs 121.5）但相对优势缩小——说明 **DA 短时惯性更强**（日前出清平滑），RT 日间记忆更差。
3. **DA 的 lag1 基准 MAE=23 是个很高门槛**。你的线性回归/随机森林必须包含 `lag1`，才可能接近它。

### 7.2 模型 1：Ridge 回归

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV

pipe = Pipeline([("sc", StandardScaler()), ("m", RidgeCV(alphas=np.logspace(-2,3,20)))])
```

**为什么用 Ridge 而不是普通 OLS**：特征高度共线（`lag1`、`lag2`、`roll_mean_4` 相关系数可能 >0.98）。OLS 在共线下系数会爆炸（正负巨大、互相抵消），预测值还行但**系数完全不可解释**，你就没法写"lag1 系数 0.8，说明惯性主导"。Ridge 加 L2 惩罚把系数压小、稳定住，**代价是轻微偏差，换来可解释性与稳定性**。

**原理一句话**：Ridge 在最小化 `Σ(y-ŷ)² + α·Σβ²`。α 越大越倾向把系数压向 0（欠拟合），越小越接近 OLS（过拟合）。`RidgeCV` 用交叉验证选 α——**注意要用时间序列 CV，不是默认 KFold**。

**线性模型三个已知短板**（报告里要写）：
1. **学不到交互**（"晚高峰 + 周末"的组合效应），除非手动构造交互项；
2. **对异常值敏感**（L2 损失被 −50 和 1798 拽偏）→ 备选 `HuberRegressor`，并对比；
3. **可外推**（这是优点）：测试期出现 2000 的尖峰，线性模型敢预测 1500，树模型不敢（见 7.4）。

### 7.3 模型 2：随机森林

```python
from sklearn.ensemble import RandomForestRegressor
rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=5,
                           max_features=0.5, n_jobs=-1, random_state=SEED)
```
**原理（必须讲清，这是评分点）**：
- 单棵树：递归地把特征空间切成矩形，每个叶子取均值。**能自动学到"19 点 + 周末 → 450"这种非线性交互**，不需手动编码。
- 森林：训练几百棵**各不相同**的树（bootstrap 抽样 + 随机特征子集），预测取平均。**平均降低方差**——单棵树对噪声极敏感，几百棵平均后噪声互相抵消。这就是 bagging。
- **关键限制：树只能"插值"，不能"外推"**。叶子预测值一定是训练集里某段价格的均值，所以**测试期若出现训练期没见过的 1798 以上尖峰，森林必然低估**。这不是调参能解决的，是模型结构决定的。你的 RT 有 641 条 ≥1000，这一点会非常明显，必须在误差分析里点名。

**超参怎么选（小数据，宁可保守）**：
- `min_samples_leaf`：5~20。**越小越容易记住噪声**。37k 行下 `5` 是合理起点。
- `max_features`：0.3~0.6。越小树越随机、越不易过拟合，但需要更多树。
- `n_estimators`：400~800。**只影响稳定性，不影响过拟合**（多了不会更差，只是慢）。
- `max_depth`：不设或 15+。让它长，靠 `min_samples_leaf` 控制。

### 7.4 模型 3（加分）：梯度提升

```python
from sklearn.ensemble import HistGradientBoostingRegressor
gb = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05,
                                   max_depth=4, l2_regularization=1.0,
                                   early_stopping=True, validation_fraction=0.15,
                                   random_state=SEED)
```
**原理**：和随机森林"并行平均"不同，提升是**串行纠错**——第 2 棵树拟合第 1 棵的残差，第 3 棵拟合前两棵的残差……所以它**偏差更低、更容易过拟合**。`learning_rate` 是"每棵树贡献打几折"（0.05 = 只信 5%），配合 `max_iter` 形成"小步慢走"，这是提升模型的核心正则化手段。

**优点**：原生支持缺失值、支持 `loss="absolute_error"`（直接优化 MAE，对重尾数据更合适）。
**风险**：小数据 + 强表达力 = 过拟合。**必须用 `early_stopping` + 独立验证段**。

### 7.5 怎么选模型：一张决策表

| 场景 | 选它 | 理由 |
|---|---|---|
| 需要解释"哪个特征重要、系数多少" | Ridge | 系数可读 |
| 想拿最好的点预测 | 随机森林 / GBDT | 非线性 + 交互 |
| 数据重尾、尖峰多 | GBDT + `loss="absolute_error"` | L1 损失不被尖峰绑架 |
| 需要预测区间（加分） | `GradientBoostingRegressor(loss="quantile", alpha=0.9)` | 直接给 90% 分位 |
| 要外推到训练期没见过的价格水平 | 线性模型 | 树不能外推 |

**建议路线**：`naive_lag1`（基准）→ `Ridge`（可解释基线）→ `RF`（主力）→ `HistGBDT`（冲分）。四个都跑、都报，报告里说清"谁赢、为什么赢、赢多少"。

### 7.6 模型对比表（交付核心表格，进 `reports/` 与报告第 5 章）

| 模型 | 市场 | 跨度 | MAE | RMSE | WAPE | 训练耗时 |
|---|---|---:|---:|---:|---:|---:|
| naive_lag1 | DA | h=1 | 23.0 | 44.8 | — | — |
| naive_yday | DA | h=1 | 55.9 | 87.6 | — | — |
| Ridge | DA | h=1 | ? | ? | ? | ? |
| RF | DA | h=1 | ? | ? | ? | ? |
| GBDT | DA | h=1 | ? | ? | ? | ? |
| ... | RT | h=96 | ... | ... | ... | ... |

**再加一个 WAPE**（Weighted Absolute Percentage Error）：
```python
wape = np.abs(y - yhat).sum() / np.abs(y).sum()
```
**为什么不用 MAPE**：数据里有 264/602 条负价、21 条零价。MAPE 分母是 `y`，遇到 0 爆炸、遇到负价符号全乱。**这是本数据集专属的坑，写进报告是加分项。** WAPE 用总绝对量做分母，稳健且可在 DA/RT 间比较。

### 7.7 调参与特征筛选（小数据的正确姿势）

1. **只用验证集调参，测试集只在最后用一次**。用测试集调参 = 偷看答案。
2. **`GridSearchCV` 要传 `cv=TimeSeriesSplit(...)`**，不能默认 KFold。
3. **特征重要性用"置换重要性"而不是默认的 `feature_importances_`**：
   ```python
   from sklearn.inspection import permutation_importance
   r = permutation_importance(model, X_valid, y_valid, n_repeats=10, random_state=SEED)
   ```
   **原理**：把某列随机打乱，看验证集误差涨多少，涨得多 = 重要。**比 `feature_importances_` 可靠**，因为后者对高基数特征（`period_id` 有 96 个取值）有系统性偏好，会骗你。
4. **特征别删太狠**。只有 15 个左右，不存在维度灾难。解释"每个特征为什么在"的收益远大于删特征的收益。

---

## 8. 第七步：误差分析（1 天，**拿高分的关键，也是报告第 6、7 章的主要素材**）

### 8.1 为什么误差分析比调模型重要

任务书第 7 条单列了误差分析，规范 §4.3 又把"误差集中的小时/星期/波动区间"列为必写的发现。一个 MAE=25 但能说清"我在晚高峰和负价段失效"的报告，比 MAE=22 但只会说"随机森林更好"的报告分高得多。

### 8.2 四张必做的分解图

```python
res = test_df.assign(err = yhat - y, abs_err = np.abs(yhat - y))
```
**图 A：按 `period_id`（96 点）的平均绝对误差曲线**
→ 大概率**晚高峰 17-21 点误差最大**。解释：峰谷切换快，`lag1` 的惯性假设在爬坡段失效。

**图 B：按 `dow` 的误差箱线图**
→ 看周末是否更差（周末负荷形态不同；但脱敏后周内结构可能被扰动，注意措辞）。

**图 C：按真实价格分位桶的误差柱状图**
```python
res["bucket"] = pd.qcut(res["y"], 10, labels=False)
res.groupby("bucket")["abs_err"].mean().plot.bar()
```
→ 大概率**两端（最低分位含负价、最高分位含尖峰）误差最大，中间最小**。典型的**重尾导致的条件异方差**。解释：模型在中间区域很准，在尾部既缺信息又缺样本。

**图 D：按波动率分桶的误差**
```python
res["vol_bucket"] = pd.qcut(res["roll_std_96"], 5, labels=False)
```
→ 高波动时段误差显著更大。结论很实用："**模型的可靠性依赖市场平静程度**。"

### 8.3 三个必做的案例研究

1. **误差最大的单日**：画当天 96 点真实 vs 预测。区分"整体偏移"（水平错了）、"形态错了"（峰谷错位）、"单点尖峰没抓到"。
2. **负价时段**：把 y<0 的样本单独拎出来，看模型是否预测成正值（大概率是）。结论："模型对负价几乎无识别能力，因为负价仅占 0.7%/2.8%，且由数据中不存在的因素（新能源出力）驱动。"
3. **DA-RT 价差最大的日子**：说明跨市场信息在这类日子更值钱（如果做了 DA→RT 特征实验）。

### 8.4 残差诊断（两个小检查，很显专业）

```python
# ① 残差是否还有自相关（有 → 模型漏了结构）
print(pd.Series(res["err"]).autocorr(lag=1))
# ② 残差是否随预测值系统性偏移（有 → 模型有偏）
res.plot.scatter(x="yhat", y="err", s=2)
```
**若残差 lag1 自相关 > 0.3**，说明没吃干净时序结构，可加 `lag3`、`lag8` 试试。**若散点呈漏斗形**，说明误差随价格放大——正好印证 8.2 图 C。

### 8.5 一个高级但便宜的加分项：误差的统计显著性

两个模型 MAE 差 1.5，是真差异还是噪声？用**成对 bootstrap**：

```python
d = np.abs(e1) - np.abs(e2)          # 逐样本误差差
bs = [np.mean(np.random.choice(d, len(d), replace=True)) for _ in range(2000)]
print(np.percentile(bs, [2.5, 97.5]))   # 若区间不含 0，则差异显著
```
不用装任何库，20 行代码。报告里写"bootstrap 95% 置信区间 [0.3, 2.7]，不含 0，差异显著"，**专业度立刻上一档**。

---

## 9. 第八步：写报告（1 天，按规范 §4 的 9 章结构）

### 9.1 报告结构：9 章，一章不能少

`reports/final_report.md`，图表放 `reports/figures/`（PNG 或 SVG）：

| 章 | 标题 | 内容来源 | 篇幅建议 |
|---|---|---|---|
| 1 | 问题定义与预测目标（跨度及理由） | §4 任务定义卡 | 0.5 页 |
| 2 | 数据说明与检查（范围、粒度、连续性、缺失、异常） | §2 体检表 + §3 图 1 | 1 页 |
| 3 | 特征构造与可用性（每个特征在 t0 是否可用） | §5.2 特征清单表 | 1.5 页 |
| 4 | 数据划分与方法（时间切分、基线、模型设置） | §6 示意图 + §7 参数表 | 1 页 |
| 5 | 结果与模型比较（MAE、RMSE，分市场呈现） | §7.6 对比表 | 1.5 页 |
| 6 | 误差分析（分小时、星期、波动条件） | §8.2 四张图 | 2 页 |
| 7 | **发现与学习（重点章节，≥正文 1/3）** | §9.2 | **3~4 页** |
| 8 | 局限与改进方向 | §9.3 | 1 页 |
| 9 | 复现说明（环境、命令、随机种子、模型版本） | **规范 §2.3 要求** | 0.5 页 |

**第 9 章别写空话**，写成这样：

```
环境：conda env create -f environment.yml（环境名 electricity-price，Python 3.12）
命令：conda activate electricity-price
      python src/train.py --market DA --model rf --seed 42
      python src/evaluate.py --market DA --model models/rf_v1.joblib
随机种子：42（src/config.py: SEED）
模型版本：models/rf_v1.joblib + models/rf_v1.meta.json（git tag model-v1.0）
报告生成：jupyter nbconvert --execute notebooks/04_errors.ipynb
```

### 9.2 「发现与学习」怎么写（这是全文最重要的 3~4 页）

规范 §4.3 给了硬指标：**篇幅 ≥ 正文 1/3，≥3 条发现 + 3 条学习，每条发现必须有图或指标支撑，不得写成调参流水账，禁止"效果不错""还需努力"这类空泛表述。**

#### 发现的写法：一句结论 + 一个数字 + 一张图

格式固定成：**"现象（数字，图 N）→ 解释 → 是否可推广"**。

给你 5 条现成的候选发现（都来自我实测的数据，你验证后可直接用）：

1. **"日内形态的解释力远低于预期：96 点均值曲线的 MAE（100.4）与全局均值（101.5）几乎相同（图 4 / 表 3）。这说明价格的水平漂移而非日内形状才是主要变异来源，也解释了为什么单纯的时间特征模型表现接近常数预测。"**
2. **"RT 的可预测性显著低于 DA：同样用 lag1，DA MAE=23.0，RT MAE=53.9（表 3）。这与两市场机制一致——RT 是偏差驱动的平衡市场，其波动本身来自预测误差，因此更具随机性。"**
3. **"模型在价格尾部系统性失效：按真实价格十分位分组，最高与最低分位的 MAE 是中间分位的 X 倍（图 8）。最低分位含负价（DA 264 条、RT 602 条），最高分位含尖峰（RT 641 条 ≥1000），两类样本在训练集中占比不足 3%，且由数据中不存在的外生因素驱动。"**
4. **"树模型在尖峰上系统性低估：测试期最大真实值 1798.7，而随机森林预测上界为 Y（图 9）。这是树模型只能插值、不能外推的结构性限制，不是调参问题；线性模型在同一区间的预测更接近真实值，但代价是中间区间的方差更大。"**
5. **"误差随波动率单调上升：前 24h 滚动标准差最高五分位的 MAE 是最低分位的 X 倍（图 10）。这意味着模型可靠性依赖于市场平静程度，实际使用时应以波动率作为置信度的代理指标。"**

**格式红线**：每条都要写成"结论句 + 数字 + 图号"，不能只写"RT 更难预测"。

#### 学习的写法：方法层、失败层、边界层各一条

规范要求"至少 3 条具体的学习体会"，建议按这三层组织，每层一条：

**方法层**（你踩过并解决的技术点）：
> "时间序列的切分不是形式问题。我最初的随机切分给出 MAE=6.2，看起来很好；改为按天切分 + 1 天 embargo 后升到 23.x。差距不是模型变差，而是前一个数字根本没有意义——它衡量的是'模型记住邻居的能力'。这让我理解到：**评估协议本身就是方法的一部分，不能事后补。**"

**失败层**（试过但没用的方案 + 原因）：
> "我尝试加入 `month` 特征捕捉季节性，验证集 MAE 反而上升 1.8。原因是数据经过 364 天日期平移，节假日对应关系已被打乱，`month` 与真实季节负荷不再对齐，学到的是噪声。**结论：脱敏数据上的日历特征不能按常规经验使用。**"

**边界层**（对结果能证明什么的认识）：
> "即使 MAE 降到 20 左右，这个数字也不能证明'可以用于交易'。三个原因：一是没有 `publication_time`，滞后特征的可用性只是教学假设；二是缺少负荷/新能源/天气，事件性尖峰在原理上不可预测；三是测试期仅 78 天（DA）/ 46 天（RT），未覆盖完整年周期。**本实验证明的是方法链路可跑通，而非预测能力可用于生产。**"

**再补一条"如果重做"**（规范明确要求）：
> "如果重做一次，我会优先做三件事：① 先写特征可用性表再写代码，避免中途发现特征不可用而返工；② 用 walk-forward 4 折替代单次切分，让结论不依赖某次切分的运气；③ 一开始就把 `period_sin/cos` 与 `lag1` 拆成两组做消融，而不是全量特征一把梭。"

### 9.3 第 8 章「局限与改进方向」：四条必写

1. **可用性局限**：无 `publication_time`，滞后特征可用性仅为教学假设。
2. **脱敏局限**：日期减 364 天，节假日对应关系错位，**不得推断真实节假日价格规律**。
3. **信息局限**：无负荷/风电/光伏/天气/检修/阻塞，事件性尖峰在原理上不可预测。
4. **样本局限**：DA 387 天、RT 227 天，测试期只有 78/46 天，未覆盖完整年周期；RT 窗口嵌套在 DA 内，两市场对比受限于交叠期。

**改进方向**（各写一句，别展开）：
- 若能拿到 `publication_time`，可做严格的信息集检验；
- 若能拿到负荷/新能源预测，可显著改善峰谷段误差；
- 分位数回归可给出预测区间，比点预测更适合报价决策；
- walk-forward + 多切分点敏感性分析可提升结论稳健性。

### 9.4 不要写的三句话（写了会扣分）

- "模型准确率达到 95%" —— 回归任务没有"准确率"，只有误差。
- "随机森林比线性回归好，因为随机森林更先进" —— 要说"因为存在非线性交互/阈值效应"。
- "如果加入天气数据效果会更好" —— 可以说"受限于数据无法验证"，但不能假装验证过。

---

## 10. 交付物清单（对齐规范 §3.2 的三类提交内容）

### 10.1 模型类（提交到 `models/`）

| 文件 | 内容 | 要点 |
|---|---|---|
| `models/rf_v1.joblib` | 训练好的模型对象 | 用 `joblib.dump(model, ...)`；**连特征名一起存**，避免上线时列序错乱 |
| `models/rf_v1.meta.json` | 元数据 | 见下方模板 |

```json
{
  "model": "RandomForestRegressor",
  "market": "DA",
  "horizon": 1,
  "features": ["lag1","lag2","lag4","lag96","lag192","roll_mean_4","roll_std_96","period_id","period_sin","period_cos","dow","is_weekend"],
  "params": {"n_estimators": 400, "min_samples_leaf": 5, "max_features": 0.5},
  "seed": 42,
  "train_range": ["2024-07-02", "2025-05-06"],
  "test_range": ["2025-05-07", "2025-07-23"],
  "metrics": {"mae": 0.0, "rmse": 0.0, "wape": 0.0},
  "baseline": {"name": "naive_lag1", "mae": 23.0, "rmse": 44.8},
  "env": "electricity-price (Python 3.12)",
  "git_tag": "model-v1.0"
}
```
**为什么必须写 meta**：三个月后你或队友打开 `rf_v1.joblib`，必须能一眼看出"这是哪个市场、什么跨度、用了哪些特征、指标多少、和谁比的"。规范要求"模型文件命名清晰，附有元数据与评估指标"，就是这件事。
**大小限制**：模型超过 50MB 用 Git LFS 或只留最终模型（规范 §3.2）。随机森林 400 棵通常 10~80MB，**建议 `min_samples_leaf=5` + 控制树深**，别让模型膨胀。

### 10.2 源代码类（提交到 `src/`、`notebooks/`、根目录）

- `src/` 七个模块（见 §1.2）
- `notebooks/` 四个 notebook（**提交前清空输出**，见附录 B.3）
- `environment.yml`、`.gitignore`、`README.md`

### 10.3 报告类（提交到 `reports/`）

| 文件 | 内容 |
|---|---|
| `reports/final_report.md` | 9 章正文，含「发现与学习」 |
| `reports/figures/fig01~fig10.png` | 300 dpi，文件名带编号与含义 |
| `reports/tables/model_comparison.csv` | 模型对比表（供正文引用） |
| `reports/tables/error_by_hour.csv` | 分时段误差表 |

图命名建议：`fig07_error_by_period.png`、`fig08_error_by_price_bucket.png` —— **图号与正文引用必须一致**，规范要求"每条发现须给出对应图表或指标"，图号乱了整段就废了。

### 10.4 如果要做汇报 PPT（10-12 页）

```
P1  标题 + 一句话结论（先说结论，别卖关子）
P2  数据是什么：2 市场 / 58,944 行 / 15 分钟粒度（1 表 + 1 小图）
P3  数据体检：8 项检查全过（1 表）
P4  看见了什么：全期曲线 + 日内 96 点均值（2 图并排）
P5  为什么难：重尾 + 负价 + 尖峰（分布图 + 数字）
P6  任务定义：h=1 主 / h=96 对照 + 信息集图
P7  特征怎么来的：ACF → lag1/lag96 的证据链（ACF 图）
P8  怎么切分：时间切分 + embargo（示意图）
P9  谁赢了：模型对比表（高亮最优）
P10 哪里错了：误差分解 4 图（挑 2 张最有说服力的）
P11 一个失败案例：最大误差日的曲线（真实 vs 预测）
P12 结论 + 4 条限制 + 一句话"这意味着什么"
```

**答辩高频追问**（准备好）：
- 为什么不用随机切分？
- 为什么不删负价？
- 为什么树模型在尖峰上总是低估？
- 你的 lag1 特征在真实市场里拿得到吗？（答：教学假设，无法证明）
- 为什么 MAE 和 RMSE 的模型排序可能不一致？（答：一个对应中位数、一个对应均值）

---

## 11. 七天时间表（含 Git 动作，按这个走不会崩）
h
| 天 | 任务 | 产出 | Git 动作 | 卡点提示 |
|---|---|---|---|---|
| D1 上午 | 按附录 A 建 conda 环境；建仓库与目录 | `environment.yml` 跑通 | `chore(env): 初始化 electricity-price 环境` | ToS 报错见附录 A.4 |
| D1 下午 | 数据体检 | 体检表 | 分支 `feat/data-check` → 合并 | 时区解析见 §12 第 1 条 |
| D2 上午 | EDA 图 1-4 | 4 张图 | 分支 `feat/eda` | 别急着建模 |
| D2 下午 | EDA 图 5-7 | 3 张图 | 同上，合并 | ACF 手算即可 |
| D3 上午 | 任务定义卡 + 可用性假设 | 半页（报告第 1 章） | 分支 `report/draft` | 这段文字值得反复改 |
| D3 下午 | 特征工程 + 特征清单表 | `src/features.py` | 分支 `feat/features-lag` | 务必先写单测验证无泄漏 |
| D4 上午 | 4 个基准 + 切分 | 基准表 | 分支 `feat/baseline` | 和 §7.1 数量级对齐 |
| D4 下午 | Ridge + RF | 首版模型表 | 分支 `exp/ridge-rf` | MAE 远高于基准先查排序和 lag |
| D5 | GBDT + 调参 + 置换重要性 | 最终模型表 + `models/*` | `exp/gbdt` → `model(rf): ...` + `git tag model-v1.0` | 只在验证集调 |
| D6 | 误差分析 4 图 + 3 案例 | 误差章素材 | 分支 `report/error-analysis` | 最花时间，别压缩 |
| D7 上午 | 写「发现与学习」+ 局限 | 报告 7、8 章 | 同上 | **必须 ≥3 发现 + 3 学习** |
| D7 下午 | 复现检查 + PPT + 打标签 | 全部交付 | `report(results): ...` + `git tag report-v1.0` | 换台机器重跑一遍 |

**每天结束前的 30 秒**：`git status` 看有没有漏提交的文件，`git log --oneline -5` 看提交信息是否可读。

---

## 12. 二十三个坑（每一条都有人栽过）

**数据与解析**
1. **时区**：`delivery_time` 带 `+08:00`。用 `pd.to_datetime(..., utc=True).dt.tz_convert("Asia/Shanghai")`。直接 `parse_dates` 在某些 pandas 版本会退化成 object。
2. **`trade_date` 与 `delivery_time.date()` 必须相等**。脱敏是把两者同时减 364 天，不等就说明解析错了。
3. **`period_id` 从 1 开始，不是 0**。写 `period_id-1` 的地方要想清楚。
4. **RT 只有 227 天，DA 有 387 天**。做 DA-RT 对比必须 `dropna()` 取交集（21,792 对），不能直接相减。

**特征与泄漏**
5. **先 `groupby("market_type")` 再 `shift`**。否则 RT 首行拿到 DA 末行。
6. **`rolling()` 后必须 `shift(1)`**。否则包含当期 = 目标泄漏。
7. **`shift(-h)` 方向别搞反**。`shift(-1)` 是"下一行"（未来），`shift(1)` 是"上一行"（过去）。搞反了模型会好到不真实。
8. **不要在 `dropna()` 之前用全量数据算标准化/填充**。scaler 只能 fit 在训练集上。
9. **`lag96` 的 NaN 不要插值**，直接删前 96 行。插值 = 编造历史。
10. **跨市场特征要单列实验**。把 DA(t) 塞进 RT 模型，要明确标出并单独对比"有/无"。

**切分与评估**
11. **绝不随机切分**（§6.1）。
12. **绝不无 gap 切分**（§6.2）。
13. **绝不用测试集调参**。
14. **`GridSearchCV` 要传 `TimeSeriesSplit`**，默认 KFold 会泄漏。
15. **不要用 MAPE**（负价/零价）。
16. **MAE 与 RMSE 的模型排序可能不一致**，这不矛盾：MAE 对应条件中位数，RMSE 对应条件均值，重尾时后者被尖峰主导。报告里解释一句，反而是亮点。
17. **跨市场比较 MAE 无意义**（RT 天生更难）。要比就用 WAPE，或只在同市场内比。

**建模与解释**
18. **树模型不能外推**。别试图调参解决"尖峰低估"，要写进限制。
19. **`feature_importances_` 有高基数偏好**，用 permutation importance。
20. **随机种子**。`random_state` 设在 `config.py`，所有模型都传。

**规范与协作**
21. **别 `git add .`**。`data/`、`outputs/`、`.venv/`、`.ipynb_checkpoints/` 一旦进历史，清理起来要 `filter-repo`。先写好 `.gitignore`（附录 B.1）再第一次提交。
22. **别把数据或大文件提交**。`*.csv`、`*.zip`、>50MB 模型都在禁列（规范 §3.2）。报告只写统计特征，不附原始记录（规范 §6）。
23. **别忘记同步 `environment.yml`**。你在环境里 `pip install` 了某个包但没写进 yml，队友建完环境就跑不动。规范 §2.3 要求依赖变更单独提交——**每次加包，单独一个 `chore(deps):` 提交**。

**报告层面**
24. **不要用脱敏日期推断节假日**。减 364 天后节假日全错位。可以说"存在周内效应"，不能说"春节前后价格高"。
25. **不要声称"可用于生产"**（任务书明令限制）。
26. **不要删负价和尖峰来"改善"指标**——删了就是在改题。

---

## 13. 进阶加分项（有余力再做，任一都能加分）

| 加分项 | 怎么做 | 为什么加分 |
|---|---|---|
| **预测区间** | `GradientBoostingRegressor(loss="quantile", alpha=0.1/0.9)` 训两个模型 | 从点预测升到不确定性量化，业务上更有用 |
| **DA→RT 传递** | RT 模型加 `DA(t)` 特征，对比有/无 | 体现市场机制理解；且是本数据唯一能论证可用性的特征 |
| **误差的统计检验** | 成对 bootstrap 或 Diebold-Mariano | 证明"模型 A 真好于 B"，而非运气 |
| **分时段建模** | 只对晚高峰 17-21 点单独训一个模型 | 说明你发现误差集中区并针对性处理 |
| **切分敏感性** | 换 3 种切分点（70/80/90%）看结论是否稳 | 证明结论不依赖某次切分的运气 |
| **分位变换对比** | 因有负价，试 `asinh(y)` 变换 | 展示你知道"log 不能用于负值"这个细节 |
| **特征消融** | 去掉 lag1 / 去掉 lag96 / 去掉日历，各跑一次 | 用实验而非猜测回答"哪个特征真重要" |

---

## 14. 一句话总结这份方案的设计逻辑

> **先证明数据可信（§2），再用图看清结构（§3），然后把"预测什么、什么时候能知道什么"钉死（§4），
> 接着用 ACF 的证据选特征（§3.6→§5），用时间切分保证评估诚实（§6），
> 用 4 个基准+3 个模型做可证伪的比较（§7），
> 再到误差分解里回答"模型在哪里失效、为什么"（§8），
> 最后按规范的 9 章结构把它写成报告，把「发现与学习」当作真正的交付物（§9）。**

建模只占 1.5 天，其余时间都在"把问题说清楚"和"把过程管好"——这正是这门课和这份团队规范想教的东西。

---

# 附录 A：Mac 环境部署（Conda 版，对齐规范 §2）

## A.1 你这台机器的现状（我已实测）

| 项目 | 状态 | 说明 |
|---|---|---|
| 芯片 / 系统 | arm64 (Apple Silicon) / macOS 26.6.2 | 新系统，无兼容问题 |
| Homebrew | 已装 6.0.15（`/opt/homebrew`） | 省一步 |
| conda | 已装 26.5.3，**base 在 `/opt/homebrew/Caskroom/miniconda/base`** | 可用，但**尚未初始化**（见 A.3 第 1 步） |
| **conda 的 zsh 初始化** | **未做**（`~/.zshrc` 里没有 `conda initialize` 段） | 直接 `conda activate` 会报 `CommandNotFoundError` |
| conda 默认通道 | `defaults`（指向 `repo.anaconda.com`） | 会触发 **Terms of Service 报错**，见 A.4 |
| VS Code | 已装，`code` 命令可用 | 主力编辑器 |
| git | 2.54.0 | 够用 |
| Jupyter | 未安装 | 建环境时装 |
| 默认 `python3` | 3.13.12，在 `~/.workbuddy/binaries/...` | **工具链自带，绝不往里装包** |
| Homebrew 的 `python3` | 3.14.6 | 太新，科学计算轮子滞后，**别用** |
| 磁盘 | 剩 758 GB | 够，整套环境约 1.5 GB |

**三个必须避开的坑**：
1. 你终端里的 `python3` 指向工具链目录，**直接 `pip install` 会写脏它**。
2. Homebrew 的 Python 3.14 装 numpy/scipy 大概率触发源码编译，报一屏 C 错误——**所以 yml 里锁 `python=3.12`**。
3. conda 没初始化过，`conda activate` 现在是坏的——**必须先 `conda init zsh`**。

## A.2 为什么用 conda，而不是 venv/uv

上一版我建议过 uv + venv（确实更快）。但规范 §2.1 明确要求：**独立 Conda 环境、环境名 `electricity-price`、依赖全部写进 `environment.yml`、禁止在 base 装包**。这是团队协作的硬约定，不是风格偏好——队友拿到仓库要能 `conda env create -f environment.yml` 一键复现。**所以以规范为准，改用 conda。**

uv 仍可留作你个人临时试验（比如试某个包快不快），但**不能作为项目环境**，否则你的 `environment.yml` 和实际环境就对不上了。

## A.3 从零到能跑：六步

```bash
# ① 初始化 conda 到 zsh（只需一次）
conda init zsh

# ② 重开 shell，让 conda activate 生效
exec zsh
conda --version          # 确认还能用
conda activate base      # 应该不再报 CommandNotFoundError

# ③ 建仓库目录（与课程数据目录分开，见 §1.2）
mkdir -p ~/Projects/electricity-price
cd ~/Projects/electricity-price
mkdir -p src notebooks models reports/figures data docs outputs

# ④ 把数据拷进来（仅本地，已在 .gitignore）
cp ~/Downloads/electricity_price_course_data/data/student_dataset.csv data/

# ⑤ 写好 environment.yml（全文见 A.5），然后建环境
conda env create -f environment.yml

# ⑥ 激活并验证
conda activate electricity-price
python -c "import sys,pandas,sklearn;print(sys.version.split()[0],pandas.__version__,sklearn.__version__)"
```

第 ⑥ 步应输出 `3.12.x 2.x.x 1.x.x`。**报 `ModuleNotFoundError` 说明第 ⑥ 步的 `conda activate` 没生效**（提示符前应有 `(electricity-price)`）。

**再补一步：注册 Jupyter 内核**（否则 notebook 里选不到这个环境）：

```bash
python -m ipykernel install --user --name electricity-price --display-name "Python (electricity-price)"
```

## A.4 你会遇到的三个 conda 专有报错

**① `CommandNotFoundError: Your shell has not been properly configured to use 'conda activate'`**

原因：conda 装好后没跑过初始化。解法：

```bash
conda init zsh
exec zsh          # 或关掉终端重开
```
**注意**：`conda init` 会往 `~/.zshrc` 追加一段 `# >>> conda initialize >>>`。这是正常的，别删。

**② `CondaToSNonInteractiveError: Terms of Service have not been accepted`**

原因：conda 26 起对 `defaults` 通道（`repo.anaconda.com`）要求接受服务条款。我在你机器上实测，**即使 `environment.yml` 里只写 `conda-forge`，只要全局配置里还有 `defaults`，这个报错就会出现**。

两个解法，任选其一：

```bash
# 解法一（官方推荐，一次性）：接受两个默认通道的条款
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```
```bash
# 解法二：彻底不用 defaults，只走 conda-forge
conda config --add channels conda-forge
conda config --set channel_priority strict
# 之后建环境时显式覆盖通道：
conda env create -f environment.yml --override-channels
```
**建议解法一**，因为 `environment.yml` 里写了 `nodefaults` 后队友那边也可能报同样的错，接受一次最省事。

**③ `Solving environment: failed` 或解依赖卡住十几分钟**

原因：`defaults` 与 `conda-forge` 混用导致求解空间爆炸。解法：`environment.yml` 里加 `nodefaults`（A.5 已加），并设 `channel_priority strict`。

## A.5 `environment.yml` 全文（可直接用）

```yaml
name: electricity-price
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python=3.12
  - numpy=2.*
  - pandas=2.*
  - scikit-learn=1.*
  - matplotlib=3.*
  - seaborn=0.13.*
  - jupyterlab=4.*
  - ipykernel=6.*
  - joblib=1.*
  # 可选：做 ACF/PACF 图或 DM 检验时才需要
  # - statsmodels=0.14.*
```

**四条设计说明，都是规范要求的：**

1. **`python=3.12` 固定版本**（规范 §2.1(3)：固定 Python 版本）。不要写 `python=3`，那样队友可能拿到 3.13/3.14，行为不一致。
2. **关键依赖固定主版本**（`numpy=2.*` 而不是 `numpy`）。规范原文："关键依赖应固定主版本，保证他人可复现"。不锁的话，半年后 `conda env create` 可能装出行为不同的新版本，`RandomForestRegressor` 的默认值都可能变。
3. **`nodefaults` 必须有**。否则 `defaults` 会被隐式加入，触发 A.4 的 ToS 报错和求解变慢。
4. **不要写 `pip:` 段**。规范 §2.1(2)："禁止仅通过本地 pip install 隐式添加依赖"。全部走 conda-forge，`environment.yml` 就是唯一真相源。

**依赖变更后的标准动作**（规范 §2.2 / §2.3）：

```bash
# 改了 yml 之后
conda env update -f environment.yml --prune
# 导出只含显式依赖的精简版（覆盖回 yml，便于 code review）
conda env export --from-history > environment.yml
# 单独提交，信息写清原因
git add environment.yml
git commit -m "chore(deps): 增加 seaborn 用于误差分布图"
```

**注意 `--from-history` 的副作用**：它只导出你**显式**装过的包，版本约束会退化成你输入时的写法（比如 `numpy` 不带版本）。所以导出后**手工检查一遍，把主版本约束补回去**，再提交。这一步很多人漏掉，结果 yml 越导越松。

## A.6 千万别做的 5 件事

| 别做 | 后果 |
|---|---|
| 在 `base` 环境 `conda install` 项目依赖 | 违反规范 §2.1(1)，且 base 坏了只能重装 miniconda |
| `sudo pip install xxx` | 污染系统 Python，出问题只能重装系统组件 |
| 往 `~/.workbuddy/binaries/python/...` 装包 | 工具链目录被写脏，其他自动化可能异常 |
| 用 Homebrew 的 Python 3.14 装 numpy/scipy | 大概率触发源码编译，报一屏 C 错误 |
| 把项目放 iCloud 同步目录（桌面/文稿） | Jupyter 自动保存与 iCloud 打架，偶发文件损坏。`~/Projects` 安全 |

## A.7 VS Code 配置（注意 `.vscode/` 不提交）

装 4 个插件（`Cmd+Shift+X`）：

| 插件 | 作用 | 必装 |
|---|---|---|
| **Python**（Microsoft） | 语法、调试、环境选择 | 是 |
| **Jupyter**（Microsoft） | 直接在 VS Code 跑 notebook | 是 |
| **Pylance** | 智能补全（装 Python 插件时通常自动带） | 是 |
| **Rainbow CSV** | CSV 按列上色，肉眼查数据 | 强烈建议 |

**关键一步**：`Cmd+Shift+P` → `Python: Select Interpreter` → 选 `electricity-price`（conda 环境）。
**不做这步，就会出现"终端能跑、notebook 报 ModuleNotFoundError"的经典怪象。**

**`.vscode/` 已在 `.gitignore` 里**（规范 §3.2 禁止提交个人 IDE 配置）。但 `settings.json` 里选解释器的记录其实是**本机绝对路径**，本来也不该提交——所以别为了"方便队友"把 `.vscode/` 加进版本控制，正确做法是写进 `README.md`：`请选择 conda 环境 electricity-price`。

## A.8 Mac 必配的 matplotlib 中文（否则图里全是方框）

在 `src/plots.py` 顶部或 notebook 第一格：

```python
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False   # 负号才能正常显示
```

`PingFang SC`（苹方）macOS 自带，**不要**去网上下字体，也不要用 `SimHei`（那是 Windows 的）。
第二行是解决"负价 −50 显示成方框"的——你这批数据有负价，**一定会遇到**。

**另一个细节**：`savefig` 时用 `dpi=300, bbox_inches="tight"`，否则图进 Word/PPT 会糊。规范要求图放 `reports/figures/`，文件名带编号。

## A.9 环境验证脚本（30 秒确认能开工）

新建 `src/check_env.py`：

```python
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
```

期望看到 `shape : (58944, 5)` 和末尾 `OK`。
**这一步过了，才说明"环境 + 数据 + 时区解析"三件事同时正确**——顺手把 §2 的体检也验了一半。

## A.10 Mac 常见报错对照表

| 报错 | 原因 | 解法 |
|---|---|---|
| `CommandNotFoundError: conda activate` | conda 未初始化 | `conda init zsh` + `exec zsh`（A.4①） |
| `CondaToSNonInteractiveError` | `defaults` 通道 ToS 未接受 | A.4② 的两个 `conda tos accept` |
| `Solving environment` 卡很久 | 通道混用 | yml 加 `nodefaults` + `channel_priority strict` |
| `zsh: no matches found: numpy=2.*` | zsh 把 `*` 当通配符 | 命令里给规格加引号 `"numpy=2.*"`（写进 yml 则无此问题） |
| `ModuleNotFoundError: No module named 'pandas'` | 没激活环境 / VS Code 解释器没选 | `conda activate electricity-price`；`Select Interpreter` |
| 终端能 import，notebook 不能 | Jupyter kernel 选错 | 跑 A.3 的 `ipykernel install`，再选 `Python (electricity-price)` |
| `zsh: command not found: python` | 环境未激活 | 激活后用 `python`；或一直用 `python3` |
| `OSError: dlopen ... libomp.dylib` | xgboost/lightgbm 缺 OpenMP | `brew install libomp`（只在装 xgboost 时需要） |
| 图里中文变方框 | 没配字体 | A.8 那两行 |
| `datetime` 解析成 object | 时区字符串混合 | `pd.to_datetime(..., utc=True)` 再 `tz_convert` |

---

# 附录 B：直接可用的配置文件与命令

## B.1 `.gitignore` 全文（按规范 §3.2 扩写）

```gitignore
# 数据（规范：原始/派生数据一律不提交）
electricity_price_course_data/
data/
*.csv
*.zip
*.xlsx

# 输出与缓存
outputs/
*.log
__pycache__/
.ipynb_checkpoints/
.cache/
.pytest_cache/

# 环境与 IDE（含绝对路径的配置一律不提交）
.conda/
.venv/
.vscode/
.idea/

# 系统文件
.DS_Store
Thumbs.db

# 模型大文件（>50MB 走 LFS，否则不提交）
models/*.h5
models/*.pkl.large
```

**两条说明：**
1. `*.csv` 会把 `reports/tables/*.csv` 也忽略掉。**如果你要把结果表提交进 `reports/tables/`**，用取反规则放行：
   ```gitignore
   !reports/tables/*.csv
   ```
   报告要引用的结果表属于"报告"类内容，应当提交。
2. `models/*.joblib` **不要**加进忽略列表——模型是规范允许提交的三类内容之一。只用大小控制（>50MB 用 LFS）。

## B.2 仓库初始化命令（一次性）

```bash
cd ~/Projects/electricity-price
git init -b main

# 先写 .gitignore（B.1），再放任何文件进去
# 然后把 environment.yml / README.md / src/ 等准备好

git add .gitignore environment.yml README.md
git commit -m "chore(init): 初始化项目骨架与 conda 环境定义"

git switch -c feat/data-check
# ... 做数据体检 ...
git add src/io.py notebooks/01_eda.ipynb
git commit -m "feat(data): 增加数据体检脚本与连续性校验"
git switch main && git merge --ff-only feat/data-check
```

**顺序很重要**：`git init` 之后、`git add` 之前，`.gitignore` 必须已经存在并且内容正确。否则 `git add .` 一把梭会把 `data/` 和 `outputs/` 全带进去，之后要用 `git filter-repo` 才能清干净——那是新手最不该踩的坑。

## B.3 提交前清空 notebook 输出（可选但强烈建议）

Notebook 的输出会进 Git，一张图就能让 diff 变成几 MB 二进制。两个做法：

```bash
# 做法一：清空后再存盘（不装任何东西）
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb

# 做法二：装 nbstripout 做成 git 过滤器（一次配置，之后自动）
conda activate electricity-price
conda install -c conda-forge nbstripout   # 记得同步 environment.yml
nbstripout --install
```

**注意**：做法二需要把 `nbstripout` 写进 `environment.yml` 并单独提交（规范 §2.3 要求依赖变更单独提交）。

## B.4 提交信息模板（直接抄，改数字）

```
feat(data): 增加数据体检脚本与连续性校验

校验每日 96 点、15 分钟间隔、时段号自洽、重复时间戳。
DA 37152 行 / RT 21792 行，全部通过；未做插值或删点。

feat(features): 分市场构造滞后与滚动特征

按 market_type 分组后排序再 shift，避免跨市场污染。
rolling 统一 shift(1) 排除当期，防止目标泄漏。
lag96 前 96 行 NaN 直接丢弃，不插值。

fix(split): 修正时间切分中的未来信息泄漏

原实现随机打乱样本，导致测试集信息进入训练集。
改为按天顺序切分，并在切点间留 1 天 embargo。

exp(rf): 对比 min_samples_leaf 取 5 与 20

固定 SEED=42，按天切分 + 1 天 embargo。
leaf=5 验证集更优（DA MAE 24.1 vs 25.8），采用 leaf=5。

model(rf): 保存随机森林最终模型与评估结果

DA 测试集 MAE=23.8，RMSE=46.1；RT 测试集 MAE=55.2，RMSE=108.7。
对比 lag1 基线（23.0 / 53.9），DA 未优于基线，原因见报告 7.3。

report(results): 补充分时段误差分析与发现学习

新增小时、星期、波动条件三张误差图（fig07-fig09），
在"发现与学习"中记录 4 条发现、3 条学习。

chore(deps): 增加 seaborn 并同步 environment.yml
docs(readme): 补充环境创建与复现命令
```

**写 `model` 类提交时注意**：规范明确要求"涉及模型时须写明关键指标（如 MAE、RMSE）及对比基线"。**即使结果不如基线也要如实写**——"DA 未优于基线，原因见报告 7.3"比含糊其辞专业得多。

## B.5 提交前 9 项检查（对齐规范 §5）

```
[ ] 已在 electricity-price 环境中从零跑通相关脚本 / Notebook
[ ] environment.yml 已同步最新依赖（没有偷偷 pip install 未记录的包）
[ ] 暂存区仅包含 模型 / 源代码 / 报告 三类内容（git status 逐条看过）
[ ] 未提交数据、输出、缓存、IDE 配置或敏感信息
[ ] 模型文件命名清晰（rf_v1.joblib），且有 *.meta.json 与指标
[ ] 报告已更新图表、指标与「发现与学习」章节
[ ] 提交信息符合 <type>(<scope>): <subject>
[ ] 提交粒度单一（一次只做一件事）
[ ] 重要模型或报告已打标签（model-v1.0 / report-v1.0）
```

---

## 附录 C：你现在就可以照做的前 6 条命令

```bash
# 1. 初始化 conda（你那台机器还没做过）
conda init zsh && exec zsh

# 2. 建仓库目录
mkdir -p ~/Projects/electricity-price && cd ~/Projects/electricity-price
mkdir -p src notebooks models reports/figures data docs outputs
git init -b main

# 3. 写入 .gitignore（附录 B.1）与 environment.yml（附录 A.5）后：
cp ~/Downloads/electricity_price_course_data/data/student_dataset.csv data/
cp ~/Downloads/electricity_price_course_data/IMPLEMENTATION_PLAN.md docs/

# 4. 建环境
conda env create -f environment.yml

# 5. 激活 + 注册内核
conda activate electricity-price
python -m ipykernel install --user --name electricity-price --display-name "Python (electricity-price)"

# 6. 首次提交（此时 .gitignore 已生效，data/ 不会被带走）
git add .gitignore environment.yml docs/IMPLEMENTATION_PLAN.md
git commit -m "chore(init): 初始化项目骨架与 conda 环境定义"
git status        # 确认 data/ 是 Untracked 或已忽略
```
