# -*- coding: utf-8 -*-
"""
数据预处理脚本
将 data/ 目录下的原始数据文件转换为前端 Vue 平台所需的 JSON 文件
输出目录: platform/public/data/
运行: D:\\Anaconda3\\envs\\data_analysis\\python.exe prepare_data.py
"""
import json
import os
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, 'data')
OUT_DIR = os.path.join(BASE, 'platform', 'public', 'data')
os.makedirs(OUT_DIR, exist_ok=True)


def save_json(name, obj):
    path = os.path.join(OUT_DIR, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    size = os.path.getsize(path) / 1024
    print('  -> %-22s %.1f KB' % (name, size))


def read_xlsx(fname, sheet=None):
    xl = pd.ExcelFile(os.path.join(DATA_DIR, fname))
    sheet = sheet or xl.sheet_names[0]
    return xl.parse(sheet)


# ---------- 01 项目基础数据 ----------
print('01 项目基础数据')
df01 = read_xlsx('01_项目基础数据.xlsx')
p = dict(zip(df01['参数'], df01['值']))
project = {
    'name': str(p['项目名称']),
    'region': str(p['区域']),
    'year': int(p['规划年份']),
    'windMw': float(p['风电容量MW']),
    'pvMw': float(p['光伏容量MW']),
    'essPowerMw': float(p['储能功率MW']),
    'essCapacityMwh': float(p['储能容量MWh']),
}
save_json('project.json', project)

# ---------- 02 设备技术参数 ----------
print('02 设备技术参数')
df02 = read_xlsx('02_设备技术参数.xlsx')
device = df02.rename(columns={
    '设备': 'device', '参数': 'param', '数值': 'value'
})[['device', 'param', 'value']].to_dict('records')
save_json('device.json', device)

# ---------- 07 华东分时电价 ----------
print('07 华东分时电价数据')
df07 = read_xlsx('07_华东分时电价数据.xlsx')
tariff = df07.rename(columns={
    '时段': 'period', '购电价格元/kWh': 'price'
}).to_dict('records')
save_json('tariff.json', tariff)

# ---------- 08 经济成本参数 ----------
print('08 经济成本参数')
df08 = read_xlsx('08_经济成本参数.xlsx')
cost = df08.rename(columns={'参数': 'param', '值': 'value'}).to_dict('records')
save_json('cost.json', cost)

# ---------- 06 容量优化与评价结果 ----------
print('06 容量优化与评价结果')
df06 = read_xlsx('06_容量优化与评价结果.xlsx')
opt_raw = dict(zip(df06['指标'], df06['模拟结果']))
optimization = {
    'windMw': float(opt_raw['风电装机(MW)']),
    'pvMw': float(opt_raw['光伏装机(MW)']),
    'essPowerMw': float(opt_raw['储能功率(MW)']),
    'essCapacityMwh': float(opt_raw['储能容量(MWh)']),
    'gridCapacityMw': float(opt_raw['外网购电容量(MW)']),
    'reConsumptionRate': float(opt_raw['新能源消纳率(%)']),
    'greenPowerRatio': float(opt_raw['绿电占比(%)']),
    'curtailRate': float(opt_raw['弃风弃光率(%)']),
    'annualCostWan': float(opt_raw['年总成本(万元)']),
    'carbonReduction': float(opt_raw['碳减排(tCO2)']),
    'friendlinessScore': float(opt_raw['友好性综合评分']),
}
save_json('optimization.json', optimization)

# ---------- 9 容量配置及评价指标 ----------
print('9 容量配置及评价指标')
df9 = read_xlsx('9_容量配置及评价指标.xlsx')
indicators = df9.rename(columns={'指标': 'indicator', '值': 'value'}).to_dict('records')
save_json('indicators.json', indicators)

# ---------- 03 小时级源荷气象电价 ----------
print('03 小时级源荷气象电价数据')
df03 = pd.read_csv(os.path.join(DATA_DIR, '03_小时级源荷气象电价数据.csv'))
df03.columns = ['time', 'windSpeed', 'ghi', 'temp', 'load', 'price']
t = pd.to_datetime(df03['time'], format='%Y/%m/%d %H:%M')
df03['time'] = t.dt.strftime('%Y-%m-%d %H:%M')
df03['date'] = t.dt.strftime('%Y-%m-%d')
df03['month'] = t.dt.month
hourly = df03.drop(columns=['month']).to_dict('records')
save_json('hourly_source.json', hourly)

# ---------- 04 典型日15分钟运行曲线 ----------
print('04 典型日15分钟运行曲线')
df04 = pd.read_csv(os.path.join(DATA_DIR, '04_典型日15分钟运行曲线.csv'))
df04.columns = ['time', 'pvAvailable', 'load']
typical_day = df04.to_dict('records')
save_json('typical_day.json', typical_day)

# ---------- 05 风光负荷同步出力数据 ----------
print('05 风光负荷同步出力数据')
df05 = pd.read_csv(os.path.join(DATA_DIR, '05_风光负荷同步出力数据.csv'))
df05.columns = ['time', 'windSpeed', 'temp', 'ghi', 'wind', 'pv', 'load',
                'charge', 'discharge', 'soc', 'gridBuy', 'gridSell',
                'curtail', 'balanceError']
t5 = pd.to_datetime(df05['time'], format='%Y/%m/%d %H:%M')
df05['time'] = t5.dt.strftime('%Y-%m-%d %H:%M')
df05['date'] = t5.dt.strftime('%Y-%m-%d')
df05['month'] = t5.dt.month
sim = df05.drop(columns=['month', 'balanceError']).to_dict('records')
save_json('simulation.json', sim)

# ---------- 汇总统计（大屏 KPI 与报告使用） ----------
print('汇总统计 summary.json')
g = df05.groupby('month')
monthly = []
for m, sub in g:
    g3 = df03[df03['month'] == m]
    monthly.append({
        'month': int(m),
        'avgWindSpeed': round(float(g3['windSpeed'].mean()), 2),
        'avgGhi': round(float(g3['ghi'].mean()), 1),
        'avgTemp': round(float(g3['temp'].mean()), 1),
        'loadMwh': round(float(sub['load'].sum()), 1),
        'windMwh': round(float(sub['wind'].sum()), 1),
        'pvMwh': round(float(sub['pv'].sum()), 1),
        'gridBuyMwh': round(float(sub['gridBuy'].sum()), 1),
        'curtailMwh': round(float(sub['curtail'].sum()), 1),
        'windHours': round(float(sub['wind'].sum()) / optimization['windMw'], 1) if optimization['windMw'] else 0,
        'pvHours': round(float(sub['pv'].sum()) / optimization['pvMw'], 1) if optimization['pvMw'] else 0,
    })

loadSum = float(df05['load'].sum())
windSum = float(df05['wind'].sum())
pvSum = float(df05['pv'].sum())
dischargeSum = float(df05['discharge'].sum())
chargeSum = float(df05['charge'].sum())
gridBuySum = float(df05['gridBuy'].sum())
gridSellSum = float(df05['gridSell'].sum())
curtailSum = float(df05['curtail'].sum())

summary = {
    'timeRange': {'start': str(df05['time'].iloc[0]), 'end': str(df05['time'].iloc[-1]), 'points': int(len(df05))},
    'balanceFormula': '风电+光伏+储能放电+外网购电 = 负荷+储能充电+外网上网+弃风弃光',
    'energy': {
        'loadMwh': round(loadSum, 1),
        'windMwh': round(windSum, 1),
        'pvMwh': round(pvSum, 1),
        'dischargeMwh': round(dischargeSum, 1),
        'chargeMwh': round(chargeSum, 1),
        'gridBuyMwh': round(gridBuySum, 1),
        'gridSellMwh': round(gridSellSum, 1),
        'curtailMwh': round(curtailSum, 1),
    },
    'kpi': {
        # 绿电占比 = (风+光-弃电) / 总供电(负荷)
        'greenPowerRatio': round((windSum + pvSum - curtailSum) / loadSum * 100, 1),
        # 新能源利用率 = 风光实际利用 / 风光理论发电
        'reConsumptionRate': round((windSum + pvSum) / (windSum + pvSum + curtailSum) * 100, 1),
        # LCOE = 年总成本 / 年供电量
        'lcoe': round(optimization['annualCostWan'] * 10000 / (loadSum * 1000), 3),
        # 自平衡率 = 本地新能源与储能放电净供给 / 负荷
        'selfBalanceRate': round((windSum + pvSum - curtailSum - gridSellSum) / loadSum * 100, 1),
        # 外购电占比
        'gridBuyRatio': round(gridBuySum / loadSum * 100, 1),
        # 储能调节贡献 = 储能放电量 / 负荷
        'essContribution': round(dischargeSum / loadSum * 100, 1),
        # 峰谷差率 = (最大负荷-最小负荷)/最大负荷
        'peakValleyRate': round((float(df05['load'].max()) - float(df05['load'].min())) / float(df05['load'].max()) * 100, 1),
        # 供电充裕度 = (风+光+储能+外购容量) / 最大负荷
        'supplyAdequacy': round((optimization['windMw'] + optimization['pvMw'] + optimization['essPowerMw'] + optimization['gridCapacityMw']) / float(df05['load'].max()) * 100, 1),
    },
    'monthly': monthly,
    # 默认典型日：日风光总出力最接近日均值的日期
    'typicalDate': None,
}
dayStat = df05.groupby('date').agg(total=('wind', 'sum'), pv=('pv', 'sum'))
dayStat['both'] = dayStat['total'] + dayStat['pv']
target = dayStat['both'].mean()
summary['typicalDate'] = str((dayStat['both'] - target).abs().idxmin())
save_json('summary.json', summary)

print('\n全部完成，输出目录:', OUT_DIR)
