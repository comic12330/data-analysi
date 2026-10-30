<template>
  <div class="dash" v-if="ready">
    <TopNav :project="project" />

    <!-- 标题 + 核心KPI -->
    <header class="dash-header">
      <div class="dh-left">
        <div class="dh-title">友好型源网荷储一体化规划配置仿真平台</div>
        <div class="dh-sub">ZERO-CARBON PARK · SOURCE-GRID-LOAD-STORAGE INTEGRATED SIMULATION</div>
      </div>
      <div class="dh-kpis">
        <div class="dh-kpi">
          <span class="v num c-cyan">{{ fmt(opt.greenPowerRatio, 1) }}%</span>
          <span class="l">绿电占比 Green Ratio</span>
        </div>
        <div class="dh-kpi">
          <span class="v num c-green">{{ fmt(opt.reConsumptionRate, 1) }}%</span>
          <span class="l">新能源利用率 RE Utilization</span>
        </div>
        <div class="dh-kpi">
          <span class="v num c-yellow">{{ fmt(kpi.lcoe, 3) }}</span>
          <span class="l">度电成本 LCOE (元/kWh)</span>
        </div>
      </div>
    </header>

    <!-- 主体：左KPI竖栏 / 中央平衡全景 / 右图表流 -->
    <main class="dash-grid" :class="{ 'q15-mode': scale === 'q15' }">
      <!-- 左侧：友好性评分 + 指标条 + 装机卡片 -->
      <aside class="side-col">
        <div class="panel score-card">
          <div class="corner"></div>
          <div class="panel-head">
            <div class="panel-title">友好性综合评分 <span class="en">Friendliness Score</span></div>
          </div>
          <div class="score-num num">{{ fmt(opt.friendlinessScore, 1) }}<span class="score-unit">分</span></div>
          <div class="metric-list">
            <div class="metric" v-for="m in metrics" :key="m.label">
              <span class="m-label">{{ m.label }}</span>
              <span class="m-track">
                <span class="m-bar" :style="{ width: Math.min(100, m.pct) + '%', background: m.color }"></span>
              </span>
              <span class="m-val num">{{ fmt(m.value, 1) }}%</span>
            </div>
          </div>
        </div>

        <div class="panel kpi-stack">
          <div class="corner"></div>
          <div class="panel-head">
            <div class="panel-title">推荐配置方案 <span class="en">Configuration</span></div>
          </div>
          <div class="kpi-row" v-for="c in cards" :key="c.label">
            <span class="kr-label">{{ c.label }}</span>
            <span class="kr-value num" :style="{ color: C.emph }">{{ c.value }}<i>{{ c.unit }}</i></span>
          </div>
          <div class="opt-link" v-if="optRec">
            <div class="ol-head">
              <span class="ol-badge">智能优化</span>
              <span>PSO 优化推荐配置</span>
              <router-link class="ol-more" to="/optimize">详情 →</router-link>
            </div>
            <div class="ol-body num">风 {{ optRec.wind }} / 光 {{ optRec.pv }} / 储 {{ optRec.ess }}/{{ optRec.cap }}</div>
            <div class="ol-body num">年成本 {{ optRec.cost }} 万元 <i v-if="optRec.saving" class="ol-save">较基线 ↓{{ optRec.saving }}%</i></div>
          </div>
        </div>
      </aside>

      <!-- 中央：电力平衡全景 -->
      <section class="panel center">
        <div class="corner"></div>
        <div class="panel-head">
          <div class="panel-title">{{ centerTitle }} <span class="en">Power Balance Overview</span></div>
          <div class="scale-bar">
            <span class="scale-btn" v-for="s in scales" :key="s.k"
                  :class="{ on: scale === s.k }" @click="scale = s.k">{{ s.label }}</span>
          </div>
          <div class="date-pick" v-if="scale === 'day'">
            <input class="input" type="date" v-model="selDate"
                   :min="timeRange.start.slice(0, 10)" :max="timeRange.end.slice(0, 10)" />
          </div>
          <div class="date-pick" v-else-if="scale === 'month'">
            <input class="input" type="month" v-model="selMonth" min="2026-01" max="2026-08" />
          </div>
        </div>
        <div class="panel-body">
          <BaseChart :option="balanceOption" />
        </div>
      </section>

      <!-- 右侧：出力与储能、雷达（15 分钟视图下隐藏，中央图占满） -->
      <aside class="right-col" v-if="scale !== 'q15'">
        <div class="panel">
          <div class="corner"></div>
          <div class="panel-head">
            <div class="panel-title">风电出力曲线 <span class="en">Wind Power</span></div>
            <span class="unit">MW · {{ selDate }}</span>
          </div>
          <div class="panel-body">
            <BaseChart :option="windOption" />
          </div>
        </div>
        <div class="panel">
          <div class="corner"></div>
          <div class="panel-head">
            <div class="panel-title">光伏出力曲线 <span class="en">Solar Power</span></div>
            <span class="unit">MW · {{ selDate }}</span>
          </div>
          <div class="panel-body">
            <BaseChart :option="pvOption" />
          </div>
        </div>
        <div class="panel">
          <div class="corner"></div>
          <div class="panel-head">
            <div class="panel-title">储能充放电过程 <span class="en">Battery</span></div>
            <span class="unit">MW | SOC% · {{ selDate }}</span>
          </div>
          <div class="panel-body">
            <BaseChart :option="batteryOption" />
          </div>
        </div>
        <div class="panel">
          <div class="corner"></div>
          <div class="panel-head">
            <div class="panel-title">友好性评价雷达 <span class="en">Radar</span></div>
          </div>
          <div class="panel-body">
            <BaseChart :option="radarOption" />
          </div>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import BaseChart from '../components/BaseChart.vue'
import TopNav from '../components/TopNav.vue'
import { chartTheme, fmt, loadJSON } from '../utils/data'

// 绿色零碳主题色板（图表统一取色）
const C = {
  wind: '#3ee68f',        // 风电实采
  windAvail: '#9fc6b4',   // 风电理论可用
  pv: '#ffb545',          // 光伏
  balWind: '#2ec98a',     // 平衡图·风电
  ess: '#b78bff',         // 储能放电
  gridBuy: '#ff5d6c',     // 外购电
  gridSell: '#4da3ff',    // 上网售电
  curtail: '#7ba28f',     // 弃风弃光
  load: '#f2fff8',        // 负荷线
  chg: '#3ee68f',         // 充电
  dis: '#ff8b4a',         // 放电
  soc: '#d0a5ff',         // SOC
  radar: '#3ee68f',
  emph: '#3ee68f',
  cross: '#2a6b4a',
  tipBg: 'rgba(6, 28, 18, .95)',
  tipBorder: '#1c5c3e'
}

const ready = ref(false)
const project = ref({})
const opt = ref({})
const summary = ref({})
const simulation = ref([])
const device = ref([])
const selDate = ref('')
const optRes = ref(null)   // 智能优化引擎输出（optimize.py 生成，可选）

// ---------- 时间尺度 ----------
const scales = [
  { k: 'day', label: '典型日' },
  { k: 'month', label: '月度' },
  { k: 'period', label: '统计期' },
  { k: 'q15', label: '15 分钟' }
]
const scale = ref('day')
const selMonth = ref('')
const typical = ref([])    // 04 典型日 15 分钟曲线（96 点）

const centerTitle = computed(() => ({
  day: '源网荷储电力平衡全景',
  month: '月度生产模拟',
  period: '统计期生产模拟',
  q15: '典型日 15 分钟运行曲线'
}[scale.value]))

const kpi = computed(() => summary.value.kpi || {})
const timeRange = computed(() => summary.value.timeRange || { start: '', end: '' })

// 当日24h数据
const dayData = computed(() =>
  selDate.value ? simulation.value.filter(r => r.date === selDate.value) : []
)
const hours = computed(() => dayData.value.map(r => r.time.slice(11, 16)))

// 所选月份逐时数据
const monthData = computed(() =>
  selMonth.value ? simulation.value.filter(r => r.date.slice(0, 7) === selMonth.value) : []
)
const monthLabels = computed(() => monthData.value.map(r => r.time.slice(5, 13)))

// 统计期按月份聚合电量（MWh）
const periodAgg = computed(() => {
  const map = {}
  simulation.value.forEach(r => {
    const k = r.time.slice(0, 7)
    if (!map[k]) map[k] = { wind: 0, pv: 0, discharge: 0, gridBuy: 0, gridSell: 0, curtail: 0, load: 0 }
    const m = map[k]
    m.wind += r.wind; m.pv += r.pv; m.discharge += r.discharge
    m.gridBuy += r.gridBuy; m.gridSell += r.gridSell; m.curtail += r.curtail; m.load += r.load
  })
  return Object.keys(map).sort().map(k => ({ label: +k.slice(5) + '月', ...map[k] }))
})

// 峰值负荷（全周期）
const peakLoad = computed(() =>
  simulation.value.length ? Math.max(...simulation.value.map(r => r.load)) : 0
)

// ---------- 风电理论可用出力（依据02设备参数：切入/额定风速） ----------
const ratedParams = computed(() => {
  const map = {}
  device.value.forEach(d => { map[d.param] = d.value })
  return { cutIn: map['切入风速m/s'] || 3, rated: map['额定风速m/s'] || 11 }
})
function windTheoretical (v) {
  const { cutIn, rated } = ratedParams.value
  if (v < cutIn) return 0
  if (v >= rated) return opt.value.windMw
  return opt.value.windMw * (Math.pow(v, 3) - Math.pow(cutIn, 3)) / (Math.pow(rated, 3) - Math.pow(cutIn, 3))
}
// ---------- 光伏理论可用出力（辐照度×装机×系统效率） ----------
function pvTheoretical (ghi) {
  const eff = device.value.find(d => d.param === '系统效率')
  const eta = eff ? eff.value : 0.82
  return Math.min(opt.value.pvMw, ghi / 1000 * opt.value.pvMw * eta)
}

// ---------- 图表配置 ----------
const toolbox = {
  show: true,
  right: 6, top: 0,
  feature: { saveAsImage: { title: '保存图片', iconStyle: { borderColor: '#5f8a78' } } },
  iconStyle: { borderColor: '#5f8a78' }
}
const tooltipAxis = {
  trigger: 'axis',
  axisPointer: { type: 'cross', crossStyle: { color: C.cross }, lineStyle: { color: C.cross } },
  backgroundColor: C.tipBg,
  borderColor: C.tipBorder,
  textStyle: { color: '#e0f7ec', fontSize: 12 }
}

const windOption = computed(() => ({
  textStyle: chartTheme.textStyle,
  legend: { ...chartTheme.legend, top: 2, right: 40 },
  grid: { left: 40, right: 12, top: 30, bottom: 22 },
  tooltip: tooltipAxis,
  toolbox,
  xAxis: { type: 'category', data: hours.value, ...chartTheme.categoryAxis, boundaryGap: false },
  yAxis: { type: 'value', name: 'MW', nameTextStyle: { color: '#5f8a78' }, ...chartTheme.valueAxis },
  series: [
    {
      name: '可用出力', type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
      data: dayData.value.map(r => +windTheoretical(r.windSpeed).toFixed(2)),
      lineStyle: { color: C.windAvail, type: 'dashed', width: 1.5 },
      itemStyle: { color: C.windAvail }
    },
    {
      name: '实采实测', type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
      data: dayData.value.map(r => +r.wind.toFixed(2)),
      lineStyle: { color: C.wind, width: 2 },
      itemStyle: { color: C.wind }
    }
  ]
}))

const pvOption = computed(() => ({
  textStyle: chartTheme.textStyle,
  legend: { ...chartTheme.legend, top: 2, right: 40 },
  grid: { left: 40, right: 12, top: 30, bottom: 22 },
  tooltip: tooltipAxis,
  toolbox,
  xAxis: { type: 'category', data: hours.value, ...chartTheme.categoryAxis, boundaryGap: false },
  yAxis: { type: 'value', name: 'MW', nameTextStyle: { color: '#5f8a78' }, ...chartTheme.valueAxis },
  series: [
    {
      name: '可用出力', type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
      data: dayData.value.map(r => +pvTheoretical(r.ghi).toFixed(2)),
      lineStyle: { color: C.windAvail, type: 'dashed', width: 1.5 },
      itemStyle: { color: C.windAvail }
    },
    {
      name: '实采实测', type: 'line', smooth: true, symbol: 'circle', symbolSize: 4,
      data: dayData.value.map(r => +r.pv.toFixed(2)),
      lineStyle: { color: C.pv, width: 2 },
      itemStyle: { color: C.pv },
      ...gradientArea('rgba(255,181,69,.45)', 'rgba(255,181,69,0)')
    }
  ]
}))

// 平衡图序列：供给侧堆叠柱 + 售电/弃电（负值线）+ 负荷线
function supplySeries (rows, isAgg) {
  const num = v => isAgg ? Math.round(v) : +v.toFixed(2)
  const val = (k, sign = 1) => rows.map(r => num((r[k] || 0) * sign))
  const sym = (isAgg || rows.length > 48) ? 'none' : 'circle'
  return [
    { name: '风电出力', type: 'bar', stack: 'supply', barMaxWidth: isAgg ? 46 : 30, data: val('wind'), itemStyle: { color: C.balWind } },
    { name: '光伏出力', type: 'bar', stack: 'supply', data: val('pv'), itemStyle: { color: C.pv } },
    { name: '储能放电', type: 'bar', stack: 'supply', data: val('discharge'), itemStyle: { color: C.ess } },
    { name: '外购电量', type: 'bar', stack: 'supply', data: val('gridBuy'), itemStyle: { color: C.gridBuy } },
    {
      name: '上网售电', type: 'line', symbol: 'none',
      data: val('gridSell', -1),
      lineStyle: { color: C.gridSell, width: 1.6, type: 'dashed' },
      itemStyle: { color: C.gridSell }
    },
    {
      name: '弃风弃光', type: 'line', symbol: 'none',
      data: val('curtail', -1),
      lineStyle: { color: C.curtail, width: 1.6, type: 'dashed' },
      itemStyle: { color: C.curtail }
    },
    {
      name: '负荷', type: 'line', symbol: sym, symbolSize: 4,
      data: val('load'),
      lineStyle: { color: C.load, width: 2 },
      itemStyle: { color: C.load }
    }
  ]
}

const zoomCfg = [
  { type: 'inside' },
  { type: 'slider', height: 14, bottom: 8, borderColor: '#1c5c3e', backgroundColor: 'rgba(6,28,18,.6)', fillerColor: 'rgba(62,230,143,.15)', textStyle: { color: '#5f8a78' } }
]

const balanceOption = computed(() => {
  // 15 分钟：04 数据只含光伏可用出力与负荷
  if (scale.value === 'q15') {
    const rows = typical.value
    return {
      textStyle: chartTheme.textStyle,
      legend: { ...chartTheme.legend, top: 2, left: 'center' },
      grid: { left: 48, right: 20, top: 34, bottom: 24 },
      tooltip: tooltipAxis,
      toolbox,
      xAxis: { type: 'category', data: rows.map(r => r.time), ...chartTheme.categoryAxis },
      yAxis: { type: 'value', name: 'MW', nameTextStyle: { color: '#5f8a78' }, ...chartTheme.valueAxis },
      series: [
        {
          name: '光伏可用出力', type: 'bar', barMaxWidth: 8,
          data: rows.map(r => +r.pvAvailable.toFixed(2)),
          itemStyle: { color: C.pv },
          ...gradientArea('rgba(255,181,69,.45)', 'rgba(255,181,69,0)')
        },
        {
          name: '负荷', type: 'line', smooth: true, symbol: 'none',
          data: rows.map(r => +r.load.toFixed(2)),
          lineStyle: { color: C.load, width: 2 },
          itemStyle: { color: C.load }
        }
      ]
    }
  }

  const isAgg = scale.value === 'period'
  const rows = isAgg ? periodAgg.value : (scale.value === 'month' ? monthData.value : dayData.value)
  const xData = isAgg
    ? periodAgg.value.map(p => p.label)
    : (scale.value === 'month' ? monthLabels.value : hours.value)
  const zoom = scale.value === 'month'

  return {
    textStyle: chartTheme.textStyle,
    legend: { ...chartTheme.legend, top: 2, left: 'center', itemGap: 12, textStyle: { color: '#9ccbbb', fontSize: 10 } },
    grid: { left: 52, right: 24, top: 36, bottom: zoom ? 46 : 26 },
    tooltip: tooltipAxis,
    toolbox,
    dataZoom: zoom ? zoomCfg : [],
    xAxis: { type: 'category', data: xData, ...chartTheme.categoryAxis },
    yAxis: { type: 'value', name: isAgg ? 'MWh' : 'MW', nameTextStyle: { color: '#5f8a78' }, ...chartTheme.valueAxis },
    series: supplySeries(rows, isAgg)
  }
})

const batteryOption = computed(() => {
  const socP = device.value.find(d => d.param === 'SOC范围')
  let socLow = 10, socHigh = 95
  if (socP) {
    const m = String(socP.value).match(/(\d+)%-(\d+)%/)
    if (m) { socLow = +m[1]; socHigh = +m[2] }
  }
  return {
    textStyle: chartTheme.textStyle,
    legend: { ...chartTheme.legend, top: 2, right: 40 },
    grid: { left: 40, right: 46, top: 30, bottom: 22 },
    tooltip: tooltipAxis,
    toolbox,
    xAxis: { type: 'category', data: hours.value, ...chartTheme.categoryAxis },
    yAxis: [
      { type: 'value', name: 'MW', nameTextStyle: { color: '#5f8a78' }, ...chartTheme.valueAxis },
      { type: 'value', name: 'SOC', min: 0, max: 100, nameTextStyle: { color: '#5f8a78' }, ...chartTheme.valueAxis, splitLine: { show: false }, axisLabel: { ...chartTheme.valueAxis.axisLabel, formatter: '{value}%' } }
    ],
    series: [
      { name: '充电', type: 'bar', stack: 'ess', barMaxWidth: 12, data: dayData.value.map(r => +r.charge.toFixed(2)), itemStyle: { color: C.chg } },
      { name: '放电', type: 'bar', stack: 'ess', data: dayData.value.map(r => +(-r.discharge).toFixed(2)), itemStyle: { color: C.dis } },
      {
        name: 'SOC', type: 'line', yAxisIndex: 1, symbol: 'none', smooth: true,
        data: dayData.value.map(r => +(r.soc * 100).toFixed(1)),
        lineStyle: { color: C.soc, width: 2 },
        itemStyle: { color: C.soc },
        markLine: {
          silent: true, symbol: 'none',
          lineStyle: { color: '#5f8a78', type: 'dashed' },
          label: { color: '#5f8a78', fontSize: 10, formatter: 'SOC {c}%' },
          data: [{ yAxis: socLow }, { yAxis: socHigh }]
        }
      }
    ]
  }
})

// 雷达图五维（全部由数据计算）
const radarOption = computed(() => {
  const adequacy = peakLoad.value
    ? Math.min(100, (opt.value.windMw + opt.value.pvMw + opt.value.essPowerMw + opt.value.gridCapacityMw) / peakLoad.value * 100)
    : 0
  return {
    textStyle: chartTheme.textStyle,
    tooltip: { ...chartTheme.tooltip },
    radar: {
      center: ['50%', '52%'],
      radius: '68%',
      splitNumber: 4,
      axisName: { color: '#9ccbbb', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(20,67,45,.7)' } },
      splitArea: { areaStyle: { color: ['rgba(11,46,30,.3)', 'rgba(6,28,18,.5)'] } },
      axisLine: { lineStyle: { color: 'rgba(20,67,45,.9)' } },
      indicator: [
        { name: '电网友好', max: 100 },
        { name: '负荷友好', max: 100 },
        { name: '低碳友好', max: 100 },
        { name: '经济友好', max: 100 },
        { name: '调节友好', max: 100 }
      ]
    },
    series: [{
      type: 'radar',
      symbolSize: 4,
      data: [{
        value: [
          +adequacy.toFixed(1),
          +(100 - kpi.value.peakValleyRate).toFixed(1),
          opt.value.greenPowerRatio,
          kpi.value.selfBalanceRate,
          opt.value.reConsumptionRate
        ],
        name: '友好性评价',
        lineStyle: { color: C.radar, width: 2 },
        itemStyle: { color: C.radar },
        areaStyle: { color: 'rgba(62,230,143,.18)' }
      }]
    }]
  }
})

// 关键指标条（左侧评分卡内）
const metrics = computed(() => [
  { label: '弃电率', value: opt.value.curtailRate, pct: opt.value.curtailRate * 4, color: 'linear-gradient(90deg,#ff5d6c,#ff8b4a)' },
  { label: '绿电占比', value: opt.value.greenPowerRatio, pct: opt.value.greenPowerRatio, color: 'linear-gradient(90deg,#3ee68f,#2ec98a)' },
  { label: '自平衡率', value: kpi.value.selfBalanceRate, pct: kpi.value.selfBalanceRate, color: 'linear-gradient(90deg,#35d0a5,#1db977)' },
  { label: '外购电占比', value: kpi.value.gridBuyRatio, pct: kpi.value.gridBuyRatio, color: 'linear-gradient(90deg,#ffb545,#ff8b4a)' },
  { label: '峰谷差率', value: kpi.value.peakValleyRate, pct: kpi.value.peakValleyRate, color: 'linear-gradient(90deg,#b78bff,#8a7bff)' }
])

// 左侧配置卡片
const cards = computed(() => [
  { label: '风电装机', value: fmt(opt.value.windMw, 0), unit: ' MW' },
  { label: '光伏装机', value: fmt(opt.value.pvMw, 0), unit: ' MWp' },
  { label: '储能功率/容量', value: fmt(opt.value.essPowerMw, 0) + '/' + fmt(opt.value.essCapacityMwh, 0), unit: ' MW/MWh' },
  { label: '外网购电量', value: fmt(summary.value.energy?.gridBuyMwh, 0), unit: ' MWh' },
  { label: '年碳减排', value: fmt(opt.value.carbonReduction, 0), unit: ' tCO₂' }
])

// 智能优化引擎推荐（optimize.py 输出，未运行时为空、卡片隐藏）
const optRec = computed(() => {
  if (!optRes.value || !optRes.value.recommend) return null
  const r = optRes.value.recommend
  const base = optRes.value.baseline
  return {
    wind: fmt(r.config[0], 0), pv: fmt(r.config[1], 0),
    ess: fmt(r.config[2], 0), cap: fmt(r.config[3], 0),
    cost: fmt(r.cost, 0),
    saving: base && base.cost ? ((base.cost - r.cost) / base.cost * 100).toFixed(1) : null
  }
})

// 面积渐变辅助
function gradientArea (from, to) {
  return {
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: from }, { offset: 1, color: to }]
      }
    }
  }
}

onMounted(async () => {
  const [p, o, s, sim, d] = await Promise.all([
    loadJSON('project.json'),
    loadJSON('optimization.json'),
    loadJSON('summary.json'),
    loadJSON('simulation.json'),
    loadJSON('device.json')
  ])
  project.value = p
  opt.value = o
  summary.value = s
  simulation.value = sim
  device.value = d
  // 智能优化引擎结果可选加载（未运行 optimize.py 时不影响大屏）
  loadJSON('optimization_results.json').then(x => { optRes.value = x }).catch(() => {})
  // 典型日 15 分钟曲线（04 文件）
  loadJSON('typical_day.json').then(x => { typical.value = x }).catch(() => {})
  selDate.value = s.typicalDate
  selMonth.value = s.typicalDate.slice(0, 7)
  ready.value = true
})
</script>

<style scoped>
.dash {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 10px 12px 12px;
  gap: 10px;
  background:
    radial-gradient(1200px 500px at 50% -10%, rgba(30, 140, 90, .16), transparent),
    var(--bg-0);
}

/* ---- 顶部 ---- */
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-shrink: 0;
}
.dh-title {
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 2px;
  background: linear-gradient(90deg, #eafff3, #3ee68f);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  white-space: nowrap;
}
.dh-sub { font-size: 10px; color: var(--txt-3); letter-spacing: 2px; margin-top: 2px; }
.dh-kpis { display: flex; gap: 34px; }
.dh-kpi { text-align: center; }
.dh-kpi .v { display: block; font-size: 24px; font-weight: 700; }
.dh-kpi .l { font-size: 11px; color: var(--txt-3); white-space: nowrap; }

/* ---- 主体 ---- */
.dash-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 250px 1fr 360px;
  gap: 10px;
}
.dash-grid.q15-mode { grid-template-columns: 250px 1fr; }
.side-col { display: flex; flex-direction: column; gap: 10px; min-height: 0; }
.score-card { flex-shrink: 0; }
.kpi-stack { flex: 1; min-height: 0; }
.right-col { display: flex; flex-direction: column; gap: 10px; min-height: 0; }
.right-col .panel { flex: 1; min-height: 0; }
.panel.center { min-height: 0; }
.unit { font-size: 11px; color: var(--txt-3); white-space: nowrap; margin-left: auto; }
.date-pick { margin-left: 4px; }
.date-pick .input { padding: 3px 8px; font-size: 12px; color-scheme: dark; }

/* 时间尺度切换 */
.scale-bar { display: flex; gap: 3px; margin-left: auto; }
.scale-btn {
  font-size: 11px;
  line-height: 1;
  padding: 4px 8px;
  border: 1px solid rgba(62, 230, 143, .3);
  border-radius: 4px;
  color: var(--txt-2);
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
}
.scale-btn:hover { color: var(--cyan); border-color: rgba(62, 230, 143, .6); }
.scale-btn.on { background: rgba(62, 230, 143, .15); color: var(--cyan); border-color: var(--cyan); }

/* 评分卡 */
.score-num {
  font-size: 44px;
  font-weight: 700;
  color: var(--cyan);
  text-align: center;
  line-height: 1.1;
  text-shadow: 0 0 18px rgba(62, 230, 143, .45);
}
.score-unit { font-size: 15px; margin-left: 4px; color: var(--txt-2); }
.metric-list { display: flex; flex-direction: column; gap: 9px; margin-top: 12px; }
.metric { display: flex; align-items: center; gap: 8px; }
.m-label { width: 64px; font-size: 11.5px; color: var(--txt-2); text-align: right; white-space: nowrap; }
.m-track { flex: 1; height: 9px; background: rgba(20, 67, 45, .7); border-radius: 5px; overflow: hidden; }
.m-bar { display: block; height: 100%; border-radius: 5px; transition: width .6s; }
.m-val { width: 48px; font-size: 11.5px; color: var(--txt-1); }

/* 配置卡片竖排 */
.kpi-stack { overflow-y: auto; }
.kpi-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 4px;
  border-bottom: 1px dashed rgba(28, 92, 62, .55);
}
.kpi-row:last-child { border-bottom: none; }
.kr-label { font-size: 12px; color: var(--txt-2); white-space: nowrap; }
.kr-value { font-size: 16px; font-weight: 700; white-space: nowrap; }
.kr-value i { font-style: normal; font-size: 10px; font-weight: 400; color: var(--txt-3); margin-left: 2px; }

/* 智能优化推荐联动卡 */
.opt-link {
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px dashed rgba(62, 230, 143, .4);
  border-radius: 8px;
  background: rgba(62, 230, 143, .05);
}
.ol-head { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--txt-2); }
.ol-badge {
  font-size: 10px; color: #04150d; font-weight: 700;
  background: linear-gradient(135deg, var(--cyan), #1db977);
  padding: 1px 6px; border-radius: 4px;
}
.ol-more { margin-left: auto; color: var(--cyan); font-size: 11px; text-decoration: none; }
.ol-more:hover { text-decoration: underline; }
.ol-body { margin-top: 4px; font-size: 12px; color: var(--txt-1); }
.ol-save { font-style: normal; color: var(--cyan); font-size: 11px; margin-left: 4px; }
</style>
