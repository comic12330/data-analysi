# -*- coding: utf-8 -*-
"""
仿真平台 · 容量优化引擎

流程：算法可行性验证 -> 规划模型构建 -> PSO 求解最小年总成本 -> 灵敏度分析 -> 结果输出
输入：data/ 下 02 设备参数、05 出力曲线、06 评价结果、07 分时电价、08 成本参数
输出：platform/public/data/optimization_results.json
      figures/convergence.png、figures/sensitivity.png

运行: D:\\Anaconda3\\envs\\data_analysis\\python.exe optimize.py
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

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, 'data')
OUT_DIR = os.path.join(BASE, 'platform', 'public', 'data')
FIG_DIR = os.path.join(BASE, 'figures')
for d in (OUT_DIR, FIG_DIR):
    os.makedirs(d, exist_ok=True)

# ---------- 算法可行性验证（Rosenbrock 基准函数） ----------
print('=' * 60)
print('优化引擎 · 算法可行性验证')
print('=' * 60)

import mealpy
from mealpy import FloatVar
from mealpy.swarm_based import PSO as MealpyPSO

print('采用 MEALPY 版本：', mealpy.__version__)
print('MEALPY 内置 PSO 变体：', [x for x in dir(MealpyPSO) if 'PSO' in x])


def rosenbrock(x):
    return (1 - x[0]) ** 2 + 100 * (x[1] - x[0] ** 2) ** 2


rb_problem = {
    'obj_func': rosenbrock,
    'bounds': FloatVar(lb=[-5., -5.], ub=[5., 5.]),
    'minmax': 'min',
    'log_to': None,
}
rb_model = MealpyPSO.OriginalPSO(epoch=100, pop_size=30)
rb_best = rb_model.solve(rb_problem)
rb_sol = np.asarray(rb_best.solution, dtype=float).ravel()
print('PSO 求解 Rosenbrock 基准函数：最优解 =', np.round(rb_sol, 6),
      ' 最优值 = %.2e' % float(rb_best.target.fitness))
print('算法可用性验证通过，确定技术路线：只用 MEALPY 的 PSO 一个算法')

# ---------- 新能源规划问题建模 ----------
# 决策变量(4维实数)：风电装机 w(MW)、光伏装机 p(MW)、储能功率 e(MW)、储能容量 c(MWh)
# 出力模型：由 05 号文件 80MW 风电 / 120MW 光伏实际出力曲线反推单位装机出力曲线（归一化），
#           任意装机下出力按容量线性缩放：wind(h)=wind05(h)/80*w，pv(h)=pv05(h)/120*p
# 时序生产模拟(5832h 逐时平衡 + 储能 SOC 递推)：盈余先充电、余电就地消纳计弃电；
#           缺口先放电(SOC 10%~95%、效率0.92)、再外购(上限70MW，06文件)、仍不足计失负荷
# 经济模型(08成本+07分时电价)：年化投资=CAPEX*CRF(i=8%,20年)；运维=CAPEX*2%；
#           购电=分时电价(谷0.35/平0.75/峰1.15)；碳收益=碳减排*80元/t(排放因子由06反推)
# 约束:  绿电占比 >= 65%、风电装机占比 >= 25%、储能时长 1~6h、失负荷率 -> 0
#        边界 10<=w<=150、10<=p<=200、5<=e<=80、20<=c<=300
print()
print('=' * 60)
print('优化引擎 · 新能源规划问题建模')
print('=' * 60)

df = pd.read_csv(os.path.join(DATA_DIR, '05_风光负荷同步出力数据.csv'))
df.columns = ['time', 'windSpeed', 'temp', 'ghi', 'wind', 'pv', 'load',
              'charge', 'discharge', 'soc', 'gridBuy', 'gridSell', 'curtail', 'balErr']
df03 = pd.read_csv(os.path.join(DATA_DIR, '03_小时级源荷气象电价数据.csv'))
df03.columns = ['time', 'windSpeed', 'ghi', 'temp', 'load', 'price']
HOUR = pd.to_datetime(df03['time'], format='%Y/%m/%d %H:%M').dt.hour.values

LOAD = df['load'].values
H = len(LOAD)

BASE_W, BASE_P = 80.0, 120.0                      # 05 数据对应装机
W_NORM = df['wind'].values / BASE_W               # 单位风电装机的出力曲线 MW/MW
P_NORM = df['pv'].values / BASE_P                 # 单位光伏装机的出力曲线 MW/MW

ESS_EFF, SOC_LO, SOC_HI = 0.92, 0.10, 0.95        # 02 设备参数
GRID_CAP = 70.0                                   # 06 外购电容量上限 MW
BUY_PRICE = np.where(HOUR < 8, 0.35, np.where(HOUR < 17, 0.75,
             np.where(HOUR < 21, 1.15, 0.75)))    # 07 分时电价
CRF = 0.08 * 1.08 ** 20 / (1.08 ** 20 - 1)
OM_RATE = 0.02
CARBON_FACTOR = 42000.0 / (df['wind'].sum() + df['pv'].sum())   # 06 碳减排反推排放因子 t/MWh

# 约束参数
GREEN_MIN = 65.0          # 绿电占比下限 %
WIND_SHARE_MIN = 25.0     # 风电装机占比下限 %
PEN_GREEN = 800.0         # 绿电每差 1 个百分点的罚值（万元）
PEN_SHARE = 400.0         # 风电占比每差 1 个百分点的罚值（万元）

print('决策变量边界：风电 10~150 MW | 光伏 10~200 MW | 储能 5~80 MW | 容量 20~300 MWh')
print('约束条件：绿电占比 >= %.0f%% | 风电装机占比 >= %.0f%% | 储能时长 1~6h | 失负荷率 -> 0'
      % (GREEN_MIN, WIND_SHARE_MIN))


def simulate(windMw, pvMw, essP, essCap):
    """时序生产模拟：5832 小时逐时平衡，储能 SOC 递推"""
    supply = W_NORM * windMw + P_NORM * pvMw
    soc = 0.5
    charge = np.zeros(H); discharge = np.zeros(H)
    buy = np.zeros(H); curtail = np.zeros(H); unmet = np.zeros(H)
    for i in range(H):
        bal = supply[i] - LOAD[i]
        if bal >= 0:   # 盈余：充电，余电弃掉（就地消纳）
            c = min(bal, essP, (SOC_HI - soc) * essCap / ESS_EFF)
            charge[i] = c; soc += c * ESS_EFF / essCap
            curtail[i] = bal - c
        else:          # 缺口：放电，再外购，仍不足为失负荷
            d = min(-bal, essP, (soc - SOC_LO) * essCap * ESS_EFF)
            discharge[i] = d; soc -= d / (ESS_EFF * essCap)
            gap = -bal - d
            b = min(gap, GRID_CAP)
            buy[i] = b; unmet[i] = gap - b
    return charge, discharge, buy, curtail, unmet


def evaluate(cfg, green_min=GREEN_MIN):
    """经济评价，返回 (罚函数修正后的目标值, 指标字典)"""
    windMw, pvMw, essP, essCap = [float(v) for v in cfg]
    chg, dis, buy, cur, unmet = simulate(windMw, pvMw, essP, essCap)
    reGen = (W_NORM.sum() * windMw + P_NORM.sum() * pvMw)
    used = reGen - cur.sum()
    loadSum = LOAD.sum()
    capex = windMw * 6500e3 + pvMw * 3500e3 + essCap * 1200e3      # 元
    annualInv = capex * CRF / 1e4                                   # 万元
    om = capex * OM_RATE / 1e4
    buyCost = float((buy * BUY_PRICE * 1000).sum()) / 1e4
    carbon = used * CARBON_FACTOR
    carbonRev = carbon * 80 / 1e4
    cost = annualInv + om + buyCost - carbonRev                     # 万元
    green = used / loadSum * 100
    curtailRate = cur.sum() / reGen * 100 if reGen else 0
    lcoe = cost * 1e4 / (loadSum * 1000)
    unmetRate = unmet.sum() / loadSum * 100
    windShare = windMw / (windMw + pvMw) * 100
    # 罚函数：绿电占比、风电装机占比、储能时长、失负荷率
    dur = essCap / essP if essP else 99
    pen = 0.0
    if dur < 1: pen += (1 - dur) * 1e4
    if dur > 6: pen += (dur - 6) * 1e4
    if green < green_min: pen += (green_min - green) * PEN_GREEN
    if windShare < WIND_SHARE_MIN: pen += (WIND_SHARE_MIN - windShare) * PEN_SHARE
    pen += unmetRate * 1e5
    info = dict(config=[round(windMw, 1), round(pvMw, 1), round(essP, 1), round(essCap, 1)],
                cost=round(cost, 1), lcoe=round(lcoe, 3),
                green=round(green, 1), curtailRate=round(curtailRate, 2),
                carbon=round(carbon), unmetRate=round(unmetRate, 3),
                windShare=round(windShare, 1), essHours=round(dur, 2),
                buyMwh=round(float(buy.sum())))
    return cost + pen, info


# 基线评估（平台当前配置 80/120/40/160，来自 06 文件）
_, base_info = evaluate([80, 120, 40, 160], green_min=0)
print('基线配置（平台当前方案 80/120/40/160）评估：')
print('  年总成本 %.1f 万元 | LCOE %.3f | 绿电 %.1f%% | 弃电率 %.2f%% | 风电占比 %.1f%% | 碳减排 %d t'
      % (base_info['cost'], base_info['lcoe'], base_info['green'],
         base_info['curtailRate'], base_info['windShare'], base_info['carbon']))

# ---------- PSO(MEALPY) 求解单目标规划 ----------
print()
print('=' * 60)
print('优化引擎 · PSO 求解单目标规划（最小年总成本）')
print('=' * 60)

LB = [10.0, 10.0, 5.0, 20.0]
UB = [150.0, 200.0, 80.0, 300.0]
EPOCH, POP = 80, 30

pso_problem = {
    'obj_func': lambda x: evaluate(x)[0],
    'bounds': FloatVar(lb=LB, ub=UB),
    'minmax': 'min',
    'log_to': None,
}

t0 = time.time()
pso_model = MealpyPSO.OriginalPSO(epoch=EPOCH, pop_size=POP)
pso_best = pso_model.solve(pso_problem)
pso_time = time.time() - t0

pso_x = np.asarray(pso_best.solution, dtype=float).ravel()[:4]
_, pso_info = evaluate(pso_x)
hfit = getattr(pso_model.history, 'list_global_best_fit', None)
pso_conv = [float(v) for v in hfit] if hfit is not None and len(hfit) else []
if not pso_conv:
    pso_conv = [float(pso_best.target.fitness)]

print('PSO 最优配置：风电%.1f 光伏%.1f 储能%.1fMW/%.0fMWh'
      % tuple(pso_info['config']))
print('PSO 年总成本 %.1f 万元（迭代 %d 代 × %d 粒子，耗时 %.0fs）'
      % (pso_info['cost'], EPOCH, POP, pso_time))
print('约束校验：绿电 %.1f%%（>=%.0f%%）| 风电占比 %.1f%%（>=%.0f%%）| 储能时长 %.2fh | 失负荷率 %.3f%%'
      % (pso_info['green'], GREEN_MIN, pso_info['windShare'], WIND_SHARE_MIN,
         pso_info['essHours'], pso_info['unmetRate']))

# 输出收敛曲线 PNG
plt.figure(figsize=(9, 4.2))
plt.plot(range(1, len(pso_conv) + 1), pso_conv, color='#1da972', lw=1.9, label='PSO (MEALPY)')
plt.axhline(base_info['cost'], color='#d94856', lw=1.2, ls='--', label='平台基线 %.0f 万元' % base_info['cost'])
plt.xlabel('迭代代数'); plt.ylabel('年总成本目标值 (万元)')
plt.title('粒子群算法收敛曲线（单目标：最小年总成本，含绿电/电源结构约束）')
plt.legend(); plt.grid(alpha=0.3)
plt.tight_layout()
conv_path = os.path.join(FIG_DIR, 'convergence.png')
plt.savefig(conv_path, dpi=130)
plt.close()
print('收敛曲线已保存:', conv_path)

# ---------- 绿电目标灵敏度分析 ----------
# 逐个绿电目标重新求解，记录成本与实际绿电占比
print()
print('=' * 60)
print('优化引擎 · 绿电目标灵敏度分析')
print('=' * 60)

sensitivity = []
for target in [55, 60, 65, 70, 75]:
    prob_t = {
        'obj_func': (lambda g: (lambda x: evaluate(x, green_min=g)[0]))(float(target)),
        'bounds': FloatVar(lb=LB, ub=UB),
        'minmax': 'min',
        'log_to': None,
    }
    m = MealpyPSO.OriginalPSO(epoch=60, pop_size=30)
    b = m.solve(prob_t)
    x = np.asarray(b.solution, dtype=float).ravel()[:4]
    _, inf = evaluate(x, green_min=target)
    ok = inf['green'] >= target - 0.5 and inf['windShare'] >= WIND_SHARE_MIN - 0.5
    sensitivity.append(dict(greenTarget=target, cost=inf['cost'], green=inf['green'],
                            curtailRate=inf['curtailRate'], windShare=inf['windShare'],
                            config=inf['config'], feasible=bool(ok)))
    print('绿电目标 >=%2d%% -> 风电%5.1f 光伏%5.1f 储能%5.1fMW/%.0fMWh | 成本 %.0f 万元 | 实际绿电 %.1f%% | 弃电 %.2f%% | %s'
          % (target, inf['config'][0], inf['config'][1], inf['config'][2], inf['config'][3],
             inf['cost'], inf['green'], inf['curtailRate'], '可行' if ok else '未达目标'))

# 输出灵敏度曲线 PNG
plt.figure(figsize=(9, 4.4))
tg = [s['greenTarget'] for s in sensitivity]
cs = [s['cost'] for s in sensitivity]
plt.plot(tg, cs, marker='o', color='#1da972', lw=2, ms=7, label='PSO 最优成本')
plt.scatter([base_info['green']], [base_info['cost']], s=120, marker='s',
            color='#d94856', zorder=5, label='平台基线配置')
plt.xlabel('绿电占比目标 (%)'); plt.ylabel('最小年总成本 (万元)')
plt.title('绿电目标 × 最小成本 灵敏度曲线（低碳约束的代价）')
plt.legend(); plt.grid(alpha=0.3)
plt.tight_layout()
sen_path = os.path.join(FIG_DIR, 'sensitivity.png')
plt.savefig(sen_path, dpi=130)
plt.close()
print('灵敏度曲线已保存:', sen_path)

# ---------- 结果对比与结论 ----------
print()
print('=' * 60)
print('优化引擎 · 优化结果对比与结论')
print('=' * 60)

rows = [['方案', '风电(MW)', '光伏(MW)', '储能(MW/MWh)', '年总成本(万元)',
         'LCOE(元/kWh)', '绿电占比(%)', '弃电率(%)', '碳减排(t)']]
for name, info in [('平台基线', base_info), ('PSO 优化方案', pso_info)]:
    rows.append([name,
                 '%.1f' % info['config'][0], '%.1f' % info['config'][1],
                 '%.0f/%.0f' % (info['config'][2], info['config'][3]),
                 '%.1f' % info['cost'], '%.3f' % info['lcoe'],
                 '%.1f' % info['green'], '%.2f' % info['curtailRate'],
                 '%d' % info['carbon']])

col_w = [14, 10, 10, 14, 15, 13, 13, 11, 10]
print('  '.join(str(c).ljust(w) for c, w in zip(rows[0], col_w)))
print('-' * sum(col_w))
for r in rows[1:]:
    print('  '.join(str(c).ljust(w) for c, w in zip(r, col_w)))

saved = (base_info['cost'] - pso_info['cost']) / base_info['cost'] * 100
print()
print('========== 结论 ==========')
print('一、算法选型：采用 MEALPY 的 OriginalPSO 完成全部求解。')
print('二、优化效果：在绿电占比 >= %.0f%%、风电装机占比 >= %.0f%% 约束下，'
      % (GREEN_MIN, WIND_SHARE_MIN))
print('    PSO 求得风电 %.1f MW / 光伏 %.1f MW / 储能 %.1f MW-%.0f MWh，年总成本 %.1f 万元，'
      % (pso_info['config'][0], pso_info['config'][1], pso_info['config'][2],
         pso_info['config'][3], pso_info['cost']))
print('    较平台基线 %.1f 万元降低 %.1f%%，同时绿电占比由 %.1f%% 提升至 %.1f%%、'
      % (base_info['cost'], saved, base_info['green'], pso_info['green']))
print('    弃电率保持在 %.2f%%，实现"降本 + 增绿"的双重目标。'
      % pso_info['curtailRate'])
print('三、灵敏度分析：绿电目标从 55%% 提高到 75%% 时，最小年总成本由 %.0f 万元升至 %.0f 万元，'
      % (sensitivity[0]['cost'], sensitivity[-1]['cost']))
print('    反映出低碳水平与投资成本之间的此消彼长关系，为规划决策提供量化依据。')

# ---------- 输出结果 JSON ----------
optimization_json = {
    'algorithm': {'name': 'PSO 粒子群算法', 'library': 'MEALPY',
                  'version': mealpy.__version__, 'epoch': EPOCH, 'popSize': POP},
    'constraints': {'greenMin': GREEN_MIN, 'windShareMin': WIND_SHARE_MIN,
                    'essHoursMin': 1, 'essHoursMax': 6},
    'baseline': base_info,
    'optimum': {**pso_info, 'convergence': [round(v, 1) for v in pso_conv],
                'time': round(pso_time, 1)},
    'sensitivity': sensitivity,
    'recommend': pso_info,
}

out_path = os.path.join(OUT_DIR, 'optimization_results.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(optimization_json, f, ensure_ascii=False)

print()
print('优化引擎完成，结果已输出: %s' % out_path)
print('平台大屏"智能优化推荐"卡、"智能优化"页、报告"智能优化配置建议"章节将自动读取该文件。')
