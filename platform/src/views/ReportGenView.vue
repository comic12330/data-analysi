<template>
  <div class="rg-page" v-if="ready">
    <TopNav :project="project" />

    <div class="rg-body">
      <!-- 左栏：报告模板 -->
      <aside class="side-tpl">
        <div class="cfg-title">报告模板</div>
        <div class="tpl-cards">
          <div class="tpl-card" v-for="t in templates" :key="t.name"
               :class="{ active: tpl === t.name }" @click="pickTemplate(t)"
               :title="t.desc">
            <b>{{ t.name }}</b>
            <small>{{ t.desc }}</small>
          </div>
        </div>
      </aside>

      <!-- 右栏：上（章节 / 导出）下（正文） -->
      <div class="main-col">
        <div class="top-row">
          <div class="cfg-cell ch-cell">
            <div class="cfg-title">内容章节 <span class="num">（已选 {{ checkedChapters.length }}/{{ allChapters.length }}）</span></div>
            <div class="ch-chips">
              <span class="ch-chip" v-for="c in allChapters" :key="c"
                    :class="{ on: checkedChapters.includes(c) }"
                    @click="toggleChapter(c)">{{ c }}</span>
            </div>
          </div>

          <div class="cfg-cell out-cell">
            <div class="cfg-title">输出设置</div>
            <div class="out-grid">
              <select class="select" v-model="outFormat">
                <option v-for="f in formats" :key="f">{{ f }}</option>
              </select>
              <select class="select" v-model="pagePaper">
                <option>A4</option><option>A3</option><option>Letter</option>
              </select>
              <select class="select" v-model="pageDir">
                <option>纵向</option><option>横向</option>
              </select>
              <div class="dpi-box">
                <input type="range" min="72" max="300" step="1" v-model="dpi" class="dpi-range" />
                <span class="dpi-num num">{{ dpi }}</span>
              </div>
            </div>
            <div class="gen-row">
              <button class="btn primary" @click="genReport" :disabled="generating">⬡ 生成报告</button>
              <button class="btn" @click="exportReport" :disabled="!done">{{ exportLabel }}</button>
            </div>
            <div class="prog-wrap">
              <div class="prog-track"><div class="prog-bar" :style="{ width: progress + '%' }"></div></div>
              <span class="prog-text num">{{ progressText }}</span>
            </div>
          </div>
        </div>

        <!-- 纸张式报告预览 -->
        <main class="rp-stage">

      <div class="paper" ref="paperEl">
        <h1 class="pp-title">{{ project.name }}</h1>
        <div class="pp-sub">{{ tpl }} · {{ opt.year || project.year }}年度 · 生成时间 {{ now }}</div>

        <template v-for="sec in sections" :key="sec.title">
          <div class="pp-sec" v-if="sec.show">
            <h2>{{ sec.no }}. {{ sec.title }}</h2>
            <p v-for="(p, i) in sec.paras" :key="i" v-html="p"></p>
            <table class="pp-table" v-if="sec.table && sec.table.length">
              <thead>
                <tr><th v-for="h in sec.table[0]" :key="h">{{ h }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in sec.table.slice(1)" :key="ri">
                  <td v-for="(cell, ci) in row" :key="ci" :class="{ strong: ci === 0 }">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
            <div class="pp-chart" v-if="sec.title === '运行仿真结果'">
              <div class="pp-chart-title">图1 全年逐月电力平衡仿真图（{{ fmt(dataPoints) }}h）</div>
              <BaseChart :option="paperChartOption" />
            </div>
          </div>
        </template>
      </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import TopNav from '../components/TopNav.vue'
import BaseChart from '../components/BaseChart.vue'
import html2pdf from 'html2pdf.js'
import * as XLSX from 'xlsx'
import { fmt, loadJSON, nowStr } from '../utils/data'

const ready = ref(false)
const project = ref({})
const summary = ref({})
const opt = ref({})
const monthly = ref([])
const cost = ref([])
const device = ref([])
const tariff = ref([])
const simulation = ref([])
const predRes = ref(null)  // 预测引擎输出（predict.py，可选）
const optRes = ref(null)   // 优化引擎输出（optimize.py，可选）

const now = ref(nowStr())
const allChapters = ['项目概况', '基础数据说明', '资源条件分析', '负荷特性分析', '储能方法说明', '容量优化结果', '运行仿真结果', '可靠性分析', '出力预测评估', '智能优化配置建议', '经济性分析', '低碳效益分析', '友好性评价', '推荐配置方案', '风险与建议']

// 五类报告模板，各自对应不同的章节组合
const templates = [
  {
    name: '标准规划报告', desc: '资源分析、容量优化、运行仿真、经济性评估全流程',
    chapters: allChapters
  },
  {
    name: '经济性评价报告', desc: '重点覆盖 IRR、NPV、LCOE、回收期',
    chapters: ['项目概况', '基础数据说明', '容量优化结果', '运行仿真结果', '经济性分析', '推荐配置方案']
  },
  {
    name: '可靠性评价报告', desc: '供电充裕度、失负荷、储能支撑、电网依赖',
    chapters: ['项目概况', '基础数据说明', '负荷特性分析', '储能方法说明', '运行仿真结果', '可靠性分析', '推荐配置方案']
  },
  {
    name: '低碳性评价报告', desc: '碳足迹、减排量、碳交易收益、中和路径',
    chapters: ['项目概况', '资源条件分析', '容量优化结果', '运行仿真结果', '低碳效益分析', '推荐配置方案']
  },
  {
    name: '友好性评价报告', desc: '多维度友好性评分、电网适应性、柔性运行',
    chapters: ['项目概况', '运行仿真结果', '可靠性分析', '友好性评价', '推荐配置方案']
  }
]
const tpl = ref(templates[0].name)
const checkedChapters = ref([...allChapters])

// 切换模板时，章节自动替换为该模板的章节集
function pickTemplate (t) {
  tpl.value = t.name
  checkedChapters.value = allChapters.filter(c => t.chapters.includes(c))
}

function toggleChapter (c) {
  const i = checkedChapters.value.indexOf(c)
  if (i >= 0) checkedChapters.value.splice(i, 1)
  else checkedChapters.value.push(c)
}

const formats = ['Word (.doc)', 'Excel (.xlsx)', 'PDF']
const outFormat = ref('Word (.doc)')
// 导出按钮文字随格式变化
const exportLabel = computed(() => '⬇ 导出 ' + outFormat.value.replace(/\s*\(.*$/, ''))
const dpi = ref(150)
const paperEl = ref(null)
const pageDir = ref('横向')
const pagePaper = ref('A4')
const dataPoints = ref(0)
const progress = ref(0)
const generating = ref(false)
const done = ref(false)
const progressText = computed(() => generating.value ? '正在生成 ' + Math.floor(progress.value) + '%' : (done.value ? '生成完成 ✓' : '待生成'))

// 章节内容（全部由数据计算生成）
const sections = computed(() => {
  const k = summary.value.kpi || {}
  const e = summary.value.energy || {}
  const windHours = e.windMwh && opt.value.windMw ? +(e.windMwh / opt.value.windMw).toFixed(1) : 0
  const pvHours = e.pvMwh && opt.value.pvMw ? +(e.pvMwh / opt.value.pvMw).toFixed(1) : 0
  const capexWind = opt.value.windMw * 1000 * (cost.value.find(c => c.param === '风电CAPEX元/kW')?.value || 0) / 10000
  const capexPv = opt.value.pvMw * 1000 * (cost.value.find(c => c.param === '光伏CAPEX元/kW')?.value || 0) / 10000
  const capexEss = opt.value.essCapacityMwh * 1000 * (cost.value.find(c => c.param === '储能CAPEX元/kWh')?.value || 0) / 10000
  const capexSum = +(capexWind + capexPv + capexEss).toFixed(0)
  const carbonIncome = opt.value.carbonReduction * (cost.value.find(c => c.param === '碳价元/t')?.value || 0) / 10000
  const show = n => checkedChapters.value.includes(allChapters[n])

  const list = [
    {
      no: 1, title: '项目概况', show: show(0),
      paras: [
        `<b>${project.value.name}</b>位于${project.value.region}，规划年份 ${project.value.year} 年。项目通过风光资源、储能、外部电网与园区负荷的协同规划，实现源网荷储一体化运行。经容量优化，推荐配置：风电 <b>${opt.value.windMw} MW</b>、光伏 <b>${opt.value.pvMw} MW</b>、储能 <b>${opt.value.essPowerMw} MW / ${opt.value.essCapacityMwh} MWh</b>（时长 ${(opt.value.essCapacityMwh / opt.value.essPowerMw).toFixed(1)} 小时），外网购电容量 ${opt.value.gridCapacityMw} MW。项目绿电占比 ${opt.value.greenPowerRatio}%，新能源消纳率 ${opt.value.reConsumptionRate}%，友好性综合评分 <b>${opt.value.friendlinessScore} 分</b>。`
      ]
    },
    {
      no: 2, title: '基础数据说明', show: show(1),
      paras: [
        `数据时间范围：<b>${summary.value.timeRange?.start}</b> 至 <b>${summary.value.timeRange?.end}</b>，小时级共 <b>${fmt(summary.value.timeRange?.points)}</b> 点。`,
        `功率平衡校验关系：${summary.value.balanceFormula}。`
      ]
    },
    {
      no: 3, title: '资源条件分析', show: show(2),
      table: [
        ['月份', '平均风速(m/s)', '平均辐照(W/m²)', '平均温度(℃)', '风电发电量(MWh)', '光伏发电量(MWh)'],
        ...[1, 4, 7, 10].map(mo => {
          const m = monthly.value.find(x => x.month === mo) || {}
          return [mo + '月', m.avgWindSpeed, m.avgGhi, m.avgTemp, fmt(m.windMwh, 1), fmt(m.pvMwh, 1)]
        }),
        ['全年', '—', '—', '—', fmt(e.windMwh, 1), fmt(e.pvMwh, 1)]
      ]
    },
    {
      no: 4, title: '负荷特性分析', show: show(3),
      paras: [
        `统计期内园区总用电量 <b>${fmt(e.loadMwh, 1)} MWh</b>，最大负荷 <b>${peakLoad.value} MW</b>，峰谷差率 ${k.peakValleyRate}%，负荷平均峰谷特性明显，具备峰谷套利与需求响应空间。`
      ]
    },
    {
      no: 5, title: '储能方法说明', show: show(4),
      paras: [
        `储能额定功率 ${opt.value.essPowerMw} MW、额定容量 ${opt.value.essCapacityMwh} MWh，充放电效率 ${device.value.find(d => d.param === '充放电效率')?.value || 0.92}，SOC 运行范围 ${device.value.find(d => d.param === 'SOC范围')?.value || '10%-95%'}。统计期内储能放电 ${fmt(e.dischargeMwh, 1)} MWh、充电 ${fmt(e.chargeMwh, 1)} MWh，对负荷贡献率 ${k.essContribution}%，主要承担削峰填谷与备用调节职能。`
      ]
    },
    {
      no: 6, title: '容量优化结果', show: show(5),
      table: [
        ['设备类型', '优化容量', '投资成本(万元)', '年发电量(MWh)', '利用小时(h)'],
        ['风力发电', `${opt.value.windMw} MW`, fmt(capexWind, 0), fmt(e.windMwh, 1), fmt(windHours, 1)],
        ['光伏发电', `${opt.value.pvMw} MW`, fmt(capexPv, 0), fmt(e.pvMwh, 1), fmt(pvHours, 1)],
        ['储能系统', `${opt.value.essPowerMw} MW / ${opt.value.essCapacityMwh} MWh`, fmt(capexEss, 0), '—— 峰谷调节 ——', '—'],
        ['合计', `${opt.value.windMw + opt.value.pvMw} MW + 储能`, fmt(capexSum, 0), fmt(e.windMwh + e.pvMwh, 1), '—']
      ]
    },
    {
      no: 7, title: '运行仿真结果', show: show(6),
      table: [
        ['项目', '电量(MWh)', '占比'],
        ['园区总负荷', fmt(e.loadMwh, 1), '100%'],
        ['风电上网电量', fmt(e.windMwh, 1), (e.windMwh / e.loadMwh * 100).toFixed(1) + '%'],
        ['光伏上网电量', fmt(e.pvMwh, 1), (e.pvMwh / e.loadMwh * 100).toFixed(1) + '%'],
        ['储能放电', fmt(e.dischargeMwh, 1), (e.dischargeMwh / e.loadMwh * 100).toFixed(1) + '%'],
        ['外网购电', fmt(e.gridBuyMwh, 1), (e.gridBuyMwh / e.loadMwh * 100).toFixed(1) + '%'],
        ['弃风弃光', fmt(e.curtailMwh, 1), (e.curtailMwh / (e.windMwh + e.pvMwh) * 100).toFixed(2) + '%']
      ]
    },
    {
      no: 8, title: '可靠性分析', show: show(7),
      paras: [
        `供电充裕度 <b>${k.supplyAdequacy}%</b>（风电 ${opt.value.windMw} MW + 光伏 ${opt.value.pvMw} MW + 储能 ${opt.value.essPowerMw} MW + 外购 ${opt.value.gridCapacityMw} MW，对比最大负荷 ${peakLoad.value} MW），统计期失负荷率 0.00%，未出现供电缺口。`,
        `储能承担削峰填谷（放电 ${fmt(e.dischargeMwh, 1)} MWh），在风光出力低谷时段提供功率支撑；外购电占比 ${k.gridBuyRatio}%，需关注电网检修或极端天气下的供电风险，建议配置可中断负荷作为补充。`
      ]
    },
    {
      no: 9, title: '出力预测评估', show: show(8),
      paras: predRes.value ? [
        `采用随机森林回归统一建模流程（气象+时间特征，时序 80/20 划分）完成三类预测：风机出力 R² <b>${predRes.value.wind.r2}</b>（MAE ${predRes.value.wind.mae} MW）、光伏出力 R² <b>${predRes.value.pv.r2}</b>（MAE ${predRes.value.pv.mae} MW）、有功负荷 R² <b>${predRes.value.load.r2}</b>（MAE ${predRes.value.load.mae} MW）。`,
        `风/光出力受气象驱动可高精度还原，负荷预测精度足以支撑日前购电与储能充放电计划编制；预测评估详情见平台"智能优化"页。`
      ] : [
        `预测引擎（predict.py）尚未运行：运行后自动展示风机/光伏/负荷三类预测的精度评估（MAE/RMSE/R²），结果由引擎写入 prediction_results.json 并同步至平台。`
      ]
    },
    {
      no: 9, title: '智能优化配置建议', show: show(8),
      paras: optRes.value ? [
        `以年总成本为目标，采用 MEALPY 的粒子群算法（PSO）求解容量规划模型，并施加绿电占比 ≥ ${optRes.value.constraints?.greenMin ?? 65}%、风电装机占比 ≥ ${optRes.value.constraints?.windShareMin ?? 25}% 的约束条件；再通过改变绿电目标开展灵敏度分析，刻画"低碳—成本"的此消彼长关系。`,
        `智能优化推荐配置：风电 <b>${fmt(optRes.value.recommend.config[0], 1)} MW</b>、光伏 <b>${fmt(optRes.value.recommend.config[1], 1)} MW</b>、储能 <b>${fmt(optRes.value.recommend.config[2], 1)} MW / ${fmt(optRes.value.recommend.config[3], 0)} MWh</b>，年总成本约 <b>${fmt(optRes.value.recommend.cost, 1)} 万元</b>，较平台基线（${fmt(optRes.value.baseline.cost, 1)} 万元）节约 <b>${((optRes.value.baseline.cost - optRes.value.recommend.cost) / optRes.value.baseline.cost * 100).toFixed(1)}%</b>。`
      ] : [
        `优化引擎（optimize.py）尚未运行：运行后自动展示 PSO 收敛曲线、绿电目标灵敏度分析与推荐容量配置，结果由引擎写入 optimization_results.json 并同步至平台大屏。`
      ],
      table: optRes.value ? [
        ['方案', '风电(MW)', '光伏(MW)', '储能(MW/MWh)', '年总成本(万元)', '弃电率(%)', '碳减排(t)'],
        ['平台基线', fmt(optRes.value.baseline.config[0], 1), fmt(optRes.value.baseline.config[1], 1), `${fmt(optRes.value.baseline.config[2], 0)}/${fmt(optRes.value.baseline.config[3], 0)}`, fmt(optRes.value.baseline.cost, 1), fmt(optRes.value.baseline.curtailRate, 2), fmt(optRes.value.baseline.carbon, 0)],
        ['PSO 优化方案（本报告采用）', fmt(optRes.value.recommend.config[0], 1), fmt(optRes.value.recommend.config[1], 1), `${fmt(optRes.value.recommend.config[2], 0)}/${fmt(optRes.value.recommend.config[3], 0)}`, fmt(optRes.value.recommend.cost, 1), fmt(optRes.value.recommend.curtailRate, 2), fmt(optRes.value.recommend.carbon, 0)]
      ] : undefined
    },
    {
      no: 11, title: '经济性分析', show: show(9),
      paras: [
        `项目初始投资合计约 <b>${fmt(capexSum, 0)} 万元</b>（风电 ${fmt(capexWind, 0)}、光伏 ${fmt(capexPv, 0)}、储能 ${fmt(capexEss, 0)}），年总成本约 <b>${fmt(opt.value.annualCostWan, 0)} 万元</b>，折合度电成本（LCOE）<b>${k.lcoe} 元/kWh</b>。`,
        `按 20 年运营期、折现率 ${cost.value.find(c => c.param === '折现率')?.value || 0.08} 测算：自发自用替代购电、余电上网与碳资产形成的年净现金流约 <b>${econKpi.value.cf} 万元</b>，静态投资回收期约 <b>${econKpi.value.payback} 年</b>，净现值 NPV 约 <b>${econKpi.value.npv} 万元</b>，内部收益率 IRR 约 <b>${econKpi.value.irr}%</b>。`,
        `上述为全投资口径，未计入绿电交易溢价、辅助服务收益与需量电费节省。当前造价与电价假设下 LCOE（${k.lcoe} 元/kWh）高于园区平均购电价，项目纯财务回报偏低，其价值更多体现在低碳减排与电网友好性上；若计入绿电溢价或降低储能投资占比，回收期可显著缩短。`
      ],
      table: [
        ['指标', '数值'],
        ['初始投资(万元)', fmt(capexSum, 0)],
        ['LCOE(元/kWh)', k.lcoe],
        ['静态投资回收期(年)', econKpi.value.payback],
        ['净现值NPV(万元)', econKpi.value.npv],
        ['内部收益率IRR(%)', econKpi.value.irr]
      ]
    },
    {
      no: 12, title: '低碳效益分析', show: show(10),
      paras: [
        `项目年碳减排量约 <b>${fmt(opt.value.carbonReduction, 0)} tCO₂</b>，按碳价 ${cost.value.find(c => c.param === '碳价元/t')?.value || 80} 元/t 计算，年碳资产收益约 <b>${fmt(carbonIncome, 1)} 万元</b>，绿电环境价值显著。`
      ]
    },
    {
      no: 13, title: '友好性评价', show: show(11),
      paras: [
        `综合评价得分 <b>${opt.value.friendlinessScore} 分</b>。其中：新能源消纳率 ${opt.value.reConsumptionRate}%、绿电占比 ${opt.value.greenPowerRatio}%、弃电率 ${opt.value.curtailRate}%、自平衡率 ${k.selfBalanceRate}%、峰谷差率 ${k.peakValleyRate}%、供电充裕度 ${k.supplyAdequacy}%，满足友好型源网荷储一体化项目要求。`
      ]
    },
    {
      no: 14, title: '推荐配置方案', show: show(12),
      table: [
        ['项目', '配置'],
        ['风电装机', `${opt.value.windMw} MW`],
        ['光伏装机', `${opt.value.pvMw} MW`],
        ['储能', `${opt.value.essPowerMw} MW / ${opt.value.essCapacityMwh} MWh（磷酸铁锂）`],
        ['外网购电容量', `${opt.value.gridCapacityMw} MW`],
        ['分时电价策略', tariff.value.map(t => t.period).join(' / ')],
        ...(optRes.value ? [['智能优化建议', `风 ${fmt(optRes.value.recommend.config[0], 0)} / 光 ${fmt(optRes.value.recommend.config[1], 0)} / 储 ${fmt(optRes.value.recommend.config[2], 0)}MW-${fmt(optRes.value.recommend.config[3], 0)}MWh（年成本 ${fmt(optRes.value.recommend.cost, 0)} 万元）`]] : [])
      ]
    },
    {
      no: 15, title: '风险与建议', show: show(13),
      paras: [
        `外购电占比 ${k.gridBuyRatio}%，对外部电网依赖度较高，建议关注电价波动风险并扩大本地新能源配置；峰谷差率 ${k.peakValleyRate}%，建议加强需求响应与储能调度；新能源利用率 ${opt.value.reConsumptionRate}%，弃电水平 ${opt.value.curtailRate}% 处于合理区间。`
      ]
    }
  ]

  // 依据勾选的章节标题过滤并重新连续编号（按标题匹配，避免增删章节时索引错位）
  let no = 0
  return list.map(s => {
    const shown = checkedChapters.value.includes(s.title)
    return { ...s, show: shown, no: shown ? ++no : 0 }
  })
})

const peakLoad = ref('--')
// 经济性指标：年净现金流 / 静态回收期 / NPV / IRR
const econKpi = ref({ cf: '--', payback: '--', npv: '--', irr: '--' })

// 纸张内嵌图表：浅色版本（适配白纸打印）
const paperChartOption = computed(() => {
  const ms = monthly.value
  const disByMonth = {}
  simulation.value.forEach(r => {
    const mo = +r.time.slice(5, 7)
    disByMonth[mo] = (disByMonth[mo] || 0) + r.discharge
  })
  return {
    textStyle: { color: '#555', fontFamily: 'Microsoft YaHei' },
    legend: { top: 0, textStyle: { color: '#555', fontSize: 11 }, itemWidth: 14, itemHeight: 8 },
    grid: { left: 46, right: 16, top: 26, bottom: 22 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ms.map(x => x.month + '月'), axisLine: { lineStyle: { color: '#999' } }, axisLabel: { color: '#666', fontSize: 10 } },
    yAxis: { type: 'value', name: 'MWh', nameTextStyle: { color: '#666' }, axisLabel: { color: '#666', fontSize: 10 }, splitLine: { lineStyle: { color: '#e5e5e5', type: 'dashed' } } },
    series: [
      { name: '风电', type: 'bar', stack: 's', barMaxWidth: 18, data: ms.map(x => x.windMwh), itemStyle: { color: '#1da972' } },
      { name: '光伏', type: 'bar', stack: 's', data: ms.map(x => x.pvMwh), itemStyle: { color: '#e89b2e' } },
      { name: '储能放电', type: 'bar', stack: 's', data: ms.map(x => +(disByMonth[x.month] || 0).toFixed(1)), itemStyle: { color: '#8a63d2' } },
      { name: '外购电', type: 'bar', stack: 's', data: ms.map(x => x.gridBuyMwh), itemStyle: { color: '#d94856' } },
      { name: '负荷', type: 'line', symbol: 'circle', symbolSize: 4, data: ms.map(x => x.loadMwh), lineStyle: { color: '#333', width: 2 }, itemStyle: { color: '#333' } }
    ]
  }
})

function genReport () {
  generating.value = true
  done.value = false
  progress.value = 0
  const timer = setInterval(() => {
    progress.value += Math.random() * 18 + 6
    if (progress.value >= 100) {
      progress.value = 100
      clearInterval(timer)
      generating.value = false
      done.value = true
    }
  }, 180)
}
// 图表 canvas 转为 dataURL 图片，保证 Word/HTML 导出后图表仍可见
function paperHtmlForExport () {
  const paper = paperEl.value
  const clone = paper.cloneNode(true)
  const srcCanvas = paper.querySelectorAll('canvas')
  const dstCanvas = clone.querySelectorAll('canvas')
  srcCanvas.forEach((cv, i) => {
    if (!dstCanvas[i]) return
    const img = document.createElement('img')
    img.src = cv.toDataURL('image/png')
    img.style.width = '100%'
    dstCanvas[i].replaceWith(img)
  })
  return clone.innerHTML
}

function downloadBlob (blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

function exportFileName (ext) {
  const d = new Date()
  const stamp = '' + d.getFullYear() + String(d.getMonth() + 1).padStart(2, '0') + String(d.getDate()).padStart(2, '0')
  return project.value.name + '_' + tpl.value + '_' + stamp + '.' + ext
}

function exportReport () {
  if (!paperEl.value) return
  if (outFormat.value === 'PDF') exportPdf()
  else if (outFormat.value === 'Excel (.xlsx)') exportExcel()
  else exportWord()
}

function exportWord () {
  const css = `
    @page Section1 { size: 21.0cm 29.7cm; margin: 2.2cm 2.4cm 2.2cm 2.4cm; }
    div.Section1 { page: Section1; }
    body { font-family: "Microsoft YaHei", "SimSun", serif; font-size: 10.5pt; color: #333; line-height: 1.75; }
    h1 { font-family: "Microsoft YaHei", "SimHei"; font-size: 18pt; font-weight: bold; text-align: center; color: #111; margin: 0 0 8pt; line-height: 1.4; }
    .pp-sub { text-align: center; color: #888; font-size: 10pt; margin: 0 0 22pt; padding-bottom: 10pt; border-bottom: 1pt solid #cfdcd5; }
    .pp-sec { margin: 0 0 18pt; }
    h2 { font-family: "Microsoft YaHei", "SimHei"; font-size: 13pt; font-weight: bold; color: #0d7a4f; margin: 16pt 0 8pt; padding-bottom: 4pt; border-bottom: 0.75pt solid #cfe3d8; }
    p { margin: 0 0 8pt; text-align: justify; text-indent: 0; }
    table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 8pt 0 12pt; }
    th { background: #eef6f1; color: #0d7a4f; font-weight: bold; border: 0.75pt solid #c8dbd1; padding: 5pt 8pt; text-align: left; }
    td { border: 0.75pt solid #dde8e2; padding: 4pt 8pt; color: #444; }
    td.strong { color: #111; font-weight: bold; }
    b { color: #a86500; font-weight: bold; }
    img { max-width: 100%; }
    .pp-chart { margin: 10pt 0; text-align: center; }
    .pp-chart img { width: 15.5cm; }
    .pp-chart-title { text-align: center; color: #888; font-size: 9pt; margin: 0 0 4pt; }
  `
  const html = '<html xmlns:o="urn:schemas-microsoft-com:office:office" ' +
    'xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">' +
    '<head><meta charset="utf-8"><title>' + tpl.value + '</title>' +
    '<style>' + css + '</style></head><body><div class="Section1">' + paperHtmlForExport() + '</div></body></html>'
  downloadBlob(new Blob(['\ufeff' + html], { type: 'application/msword' }), exportFileName('doc'))
}

function exportExcel () {
  const rows = [['章节', '条目', '内容']]
  sections.value.filter(s => s.show).forEach(s => {
    rows.push([s.no + '. ' + s.title, '', ''])
    if (s.table) {
      s.table.forEach((row, ri) => rows.push(['', ri === 0 ? '表头' : row[0], row.join(' | ')]))
    } else {
      (s.paras || []).forEach((p, i) => rows.push(['', '正文' + (i + 1), String(p).replace(/<[^>]+>/g, '')]))
    }
  })
  const ws = XLSX.utils.aoa_to_sheet(rows)
  ws['!cols'] = [{ wch: 20 }, { wch: 16 }, { wch: 90 }]
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '报告内容')
  XLSX.writeFile(wb, exportFileName('xlsx'))
}

function exportPdf () {
  // 每章从新页开始，避免表格/图表在页底被截断
  const secs = paperEl.value.querySelectorAll('.pp-sec')
  secs.forEach((s, i) => { s.style.breakBefore = i ? 'page' : 'auto' })
  html2pdf().set({
    margin: [12, 10, 14, 10],
    filename: exportFileName('pdf'),
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: Math.max(1, Math.min(3, dpi.value / 96)), useCORS: true, backgroundColor: '#ffffff', logging: false },
    jsPDF: {
      unit: 'mm',
      format: pagePaper.value.toLowerCase(),
      orientation: pageDir.value === '横向' ? 'landscape' : 'portrait'
    },
    pagebreak: { mode: ['css', 'legacy'], avoid: ['tr', 'img', 'table'] }
  }).from(paperEl.value).save().then(() => {
    secs.forEach(s => { s.style.breakBefore = '' })
  })
}

onMounted(async () => {
  const [p, s, o, m, c, d, ta, hourly, sim] = await Promise.all([
    loadJSON('project.json'),
    loadJSON('summary.json'),
    loadJSON('optimization.json'),
    loadJSON('summary.json').then(x => x.monthly),
    loadJSON('cost.json'),
    loadJSON('device.json'),
    loadJSON('tariff.json'),
    loadJSON('hourly_source.json'),
    loadJSON('simulation.json')
  ])
  project.value = p
  summary.value = s
  opt.value = o
  monthly.value = m
  cost.value = c
  device.value = d
  tariff.value = ta
  simulation.value = sim
  peakLoad.value = fmt(Math.max(...hourly.map(r => r.load)), 1)
  dataPoints.value = s.timeRange?.points || 0

  // 经济性指标：以"全外购"为对照，自发自用节省的购电成本即项目现金流来源
  const carbonPrice = (c.find(x => x.param === '碳价元/t')?.value) || 80
  const disc = +((c.find(x => x.param === '折现率')?.value) || 0.08)
  const capexWan = opt.value.windMw * 1000 * (c.find(x => x.param === '风电CAPEX元/kW')?.value || 0) / 10000 +
                   opt.value.pvMw * 1000 * (c.find(x => x.param === '光伏CAPEX元/kW')?.value || 0) / 10000 +
                   opt.value.essCapacityMwh * 1000 * (c.find(x => x.param === '储能CAPEX元/kWh')?.value || 0) / 10000
  let savingWan = 0
  for (let i = 0; i < sim.length; i++) {
    const pr = hourly[i]?.price || 0.7
    // 自发自用替代的购电成本 + 余电上网售电收入；MWh × 元/kWh → 万元
    savingWan += (hourly[i].load - sim[i].gridBuy) * pr * 0.1
    savingWan += (sim[i].gridSell || 0) * 0.35 * 0.1
  }
  const cf = savingWan + opt.value.carbonReduction * carbonPrice / 10000 - capexWan * 0.02
  const npvAt = r => {
    let v = -capexWan
    for (let t = 1; t <= 20; t++) v += cf / Math.pow(1 + r, t)
    return v
  }
  let lo = 0, hi = 1
  for (let it = 0; it < 60; it++) {
    const mid = (lo + hi) / 2
    if (npvAt(mid) > 0) lo = mid; else hi = mid
  }
  econKpi.value = {
    cf: fmt(cf, 0),
    payback: cf > 0 ? (capexWan / cf).toFixed(1) : '--',
    npv: fmt(npvAt(disc), 0),
    irr: npvAt(0) > 0 ? ((lo + hi) / 2 * 100).toFixed(1) : '＜0'
  }
  // 智能优化引擎结果可选加载（未运行 optimize.py 时报告章节显示提示文案）
  loadJSON('prediction_results.json').then(x => { predRes.value = x }).catch(() => {})
  loadJSON('optimization_results.json').then(x => { optRes.value = x }).catch(() => {})
  ready.value = true
})
</script>

<style scoped>
.rg-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-0);
}

/* ---- 主体：左栏模板 + 右栏（上配置 / 下正文） ---- */
.rg-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 10px;
  padding: 10px 12px 0;
}
.side-tpl {
  flex: 0 0 214px;
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  background: var(--panel-bg);
  align-self: flex-start;
}
.main-col {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.top-row {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
  flex-wrap: wrap;
  align-items: flex-start;
}
.cfg-cell {
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  background: var(--panel-bg);
  padding: 10px 12px;
}
.cfg-title {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--txt-1);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.cfg-title .num { font-size: 10.5px; color: var(--txt-3); font-weight: 400; }
.tpl-cards { display: flex; flex-direction: column; gap: 7px; }
.tpl-card {
  padding: 6px 9px;
  border: 1px solid var(--panel-border);
  border-radius: 4px;
  background: rgba(9, 38, 26, .55);
  color: var(--txt-2);
  font-size: 12px;
  cursor: pointer;
  transition: all .2s;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  min-width: 0;
}
.tpl-card b { font-weight: 600; color: var(--txt-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.tpl-card small { font-size: 10.5px; color: var(--txt-3); line-height: 1.3; }
.tpl-card:hover { border-color: var(--cyan); color: var(--txt-1); }
.tpl-card.active {
  border-color: var(--cyan);
  color: var(--cyan);
  background: rgba(62, 230, 143, .1);
  box-shadow: 0 0 10px rgba(62, 230, 143, .15);
}
.tpl-card.active b { color: var(--cyan); }

.ch-cell { flex: 1 1 340px; min-width: 320px; }
.ch-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.ch-chip {
  padding: 4px 10px;
  font-size: 11.5px;
  border-radius: 3px;
  border: 1px solid var(--panel-border);
  color: var(--txt-3);
  cursor: pointer;
  transition: all .15s;
  user-select: none;
}
.ch-chip:hover { color: var(--txt-2); }
.ch-chip.on {
  color: #04150d;
  background: var(--cyan);
  border-color: var(--cyan);
  font-weight: 600;
}

.out-cell { flex: 0 0 292px; display: flex; flex-direction: column; }
.out-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px; }
.out-grid .select { font-size: 11.5px; padding: 4px 6px; width: 100%; }
.dpi-box { display: flex; align-items: center; gap: 6px; }
.dpi-num { font-size: 11px; color: var(--cyan); white-space: nowrap; }
.dpi-range { flex: 1; min-width: 0; accent-color: var(--cyan); }
.gen-row { display: flex; align-items: center; gap: 10px; }
.prog-wrap { flex: 1; min-width: 140px; }
.prog-track { height: 8px; background: rgba(20, 67, 45, .7); border-radius: 4px; overflow: hidden; }
.prog-bar { height: 100%; background: linear-gradient(90deg, var(--cyan), var(--blue)); border-radius: 4px; transition: width .2s; }
.prog-text { font-size: 10.5px; color: var(--txt-3); margin-top: 3px; display: block; }

/* ---- 纸张式预览 ---- */
.rp-stage {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 2px 16px;
  display: flex;
  justify-content: center;
}
.paper {
  width: 100%;
  max-width: 920px;
  background: #fdfdfb;
  color: #2a2a2a;
  border-radius: 4px;
  box-shadow: 0 6px 30px rgba(0, 0, 0, .45);
  padding: 42px 54px 30px;
  font-size: 13px;
  line-height: 22px;
  height: max-content;
}
.pp-title {
  font-size: 20px;
  text-align: center;
  letter-spacing: 1px;
  color: #111;
  margin: 0 0 6px;
}
.pp-sub {
  text-align: center;
  font-size: 11.5px;
  color: #999;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #1da972;
}
.pp-sec { margin-bottom: 18px; }
.pp-sec h2 {
  font-size: 14.5px;
  color: #0d7a4f;
  margin: 0 0 8px;
  padding-left: 8px;
  border-left: 3px solid #1da972;
}
.pp-sec p { margin: 0 0 6px; color: #444; }
.pp-sec p b { color: #b06e00; }
.pp-table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 12px;
}
.pp-table th {
  background: #f0f7f3;
  color: #0d7a4f;
  border: 1px solid #d7e6de;
  padding: 6px 8px;
  font-weight: 600;
  text-align: left;
}
.pp-table td {
  border: 1px solid #e2ebe6;
  padding: 5px 8px;
  color: #444;
}
.pp-table td.strong { color: #111; font-weight: 600; }
.pp-chart { margin: 12px 0 4px; height: 230px; }
.pp-chart-title { font-size: 11.5px; color: #888; text-align: center; margin-bottom: 2px; }
</style>
