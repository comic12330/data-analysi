# -*- coding: utf-8 -*-
"""
仿真平台 · 预测引擎

流程：读取 05 出力数据 -> 构造时间特征 -> 随机森林建模 -> 风机/光伏/负荷预测与评估
输入：data/05_风光负荷同步出力数据.csv
输出：platform/public/data/prediction_results.json
      figures/forecast_wind.png、forecast_pv.png、forecast_load.png

运行: D:\\Anaconda3\\envs\\data_analysis\\python.exe predict.py
"""
import os
import time
import json
import warnings

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, 'data')
OUT_DIR = os.path.join(BASE, 'platform', 'public', 'data')
FIG_DIR = os.path.join(BASE, 'figures')
for d in (OUT_DIR, FIG_DIR):
    os.makedirs(d, exist_ok=True)

print('=' * 60)
print('预测引擎 · 数据准备与特征工程')
print('=' * 60)

# ---------- 数据准备 ----------
df = pd.read_csv(os.path.join(DATA_DIR, '05_风光负荷同步出力数据.csv'))
df.columns = ['time', 'windSpeed', 'temp', 'ghi', 'wind', 'pv', 'load',
              'charge', 'discharge', 'soc', 'gridBuy', 'gridSell', 'curtail', 'balErr']

t = pd.to_datetime(df['time'], format='%Y/%m/%d %H:%M')
df['hour'] = t.dt.hour          # 一天内小时
df['month'] = t.dt.month        # 月份（季节性）
df['dow'] = t.dt.dayofweek      # 星期（工作日/周末特性）

FEATURES = ['windSpeed', 'ghi', 'temp', 'hour', 'month', 'dow']
print('数据集规模：%d 行 × %d 特征' % (len(df), len(FEATURES)))
print('时间范围：%s ~ %s' % (df['time'].iloc[0], df['time'].iloc[-1]))
print('特征字段：', '、'.join(FEATURES))
print('划分方式：时序 80%% 训练 / 20%% 测试（避免未来信息泄露）')


# ---------- 预测统一流程（三类预测复用） ----------
# 随机森林回归：无需特征缩放，可拟合非线性气象-出力关系
def run_forecast(name, target_col, color, fig_name):
    """统一预测流程：训练、评估、可视化、返回结果"""
    X = df[FEATURES].values
    y = df[target_col].values
    n = len(df)
    split = int(n * 0.8)
    Xtr, Xte = X[:split], X[split:]
    ytr, yte = y[:split], y[split:]

    mdl = RandomForestRegressor(n_estimators=100, max_depth=16, n_jobs=-1, random_state=42)
    t0 = time.time()
    mdl.fit(Xtr, ytr)
    pred = mdl.predict(Xte)
    elapsed = time.time() - t0

    mae = mean_absolute_error(yte, pred)
    rmse = mean_squared_error(yte, pred) ** 0.5
    r2 = r2_score(yte, pred)

    # 绘制测试集前 168 小时预测对比与散点图
    N = 168
    tt = t.dt.strftime('%m-%d %H:%M').values[split:split + N]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2))
    axes[0].plot(range(N), yte[:N], color='#888', lw=1.4, label='实际值')
    axes[0].plot(range(N), pred[:N], color=color, lw=1.4, alpha=0.85, label='预测值')
    axes[0].set_title('%s预测：测试集前168小时对比' % name)
    axes[0].set_xlabel('时间'); axes[0].set_ylabel('MW')
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[0].set_xticks(range(0, N, 24))
    axes[1].scatter(yte, pred, s=6, alpha=0.35, color=color)
    lim = [min(yte.min(), pred.min()), max(yte.max(), pred.max())]
    axes[1].plot(lim, lim, 'r--', lw=1, label='y = x')
    axes[1].set_title('%s预测：预测值-实际值散点' % name)
    axes[1].set_xlabel('实际值 (MW)'); axes[1].set_ylabel('预测值 (MW)')
    axes[1].legend(); axes[1].grid(alpha=0.3)
    plt.tight_layout()
    fig_path = os.path.join(FIG_DIR, fig_name)
    plt.savefig(fig_path, dpi=130)
    plt.close(fig)

    print('【%s预测】MAE=%.3f MW | RMSE=%.3f MW | R²=%.4f | 训练+预测耗时 %.1fs | 图: %s'
          % (name, mae, rmse, r2, elapsed, os.path.basename(fig_path)))
    return dict(name=name, mae=round(mae, 3), rmse=round(rmse, 3), r2=round(float(r2), 4),
                yte=yte, pred=pred, time=tt)


# ---------- 风机出力预测 ----------
print()
print('=' * 60)
print('预测引擎 · 风机出力预测')
print('=' * 60)
res_wind = run_forecast('风机出力', 'wind', '#1da972', 'forecast_wind.png')
print('结论：随机森林对风机出力测试集 R²=%.4f，MAE 仅 %.3f MW（额定出力的 %.2f%%）。'
      % (res_wind['r2'], res_wind['mae'], res_wind['mae'] / 80 * 100))
print('风机出力可由风速等气象特征高精度还原，验证"气象→功率曲线"映射的有效性。')

# ---------- 光伏出力预测 ----------
print()
print('=' * 60)
print('预测引擎 · 光伏出力预测')
print('=' * 60)
res_pv = run_forecast('光伏出力', 'pv', '#e89b2e', 'forecast_pv.png')
print('结论：光伏出力预测 R²=%.4f，MAE=%.3f MW。模型准确复现"白天钟形曲线、夜间归零"形态。'
      % (res_pv['r2'], res_pv['mae']))

# ---------- 负荷预测 ----------
print()
print('=' * 60)
print('预测引擎 · 负荷预测')
print('=' * 60)
res_load = run_forecast('负荷', 'load', '#3d7edb', 'forecast_load.png')
print('结论：负荷预测 R²=%.4f，MAE=%.3f MW（峰值负荷 %.1f MW 的 %.1f%%）。'
      % (res_load['r2'], res_load['mae'], df['load'].max(), res_load['mae'] / df['load'].max() * 100))
print('负荷随机波动高于风光出力，仍达较高精度，可支撑日前购电与储能充放电计划。')

# ---------- 输出结果 JSON ----------
def sample_series(r):
    N = 168
    return {'time': list(r['time'][:N]), 'actual': [round(float(v), 2) for v in r['yte'][:N]],
            'pred': [round(float(v), 2) for v in r['pred'][:N]]}


prediction_json = {
    'wind': {'mae': res_wind['mae'], 'rmse': res_wind['rmse'], 'r2': res_wind['r2'], **sample_series(res_wind)},
    'pv': {'mae': res_pv['mae'], 'rmse': res_pv['rmse'], 'r2': res_pv['r2'], **sample_series(res_pv)},
    'load': {'mae': res_load['mae'], 'rmse': res_load['rmse'], 'r2': res_load['r2'], **sample_series(res_load)},
}

out_path = os.path.join(OUT_DIR, 'prediction_results.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(prediction_json, f, ensure_ascii=False)

print()
print('预测引擎完成，结果已输出: %s' % out_path)
print('平台"智能优化"页预测评估板块将自动读取该文件。')
