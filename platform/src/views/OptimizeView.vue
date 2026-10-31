<template>
  <div class="page optimize-page">
    <TopNav :project="project" />

    <!-- 页头 -->
    <div class="pg-head">
      <div>
        <h2>智能优化决策</h2>
        <p>出力与负荷预测 · 容量优化配置 · 规划方案对比</p>
      </div>
    </div>

    <div v-if="!ready" class="empty-hint">
      <div class="empty-icon">⚙</div>
      <p>计算结果尚未生成</p>
      <span>请先在数据管理页完成数据导入，系统将自动重算并生成本页结果</span>
    </div>

    <template v-else>
      <!-- 板块一：预测评估 -->
      <section class="panel sec-pred">
        <div class="sec-title"><i />出力与负荷预测 <em>随机森林模型 · 实际值与预测值对比</em></div>
        <div class="pred-body">
          <div class="metric-col">
            <div v-for="m in predMetrics" :key="m.key" class="metric-card"
                 :class="{ on: predTab === m.key }" @click="predTab = m.key">
              <div class="mc-head">
                <span class="dot" :style="{ background: m.color }" />{{ m.name }}
              </div>
              <div class="mc-r2">决定系数 <b>{{ m.r2 }}</b></div>
              <div class="mc-err">平均绝对误差 {{ m.mae }} MW ｜ 均方根误差 {{ m.rmse }} MW</div>
            </div>
          </div>
          <div class="pred-chart panel-chart">
            <BaseChart :option="predOption" />
          </div>
        </div>
      </section>

      <!-- 板块二：优化求解 -->
      <div class="opt-grid">
        <section class="panel">
          <div class="sec-title"><i />PSO 收敛曲线 <em>单目标 · 最小年总成本</em></div>
          <div class="panel-chart"><BaseChart :option="convOption" /></div>
        </section>
        <section class="panel">
          <div class="sec-title"><i />绿电目标 × 最小成本 <em>灵敏度分析</em></div>
          <div class="panel-chart"><BaseChart :option="senOption" /></div>
        </section>
      </div>

      <!-- 板块三：方案对比 -->
      <section class="panel">
        <div class="sec-title"><i />规划方案对比 <em>当前方案 / 优化推荐方案</em></div>
        <table class="cmp-table">
          <thead>
            <tr>
              <th>方案</th><th>风电<br>MW</th><th>光伏<br>MW</th><th>储能<br>MW / MWh</th>
              <th>年总成本<br>万元</th><th>度电成本<br>元/kWh</th><th>绿电占比<br>%</th>
              <th>弃电率<br>%</th><th>碳减排<br>t</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in cmpRows" :key="r.name" :class="{ rec: r.rec }">
              <td class="c-name">
                {{ r.name }}
                <span v-if="r.rec" class="rec-tag">推荐</span>
              </td>
              <td>{{ r.w }}</td><td>{{ r.p }}</td><td>{{ r.e }}</td>
              <td class="num">{{ r.cost }}</td><td class="num">{{ r.lcoe }}</td>
              <td class="num">{{ r.green }}</td><td class="num">{{ r.curtail }}</td>
              <td class="num">{{ r.carbon }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import TopNav from '../components/TopNav.vue'
import BaseChart from '../components/BaseChart.vue'
import { fmt, loadJSON } from '../utils/data'

const project = ref({})
const pred = ref(null)
const opt = ref(null)
const ready = computed(() => !!(pred.value && opt.value))
const predTab = ref('wind')

const C = { wind: '#3ee68f', pv: '#ffb545', load: '#4da3ff', ess: '#b78bff', red: '#ff5d6c', grey: '#7ba28f' }

onMounted(async () => {
  loadJSON('project.json').then(p => { project.value = p }).catch(() => {})
  try {
    const [p, o] = await Promise.all([
      loadJSON('prediction_results.json'),
      loadJSON('optimization_results.json')
    ])
    pred.value = p
    opt.value = o
  } catch (e) { /* 结果文件未生成，页面显示提示 */ }
})

/* ---------- 预测 ---------- */
const predMetrics = computed(() => {
  if (!pred.value) return []
  return [
    { key: 'wind', name: '风机出力', color: C.wind, ...pred.value.wind },
    { key: 'pv', name: '光伏出力', color: C.pv, ...pred.value.pv },
    { key: 'load', name: '有功负荷', color: C.load, ...pred.value.load }
  ].map(m => ({ ...m, mae: fmt(m.mae, 2), rmse: fmt(m.rmse, 2), r2: m.r2 }))
})

const predOption = computed(() => {
  if (!pred.value) return {}
  const d = pred.value[predTab.value]
  const lab = Math.max(1, Math.round(d.time.length / 7))
  const col = predTab.value === 'wind' ? C.wind : predTab.value === 'pv' ? C.pv : C.load
  const area = predTab.value === 'wind' ? 'rgba(62,230,143,.13)'
    : predTab.value === 'pv' ? 'rgba(255,181,69,.13)' : 'rgba(77,163,255,.13)'
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(6,28,18,.95)', borderColor: '#1c5c3e', textStyle: { color: '#e0f7ec', fontSize: 12 } },
    legend: { top: 4, textStyle: { color: '#9ccbbb', fontSize: 11 }, icon: 'roundRect', itemWidth: 14, itemHeight: 8 },
    grid: { left: 44, right: 14, top: 34, bottom: 40 },
    xAxis: { type: 'category', data: d.time, axisLine: { lineStyle: { color: '#2a6b4a' } }, axisTick: { show: false }, axisLabel: { color: '#5f8a78', fontSize: 10, interval: lab } },
    yAxis: { type: 'value', name: 'MW', nameTextStyle: { color: '#5f8a78' }, axisLabel: { color: '#5f8a78', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(20,67,45,.5)', type: 'dashed' } } },
    series: [
      {
        name: '实际值', type: 'line', data: d.actual, symbol: 'none', z: 3,
        lineStyle: { width: 2.6, color: '#ffffff' },
        itemStyle: { color: '#ffffff' }
      },
      {
        name: '预测值', type: 'line', data: d.pred, symbol: 'none', z: 2,
        lineStyle: { width: 2.2, color: col },
        itemStyle: { color: col },
        areaStyle: { color: area }
      }
    ]
  }
})

/* ---------- PSO 收敛曲线 ---------- */
const convOption = computed(() => {
  if (!opt.value) return {}
  const cv = opt.value.optimum.convergence
  return {
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(6,28,18,.95)', borderColor: '#1c5c3e', textStyle: { color: '#e0f7ec', fontSize: 12 } },
    legend: { top: 4, textStyle: { color: '#9ccbbb', fontSize: 11 }, icon: 'roundRect', itemWidth: 14, itemHeight: 8 },
    grid: { left: 56, right: 20, top: 34, bottom: 30 },
    xAxis: { type: 'value', name: '代数', nameTextStyle: { color: '#5f8a78' }, axisLabel: { color: '#5f8a78', fontSize: 10 }, splitLine: { show: false } },
    yAxis: { type: 'value', name: '年总成本 (万元)', nameTextStyle: { color: '#5f8a78' }, axisLabel: { color: '#5f8a78', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(20,67,45,.5)', type: 'dashed' } } },
    series: [{
      name: 'PSO 最优成本', type: 'line', data: cv.map((v, i) => [i + 1, v]),
      symbol: 'none', lineStyle: { width: 2 }, itemStyle: { color: C.wind },
      areaStyle: { color: 'rgba(62,230,143,.10)' },
      markLine: {
        silent: true, symbol: 'none',
        label: { formatter: '当前方案 {c}', color: C.red, fontSize: 10, position: 'insideEndTop' },
        lineStyle: { color: C.red, type: 'dashed', width: 1.2 },
        data: [{ yAxis: opt.value.baseline.cost }]
      }
    }]
  }
})

/* ---------- 绿电目标灵敏度 ---------- */
const senOption = computed(() => {
  if (!opt.value) return {}
  const s = opt.value.sensitivity || []
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(6,28,18,.95)', borderColor: '#1c5c3e', textStyle: { color: '#e0f7ec', fontSize: 12 },
      formatter: ps => {
        const a = ps.find(x => x.seriesName === 'PSO 最优成本')
        if (!a) return ''
        const it = s[a.dataIndex]
        return `绿电目标 ${it.greenTarget}%<br/>实际绿电 ${it.green}%<br/>最小成本 <b>${fmt(it.cost, 0)}</b> 万元<br/>弃电率 ${it.curtailRate}%`
      }
    },
    legend: { top: 4, textStyle: { color: '#9ccbbb', fontSize: 11 }, icon: 'roundRect', itemWidth: 14, itemHeight: 8 },
    grid: { left: 56, right: 20, top: 34, bottom: 34 },
    xAxis: { type: 'value', name: '绿电占比 (%)', min: 40, max: 80, nameTextStyle: { color: '#5f8a78' }, axisLabel: { color: '#5f8a78', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(20,67,45,.5)', type: 'dashed' } } },
    yAxis: { type: 'value', name: '最小成本 (万元)', nameTextStyle: { color: '#5f8a78' }, axisLabel: { color: '#5f8a78', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(20,67,45,.5)', type: 'dashed' } } },
    series: [
      {
        name: 'PSO 最优成本', type: 'line', smooth: true,
        data: s.map(x => [x.greenTarget, x.cost]),
        symbol: 'circle', symbolSize: 7, itemStyle: { color: C.wind },
        lineStyle: { width: 2 }, areaStyle: { color: 'rgba(62,230,143,.10)' }
      },
      {
        name: '当前方案', type: 'scatter', symbol: 'rect', symbolSize: 13,
        itemStyle: { color: C.red }, z: 5,
        data: [[opt.value.baseline.green, opt.value.baseline.cost]]
      }
    ]
  }
})

/* ---------- 对比表 ---------- */
const cmpRows = computed(() => {
  if (!opt.value) return []
  const row = (name, info, rec = false) => ({
    name, rec,
    w: fmt(info.config[0], 1), p: fmt(info.config[1], 1),
    e: `${fmt(info.config[2], 0)} / ${fmt(info.config[3], 0)}`,
    cost: fmt(info.cost, 1), lcoe: fmt(info.lcoe, 3),
    green: fmt(info.green, 1), curtail: fmt(info.curtailRate, 2), carbon: fmt(info.carbon, 0)
  })
  return [
    row('当前方案', opt.value.baseline),
    row('优化推荐方案', opt.value.optimum, true)
  ]
})
</script>

<style scoped>
.optimize-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.pg-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 14px 20px 10px;
}
.pg-head h2 { font-size: 17px; color: var(--txt-1); margin: 0 0 4px; }
.pg-head p { margin: 0; font-size: 12px; color: var(--txt-2); }

.panel {
  margin: 0 20px 14px;  border: 1px solid var(--panel-border);
  border-radius: 10px;
  background: linear-gradient(160deg, rgba(9, 34, 22, .82), rgba(6, 24, 16, .9));
  padding: 12px 14px;
  flex-shrink: 0;
}
.sec-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--txt-1);
  margin-bottom: 10px;
}
.sec-title i {
  width: 3px; height: 13px;
  background: var(--cyan);
  border-radius: 2px;
  box-shadow: 0 0 6px var(--cyan);
  align-self: center;
}
.sec-title em { font-style: normal; font-size: 11px; font-weight: 400; color: var(--txt-2); }
.panel-chart { height: 260px; }

/* 空状态 */
.empty-hint {
  margin: 60px auto;
  text-align: center;
  color: var(--txt-2);
}
.empty-icon { font-size: 40px; opacity: .5; margin-bottom: 10px; }
.empty-hint p { font-size: 15px; color: var(--txt-1); margin: 0 0 6px; }
.empty-hint span { font-size: 12px; }

/* 预测板块 */
.pred-body { display: grid; grid-template-columns: 250px 1fr; gap: 14px; }
.metric-col { display: flex; flex-direction: column; gap: 10px; }
.metric-card {
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
  background: rgba(10, 40, 26, .4);
  transition: border-color .2s, background .2s;
}
.metric-card:hover { border-color: rgba(62, 230, 143, .45); }
.metric-card.on {
  border-color: var(--cyan);
  background: rgba(62, 230, 143, .1);
  box-shadow: 0 0 12px rgba(62, 230, 143, .12) inset;
}
.mc-head { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--txt-2); }
.mc-head .dot { width: 8px; height: 8px; border-radius: 50%; }
.mc-r2 { margin: 4px 0 2px; font-size: 12px; color: var(--txt-2); }
.mc-r2 b { font-size: 21px; font-weight: 700; color: var(--txt-1); margin-left: 6px; font-family: Consolas, monospace; }
.mc-err { font-size: 11px; color: var(--txt-2); }

.opt-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin: 0 20px 14px;
}
.opt-grid .panel { margin: 0; }

/* 对比表 */
.cmp-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.cmp-table th {
  color: var(--txt-2);
  font-weight: 500;
  font-size: 11.5px;
  padding: 8px 6px;
  border-bottom: 1px solid var(--panel-border);
  text-align: center;
  line-height: 1.35;
}
.cmp-table td {
  padding: 9px 6px;
  text-align: center;
  color: var(--txt-1);
  border-bottom: 1px solid rgba(28, 92, 62, .35);
}
.cmp-table td.num { font-family: Consolas, monospace; color: var(--cyan); }
.cmp-table .c-name { text-align: left; color: var(--txt-1); font-weight: 600; white-space: nowrap; }
.cmp-table tr.rec td { background: rgba(62, 230, 143, .07); }
.rec-tag {
  font-size: 10px;
  color: #04150d;
  background: linear-gradient(135deg, var(--cyan), #1db977);
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: 6px;
  font-weight: 700;
}
</style>
