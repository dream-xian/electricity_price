# electricity-price

电价预测课程项目：DA/RT 两个市场、15 分钟粒度。

## 环境

    conda env create -f environment.yml
    conda activate electricity-price
    python -m ipykernel install --user --name electricity-price --display-name "Python (electricity-price)"

## 数据

把课程提供的数据拷到本地（不进 Git）：

    mkdir -p data && cp ~/Downloads/electricity_price_course_data/data/student_dataset.csv data/

## 运行

    python src/check_env.py                       # 环境自检
    python src/train.py --market DA --h 1         # 训练 + 评估 + 出表
    python src/train.py --market RT --h 1
    python src/train.py --market DA --h 96        # 次日同时段（对照任务）

产物：`models/*.joblib`、`reports/tables/*.csv`、`reports/figures/*.png`。

## 复现

随机种子 42，定义在 `src/config.py`。所有切分按天顺序切，训练/验证/测试之间留 1 天 embargo。
