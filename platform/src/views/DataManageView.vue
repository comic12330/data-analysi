<template>
  <div class="dm-page" v-if="ready">
    <TopNav :project="project" />

    <!-- 横向数据类型选择条 -->
    <div class="type-bar">
      <div class="type-chip" v-for="t in types" :key="t.key"
           :class="{ active: selected === t.key }" @click="selectType(t.key)">
        <span class="tc-label">{{ t.label }}</span>
        <span class="tc-count num">{{ fmt(t.count) }}<i>条</i></span>
      </div>
    </div>

    <!-- 主体：左=导入工作台 / 右=常驻数据预览 -->
    <main class="dm-layout">
      <!-- 左：导入工作台 -->
      <section class="panel dm-work">
        <div class="corner"></div>
        <div class="col-title">导入工作台 <span class="en">IMPORT WORKBENCH</span></div>

        <div class="wk-scroll scroll-y">
          <!-- 上传 + 模板 + 分辨率 -->
          <div class="upload-row">
            <div class="upload-zone" :class="{ dragging }"
                 @dragover.prevent="dragging = true"
                 @dragleave.prevent="dragging = false"
                 @drop.prevent="onDrop"
                 @click="$refs.fileInput.click()">
              <div class="uz-icon">📂</div>
              <div class="uz-main">拖拽文件至此处上传</div>
              <div class="uz-sub">支持 Excel (.xlsx) / CSV (.csv)，≤ 10 万行</div>
              <input type="file" ref="fileInput" hidden accept=".csv,.xlsx,.xls" @change="onFileChange" />
            </div>
            <div class="upload-side">
              <div class="blk">
                <div class="blk-title">模板下载</div>
                <div class="tpl-btns">
                  <button class="btn sm" @click="downloadTpl('wind')">▼ 风资源模板</button>
                  <button class="btn sm" @click="downloadTpl('solar')">▼ 光资源模板</button>
                  <button class="btn sm" @click="downloadTpl('load')">▼ 负荷模板</button>
                  <button class="btn sm" @click="downloadTpl('price')">▼ 电价模板</button>
                </div>
              </div>
              <div class="blk">
                <div class="blk-title">时间分辨率</div>
                <select class="select" v-model="resolution">
                  <option value="1小时">1 小时</option>
                  <option value="15分钟">15 分钟</option>
                </select>
              </div>
            </div>
          </div>

          <!-- 字段映射 -->
          <template v-if="upload.file">
            <div class="blk-title map-title">字段配置 <span class="en">COLUMN MAPPING</span>
              <span class="upload-meta">当前文件：<b>{{ upload.file }}</b>
                <span class="num">（{{ fmt(upload.rows.length) }} 行 × {{ upload.columns.length }} 列）</span>
              </span>
            </div>
            <div class="tbl-wrap">
              <table class="tbl">
                <thead>
                  <tr>
                    <th>CSV列名（映射文件）</th><th style="width:26px"></th>
                    <th>系统字段</th><th>数据类型</th><th>单位</th><th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(m, i) in mapping" :key="i">
                    <td class="num c-cyan">{{ m.col }}</td>
                    <td class="c-cyan">→</td>
                    <td>
                      <select class="select sm" v-model="m.target">
                        <option value="">— 未映射 —</option>
                        <option v-for="f in sysFields" :key="f.key" :value="f.key">{{ f.name }}</option>
                      </select>
                    </td>
                    <td class="num">{{ m.dtype }}</td>
                    <td class="num">{{ m.unit }}</td>
                    <td>
                      <span class="tag ok" v-if="m.target">✓ 已匹配</span>
                      <span class="tag warn" v-else>◌ 待确认</span>
                    </td>
                  </tr>
                  <tr v-if="!mapping.length">
                    <td class="c-red">— 未识别到数据列 —</td><td></td><td></td><td></td><td></td><td></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <!-- 校验/预处理结果 -->
          <div v-if="checkResult" class="check-result" :class="checkResult.ok ? 'ok' : 'warn'">
            <div class="cr-title">{{ checkResult.ok ? '✓ 数据校验通过' : '⚠ 数据校验发现问题' }}</div>
            <div class="cr-line" v-for="l in checkResult.lines" :key="l">{{ l }}</div>
            <div class="cr-line" v-if="preprocessMsg">✦ 预处理：{{ preprocessMsg }}</div>
          </div>

          <!-- 操作栏 -->
          <div class="action-bar">
            <button class="btn" @click="doValidate" :disabled="!upload.rows.length">⚙ 数据校验</button>
            <button class="btn warn" @click="doPreprocess" :disabled="!upload.rows.length">✦ 数据预处理</button>
            <button class="btn success" @click="doConfirm" :disabled="!validated">✓ 确认导入</button>
          </div>
        </div>
      </section>

      <!-- 右：常驻数据预览 -->
      <section class="panel dm-preview">
        <div class="corner"></div>
        <div class="pv-head">
          <div class="col-title">{{ curType.label }} <span class="en">LIVE PREVIEW</span></div>
          <div class="pv-meta">
            <span class="meta">来源：{{ curType.file }} · 共 <b class="num c-cyan">{{ fmt(curType.count) }}</b> 条</span>
            <div class="pager" v-if="previewRows.length">
              <button class="btn sm" @click="page--" :disabled="page <= 1">‹</button>
              <span class="num">{{ page }} / {{ totalPages }}</span>
              <button class="btn sm" @click="page++" :disabled="page >= totalPages">›</button>
            </div>
          </div>
        </div>
        <div class="tbl-wrap scroll-y grow">
          <table class="tbl" v-if="previewRows.length">
            <thead>
              <tr><th v-for="c in curType.cols" :key="c">{{ c }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in pagedRows" :key="i">
                <td v-for="c in curType.cols" :key="c" class="num">{{ r[c] }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty">暂无数据</div>
        </div>
      </section>
    </main>

    <!-- 底部：导入历史横向时间线 -->
    <section class="panel dm-history">
      <div class="corner"></div>
      <div class="col-title">导入历史 <span class="en">IMPORT HISTORY</span></div>
      <div class="his-track scroll-x">
        <div class="his-card" v-for="h in history" :key="h.no">
          <div class="hc-top">
            <span class="hc-no num">#{{ h.no }}</span>
            <span class="tag ok">✓ {{ h.status }}</span>
          </div>
          <div class="hc-type">{{ h.type }}</div>
          <div class="hc-file num">{{ h.file }}</div>
          <div class="hc-foot num">
            {{ fmt(h.rows) }} 行 · {{ h.res }} · {{ h.time }} · {{ h.by }}
          </div>
        </div>
        <div v-if="!history.length" class="empty">暂无导入记录</div>
      </div>
    </section>

    <!-- 轻提示 -->
    <div class="toast" v-if="toast.show" :class="toast.type">{{ toast.text }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Papa from 'papaparse'
import * as XLSX from 'xlsx'
import TopNav from '../components/TopNav.vue'
import { fmt, loadJSON, nowStr } from '../utils/data'

const ready = ref(false)
const project = ref({})
const hourly = ref([])
const tariff = ref([])
const device = ref([])
const cost = ref([])
const optimization = ref({})
const indicators = ref([])

const selected = ref('wind')
const page = ref(1)
const pageSize = 50

const resolution = ref('1小时')
const dragging = ref(false)
const fileInput = ref(null)

// 上传状态
const upload = ref({ file: '', rows: [], columns: [] })
const mapping = ref([])
const validated = ref(false)
const checkResult = ref(null)
const preprocessMsg = ref('')
const history = ref([
  { no: 3, time: '2026-09-30 10:26:41', type: '电价数据', file: '07_华东分时电价数据.xlsx', rows: 5, res: '分时段', by: '系统初始化', status: '成功' },
  { no: 2, time: '2026-09-30 10:24:18', type: '负荷数据', file: '03_小时级源荷气象电价数据.csv', rows: 5832, res: '1小时', by: '系统初始化', status: '成功' },
  { no: 1, time: '2026-09-30 10:21:05', type: '风资源数据', file: '03_小时级源荷气象电价数据.csv', rows: 5832, res: '1小时', by: '系统初始化', status: '成功' }
])
const toast = ref({ show: false, text: '', type: 'ok' })
let toastTimer = null

function showToast (text, type = 'ok') {
  toast.value = { show: true, text, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}

// ---------- 数据类型定义（记录数来自真实数据文件） ----------
const types = computed(() => [
  { key: 'wind', label: '风资源数据', count: hourly.value.length, file: '03_小时级源荷气象电价数据.csv', cols: ['时间', '风速(m/s)', '温度(℃)'] },
  { key: 'solar', label: '光资源数据', count: hourly.value.length, file: '03_小时级源荷气象电价数据.csv', cols: ['时间', '总辐照度(W/m2)'] },
  { key: 'load', label: '负荷数据', count: hourly.value.length, file: '03_小时级源荷气象电价数据.csv', cols: ['时间', '有功负荷(MW)'] },
  { key: 'price', label: '电价数据', count: tariff.value.length, file: '07_华东分时电价数据.xlsx', cols: ['时段', '购电价格元/kWh'] },
  { key: 'device', label: '设备参数', count: device.value.length, file: '02_设备技术参数.xlsx', cols: ['设备', '参数', '数值'] },
  { key: 'cost', label: '成本参数', count: cost.value.length, file: '08_经济成本参数.xlsx', cols: ['参数', '值'] },
  { key: 'grid', label: '电网约束', count: Object.keys(optimization.value).length, file: '06_容量优化与评价结果.xlsx', cols: ['指标', '模拟结果'] },
  { key: 'friend', label: '友好数据', count: indicators.value.length, file: '9_容量配置及评价指标.xlsx', cols: ['指标', '值'] }
])
const curType = computed(() => types.value.find(t => t.key === selected.value))

// 预览行数据（统一映射为中文列名）
const previewRows = computed(() => {
  const k = curType.value.key
  if (k === 'wind') return hourly.value.map(r => ({ '时间': r.time, '风速(m/s)': r.windSpeed, '温度(℃)': r.temp }))
  if (k === 'solar') return hourly.value.map(r => ({ '时间': r.time, '总辐照度(W/m2)': r.ghi }))
  if (k === 'load') return hourly.value.map(r => ({ '时间': r.time, '有功负荷(MW)': r.load }))
  if (k === 'price') return tariff.value.map(r => ({ '时段': r.period, '购电价格元/kWh': r.price }))
  if (k === 'device') return device.value.map(r => ({ '设备': r.device, '参数': r.param, '数值': r.value }))
  if (k === 'cost') return cost.value.map(r => ({ '参数': r.param, '值': r.value }))
  if (k === 'grid') return Object.entries(optimization.value).map(([指标, 模拟结果]) => ({ '指标': 指标, '模拟结果': 模拟结果 }))
  if (k === 'friend') return indicators.value.map(r => ({ '指标': r.indicator, '值': r.value }))
  return []
})
const totalPages = computed(() => Math.max(1, Math.ceil(previewRows.value.length / pageSize)))
const pagedRows = computed(() => previewRows.value.slice((page.value - 1) * pageSize, page.value * pageSize))

function selectType (k) {
  selected.value = k
  page.value = 1
}

// ---------- 系统字段与自动匹配 ----------
const sysFields = [
  { key: 'time', name: '时间', dtype: 'datetime', unit: '—', aliases: ['时间', 'datetime', 'date', 'time', 'timestamp', '日期时间'] },
  { key: 'windSpeed', name: '风速', dtype: 'float', unit: 'm/s', aliases: ['风速', 'wind_speed', 'windspeed', 'wind'] },
  { key: 'ghi', name: '总辐照度', dtype: 'float', unit: 'W/m²', aliases: ['辐照', 'ghi', '辐射', 'irradiance'] },
  { key: 'temp', name: '温度', dtype: 'float', unit: '℃', aliases: ['温度', 'temperature', 'temp'] },
  { key: 'load', name: '有功负荷', dtype: 'float', unit: 'MW', aliases: ['负荷', 'load', 'demand'] },
  { key: 'price', name: '购电价', dtype: 'float', unit: '元/kWh', aliases: ['购电价', '电价', 'price', 'tariff'] },
  { key: 'pvAvailable', name: '光伏可用出力', dtype: 'float', unit: 'MW', aliases: ['光伏可用出力', 'pv', '光伏出力', 'photovoltaic'] }
]
const norm = s => String(s).toLowerCase().replace(/\s|\(|\)|（|）|\/|\./g, '')

function buildMapping (columns) {
  mapping.value = columns.map(col => {
    const n = norm(col)
    let hit = sysFields.find(f => f.aliases.some(a => n === norm(a) || n.includes(norm(a))))
    return {
      col,
      target: hit ? hit.key : '',
      dtype: hit ? hit.dtype : guessType(upload.value.rows[0]?.[col]),
      unit: hit ? hit.unit : '—'
    }
  })
}
function guessType (v) {
  if (v === undefined || v === null || v === '') return 'string'
  return isNaN(Number(v)) ? 'string' : 'float'
}

// ---------- 文件上传与解析 ----------
function onDrop (e) {
  dragging.value = false
  if (e.dataTransfer.files.length) parseFile(e.dataTransfer.files[0])
}
function onFileChange (e) {
  if (e.target.files.length) parseFile(e.target.files[0])
  e.target.value = ''
}

function parseFile (file) {
  const name = file.name
  if (/\.csv$/i.test(name)) {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: res => {
        upload.value = { file: name, rows: res.data, columns: res.meta.fields || [] }
        buildMapping(res.meta.fields || [])
        validated.value = false
        checkResult.value = null
        preprocessMsg.value = ''
        showToast('文件解析成功：' + name)
      },
      error: () => showToast('CSV 解析失败', 'err')
    })
  } else if (/\.xlsx?$/i.test(name)) {
    const reader = new FileReader()
    reader.onload = e => {
      try {
        const wb = XLSX.read(new Uint8Array(e.target.result), { type: 'array' })
        const ws = wb.Sheets[wb.SheetNames[0]]
        const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' })
        const cols = aoa[0].map(String)
        const rows = aoa.slice(1).filter(r => r.some(v => v !== '')).map(arr => {
          const o = {}
          cols.forEach((c, i) => { o[c] = arr[i] })
          return o
        })
        upload.value = { file: name, rows, columns: cols }
        buildMapping(cols)
        validated.value = false
        checkResult.value = null
        preprocessMsg.value = ''
        showToast('文件解析成功：' + name)
      } catch (err) {
        showToast('Excel 解析失败', 'err')
      }
    }
    reader.readAsArrayBuffer(file)
  } else {
    showToast('仅支持 .csv / .xlsx / .xls 文件', 'err')
  }
}

// ---------- 模板下载（由真实数据生成） ----------
function downloadTpl (kind) {
  let rows
  if (kind === 'wind') rows = hourly.value.slice(0, 48).map(r => ({ '时间': r.time, '风速(m/s)': r.windSpeed, '温度(℃)': r.temp }))
  else if (kind === 'solar') rows = hourly.value.slice(0, 48).map(r => ({ '时间': r.time, '总辐照度(W/m2)': r.ghi }))
  else if (kind === 'load') rows = hourly.value.slice(0, 48).map(r => ({ '时间': r.time, '有功负荷(MW)': r.load }))
  else rows = tariff.value.map(r => ({ '时段': r.period, '购电价格(元/kWh)': r.price }))
  const csv = '\uFEFF' + Papa.unparse(rows)
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  a.download = { wind: '风资源模板', solar: '光资源模板', load: '负荷模板', price: '电价模板' }[kind] + '.csv'
  a.click()
  URL.revokeObjectURL(a.href)
  showToast('模板已下载：' + a.download)
}

// ---------- 数据校验 ----------
const RANGES = {
  windSpeed: [0, 50], ghi: [0, 1500], temp: [-50, 70],
  load: [0, 1000], price: [0, 5], pvAvailable: [0, 500]
}
function doValidate () {
  const rows = upload.value.rows
  const lines = []
  let badTime = 0, nullCnt = {}, rangeCnt = 0
  const mapped = mapping.value.filter(m => m.target)
  rows.forEach(r => {
    mapped.forEach(m => {
      const v = r[m.col]
      if (m.target === 'time') {
        if (!v || isNaN(new Date(String(v).replace(/-/g, '/')).getTime())) badTime++
      } else {
        if (v === '' || v === null || v === undefined) {
          nullCnt[m.target] = (nullCnt[m.target] || 0) + 1
        } else {
          const [lo, hi] = RANGES[m.target] || [-Infinity, Infinity]
          const num = Number(v)
          if (isNaN(num) || num < lo || num > hi) rangeCnt++
        }
      }
    })
  })
  const problems = badTime + rangeCnt + Object.values(nullCnt).reduce((a, b) => a + b, 0)
  lines.push('共校验 ' + fmt(rows.length) + ' 行数据，映射字段 ' + mapped.length + ' 个')
  lines.push('时间格式异常：' + badTime + ' 条；数值越限/非法：' + rangeCnt + ' 条；缺失值：' +
    (Object.entries(nullCnt).map(([k, v]) => k + ' ' + v + ' 条').join('，') || '0 条'))
  const ok = problems === 0
  checkResult.value = { ok, lines }
  validated.value = true
  showToast(ok ? '数据校验通过，可执行预处理或直接导入' : '校验发现 ' + problems + ' 处问题，建议先执行数据预处理', ok ? 'ok' : 'warn')
}

// ---------- 数据预处理 ----------
function doPreprocess () {
  const rows = upload.value.rows
  const mapped = mapping.value.filter(m => m.target && m.target !== 'time')
  let filled = 0, dropped = 0
  // 均值填充
  mapped.forEach(m => {
    const nums = rows.map(r => Number(r[m.col])).filter(v => !isNaN(v))
    if (!nums.length) return
    const mean = +(nums.reduce((a, b) => a + b, 0) / nums.length).toFixed(2)
    rows.forEach(r => {
      const v = r[m.col]
      if (v === '' || v === null || v === undefined || isNaN(Number(v))) {
        r[m.col] = mean
        filled++
      } else {
        const [lo, hi] = RANGES[m.target] || [-Infinity, Infinity]
        if (Number(v) < lo) { r[m.col] = lo; filled++ }
        if (Number(v) > hi) { r[m.col] = hi; filled++ }
      }
    })
  })
  // 删除时间异常行
  const timeM = mapping.value.find(m => m.target === 'time')
  if (timeM) {
    for (let i = rows.length - 1; i >= 0; i--) {
      const v = rows[i][timeM.col]
      if (!v || isNaN(new Date(String(v).replace(/-/g, '/')).getTime())) { rows.splice(i, 1); dropped++ }
    }
  }
  preprocessMsg.value = '填充/修正异常值 ' + filled + ' 处（均值与边界裁剪），剔除时间异常行 ' + dropped + ' 行，剩余 ' + fmt(rows.length) + ' 行'
  checkResult.value = { ok: true, lines: ['✓ 预处理完成，数据已满足导入条件'] }
  showToast('数据预处理完成')
}

// ---------- 确认导入 ----------
let hisSeq = 4
function doConfirm () {
  const mappedFields = mapping.value.filter(m => m.target).map(m => m.target)
  const typeName = curType.value ? curType.value.label : '其他数据'
  history.value.unshift({
    no: hisSeq++,
    time: nowStr(),
    type: typeName,
    file: upload.value.file,
    rows: upload.value.rows.length,
    res: resolution.value,
    by: '管理员',
    status: '成功'
  })
  showToast('导入成功：' + upload.value.file + '（' + fmt(upload.value.rows.length) + ' 行，字段：' + mappedFields.join('、') + '）')
  upload.value = { file: '', rows: [], columns: [] }
  mapping.value = []
  checkResult.value = null
  validated.value = false
  preprocessMsg.value = ''
}

onMounted(async () => {
  const [p, h, ta, d, c, o, i] = await Promise.all([
    loadJSON('project.json'),
    loadJSON('hourly_source.json'),
    loadJSON('tariff.json'),
    loadJSON('device.json'),
    loadJSON('cost.json'),
    loadJSON('optimization.json'),
    loadJSON('indicators.json')
  ])
  project.value = p
  hourly.value = h
  tariff.value = ta
  device.value = d
  cost.value = c
  optimization.value = o
  indicators.value = i
  ready.value = true
})
</script>

<style scoped>
.dm-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-0);
}

/* ---- 横向数据类型条 ---- */
.type-bar {
  display: flex;
  gap: 8px;
  padding: 10px 12px 0;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.type-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border: 1px solid var(--panel-border);
  border-radius: 20px;
  background: rgba(9, 38, 26, .55);
  cursor: pointer;
  transition: all .2s;
}
.type-chip:hover { border-color: var(--cyan); }
.type-chip.active {
  border-color: var(--cyan);
  background: rgba(62, 230, 143, .12);
  box-shadow: 0 0 12px rgba(62, 230, 143, .15);
}
.tc-label { font-size: 12.5px; color: var(--txt-2); }
.type-chip.active .tc-label { color: var(--txt-1); font-weight: 600; }
.tc-count { font-size: 12.5px; color: var(--cyan); font-weight: 700; }
.tc-count i { font-style: normal; font-size: 9px; color: var(--txt-3); margin-left: 1px; }

/* ---- 主体双栏 ---- */
.dm-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.08fr 1fr;
  gap: 10px;
  padding: 10px 12px;
}
.panel { padding: 12px 14px; display: flex; flex-direction: column; min-height: 0; }
.col-title { font-size: 13px; font-weight: 700; color: var(--txt-1); margin-bottom: 10px; flex-shrink: 0; }
.col-title .en { font-size: 10px; color: var(--txt-3); font-weight: 400; margin-left: 4px; }

.wk-scroll { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 10px; }

.upload-row { display: flex; gap: 10px; flex-shrink: 0; }
.upload-zone {
  flex: 1;
  border: 1px dashed #2a7a54;
  border-radius: 6px;
  background: rgba(6, 28, 18, .5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 128px;
  cursor: pointer;
  transition: all .2s;
}
.upload-zone:hover, .upload-zone.dragging { border-color: var(--cyan); background: rgba(62, 230, 143, .05); box-shadow: 0 0 16px rgba(62, 230, 143, .12) inset; }
.uz-icon { font-size: 26px; }
.uz-main { font-size: 14px; color: var(--txt-1); }
.uz-sub { font-size: 11px; color: var(--txt-3); }
.upload-side { width: 240px; display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }
.blk { border: 1px solid var(--panel-border); border-radius: 4px; padding: 8px 10px; background: rgba(6, 28, 18, .5); flex: 1; }
.blk-title { font-size: 12.5px; font-weight: 600; color: var(--txt-1); margin-bottom: 6px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.tpl-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.map-title { margin: 2px 0 0; }
.upload-meta { font-size: 11.5px; color: var(--txt-3); font-weight: 400; }
.upload-meta b { color: var(--txt-1); }

.select.sm { padding: 3px 6px; font-size: 12px; max-width: 130px; }

.tbl-wrap { border: 1px solid var(--panel-border); border-radius: 4px; overflow-y: auto; max-height: 300px; }
.tbl-wrap.grow { flex: 1; max-height: none; }

.check-result {
  border: 1px solid;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 20px;
  flex-shrink: 0;
}
.check-result.ok { border-color: rgba(62, 230, 143, .4); background: rgba(62, 230, 143, .06); }
.check-result.warn { border-color: rgba(255, 181, 69, .4); background: rgba(255, 181, 69, .06); }
.cr-title { font-weight: 700; margin-bottom: 2px; }

.action-bar {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--panel-border);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-shrink: 0;
}

/* ---- 右侧预览 ---- */
.pv-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.pv-meta { display: flex; align-items: center; gap: 14px; }
.pv-meta .meta { font-size: 12px; color: var(--txt-3); }
.pv-meta .meta b { color: var(--cyan); }
.pager { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--txt-2); }

.empty { text-align: center; color: var(--txt-3); padding: 40px 0; font-size: 13px; }

/* ---- 底部历史时间线 ---- */
.dm-history { flex-shrink: 0; margin: 0 12px 12px; }
.col-title { margin-bottom: 8px; }
.his-track {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 2px;
}
.his-card {
  min-width: 240px;
  flex-shrink: 0;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  padding: 8px 12px;
  background: rgba(6, 28, 18, .55);
  position: relative;
}
.his-card::before {
  content: '';
  position: absolute;
  left: 0; top: 10px; bottom: 10px;
  width: 2px;
  background: linear-gradient(180deg, var(--cyan), transparent);
  border-radius: 2px;
}
.hc-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 3px; }
.hc-no { font-size: 12px; color: var(--cyan); font-weight: 700; }
.hc-type { font-size: 13px; color: var(--txt-1); font-weight: 600; }
.hc-file { font-size: 11px; color: var(--txt-2); margin: 2px 0 4px; }
.hc-foot { font-size: 10.5px; color: var(--txt-3); }

/* ---- toast ---- */
.toast {
  position: fixed;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 22px;
  border-radius: 4px;
  font-size: 13px;
  z-index: 99;
  border: 1px solid;
  box-shadow: 0 4px 20px rgba(0, 0, 0, .5);
}
.toast.ok { color: var(--green); border-color: rgba(62, 230, 143, .5); background: rgba(6, 30, 20, .95); }
.toast.warn { color: var(--yellow); border-color: rgba(255, 181, 69, .5); background: rgba(34, 26, 6, .95); }
.toast.err { color: var(--red); border-color: rgba(255, 93, 108, .5); background: rgba(36, 8, 12, .95); }
</style>
