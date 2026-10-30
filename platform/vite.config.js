import fs from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const require = createRequire(import.meta.url)
const XLSX = require('xlsx')

// 项目根目录（课程实验），data 与平台目录的上级
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const DATA_DIR = path.join(ROOT, 'data')
const BACKUP_DIR = path.join(DATA_DIR, '_backup')

// 导入类型对应的原始数据文件
const TYPE_FILE = {
  wind: '03_小时级源荷气象电价数据.csv',
  solar: '03_小时级源荷气象电价数据.csv',
  load: '03_小时级源荷气象电价数据.csv',
  price: '03_小时级源荷气象电价数据.csv',
  q15: '04_典型日15分钟运行曲线.csv',
  device: '02_设备技术参数.xlsx',
  cost: '08_经济成本参数.xlsx',
  tariff: '07_华东分时电价数据.xlsx'
}

// 系统字段对应的原始文件列名
const FIELD_COL = {
  windSpeed: '风速(m/s)',
  ghi: '总辐照度(W/m2)',
  temp: '温度(℃)',
  load: '有功负荷(MW)',
  price: '购电价(元/kWh)',
  pvAvailable: '光伏可用出力(MW)'
}

const pad = n => String(n).padStart(2, '0')

// 统一时间格式，兼容 2026/1/1 0:00、2026-01-01 00:00、00:00 三种写法
function normTime (v) {
  const s = String(v).trim().replace(/\//g, '-')
  const m = s.match(/(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2})/)
  if (m) return `${m[1]}-${pad(m[2])}-${pad(m[3])} ${pad(m[4])}:${m[5]}`
  const hm = s.match(/^(\d{1,2}):(\d{2})/)
  if (hm) return `${pad(hm[1])}:${hm[2]}`
  return s
}

function splitCsvLine (line) {
  const out = []
  let cur = ''
  let quoted = false
  for (const ch of line) {
    if (ch === '"') quoted = !quoted
    else if (ch === ',' && !quoted) { out.push(cur); cur = '' }
    else cur += ch
  }
  out.push(cur)
  return out
}

function saveBackup (files) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const dir = path.join(BACKUP_DIR, stamp)
  fs.mkdirSync(dir, { recursive: true })
  files.forEach(f => {
    const src = path.join(DATA_DIR, f)
    if (fs.existsSync(src)) fs.copyFileSync(src, path.join(dir, f))
  })
  return dir
}

// 写回 CSV：导入行与原文件行数一致时按行序替换，否则按时间键匹配
function writeCsv (fp, rows, mapping) {
  const raw = fs.readFileSync(fp, 'utf8').replace(/^\uFEFF/, '')
  const lines = raw.split(/\r?\n/).filter((l, i) => i === 0 || l.trim() !== '')
  const head = splitCsvLine(lines[0]).map(s => s.trim())
  const timeIdx = head.findIndex(h => h === '时间' || h === 'time')
  const body = lines.slice(1).map(l => splitCsvLine(l))
  const cols = mapping
    .filter(m => m.target && FIELD_COL[m.target])
    .map(m => ({ idx: head.indexOf(FIELD_COL[m.target]), src: m.col }))
    .filter(c => c.idx >= 0)

  if (!cols.length) return { updated: 0, skipped: rows.length, cols: 0 }

  let updated = 0
  let skipped = 0
  const sameSize = rows.length === body.length

  if (sameSize) {
    body.forEach((cells, i) => {
      cols.forEach(c => {
        const v = rows[i][c.src]
        if (v !== undefined && v !== null && v !== '') { cells[c.idx] = String(v); updated++ }
      })
    })
    skipped = 0
  } else {
    const idx = {}
    body.forEach((cells, i) => { if (timeIdx >= 0) idx[normTime(cells[timeIdx])] = i })
    rows.forEach(r => {
      const timeCell = timeIdx >= 0 ? r[mapping.find(m => m.target === 'time')?.col] : null
      const at = timeIdx >= 0 ? idx[normTime(timeCell)] : -1
      if (at === undefined) { skipped++; return }
      cols.forEach(c => {
        const v = r[c.src]
        if (v !== undefined && v !== null && v !== '') { body[at][c.idx] = String(v); updated++ }
      })
    })
  }

  const out = '\uFEFF' + [head, ...body].map(cells => cells.join(',')).join('\r\n') + '\r\n'
  if (!updated) return { updated, skipped, cols: cols.length }
  fs.writeFileSync(fp, out, 'utf8')
  return { updated, skipped, cols: cols.length }
}

// 写回 Excel：按首列键值更新指定列，列名支持多个候选写法
function pickValue (row, names) {
  for (const n of names) {
    if (row[n] !== undefined && row[n] !== null && row[n] !== '') return row[n]
  }
  return undefined
}

function firstIndex (head, names) {
  for (const n of names) {
    const i = head.indexOf(n)
    if (i >= 0) return i
  }
  return -1
}

function writeXlsx (fp, rows, keyNames, valNames) {
  const wb = XLSX.readFile(fp)
  const ws = wb.Sheets[wb.SheetNames[0]]
  const aoa = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' })
  const head = aoa[0].map(s => String(s).trim())
  const kIdx = firstIndex(head, keyNames)
  const vIdx = firstIndex(head, valNames)
  if (kIdx < 0 || vIdx < 0) return { updated: 0, skipped: rows.length, cols: 0 }

  const map = {}
  aoa.slice(1).forEach((cells, i) => {
    if (cells[kIdx] !== undefined) map[String(cells[kIdx]).trim()] = i + 1
  })

  let updated = 0
  let skipped = 0
  rows.forEach(r => {
    const k = String(pickValue(r, keyNames) ?? '').trim()
    const at = map[k]
    if (at === undefined) { skipped++; return }
    const v = pickValue(r, valNames)
    if (v !== undefined) { aoa[at][vIdx] = v; updated++ }
  })

  wb.Sheets[wb.SheetNames[0]] = XLSX.utils.aoa_to_sheet(aoa)
  if (!updated) return { updated, skipped, cols: 1 }
  XLSX.writeFile(wb, fp)
  return { updated, skipped, cols: 1 }
}

// 依次执行三个计算脚本，生成平台所需的 JSON
const SCRIPTS = ['prepare_data.py', 'predict.py', 'optimize.py']

function pythonBin () {
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN
  const local = 'D:/Anaconda3/envs/data_analysis/python.exe'
  if (fs.existsSync(local)) return local
  return 'python'
}

function importApi () {
  let job = { running: false, step: '', log: [], error: '', startedAt: '', finishedAt: '' }

  function runScripts (onDone) {
    const py = pythonBin()
    let i = 0
    const next = () => {
      if (i >= SCRIPTS.length) {
        job.running = false
        job.step = '完成'
        job.finishedAt = new Date().toISOString()
        onDone()
        return
      }
      const name = SCRIPTS[i++]
      job.step = name
      job.log.push('运行 ' + name)
      const cp = spawn(py, [name], { cwd: ROOT })
      const push = chunk => {
        String(chunk).split(/\r?\n/).filter(Boolean).forEach(l => {
          job.log.push(l)
          if (job.log.length > 300) job.log.shift()
        })
      }
      cp.stdout.on('data', push)
      cp.stderr.on('data', push)
      cp.on('close', code => {
        if (code !== 0) {
          job.error = name + ' 退出码 ' + code
          job.running = false
          job.step = '失败'
          return
        }
        next()
      })
    }
    next()
  }

  return {
    name: 'import-api',
    configureServer (server) {
      server.middlewares.use('/api/import', (req, res) => {
        res.setHeader('Content-Type', 'application/json; charset=utf-8')

        if (req.method === 'GET') {
          res.end(JSON.stringify(job))
          return
        }
        if (req.method !== 'POST') {
          res.statusCode = 405
          res.end(JSON.stringify({ error: '仅支持 POST' }))
          return
        }

        let body = ''
        req.on('data', c => { body += c })
        req.on('end', () => {
          if (job.running) {
            res.statusCode = 409
            res.end(JSON.stringify({ error: '已有导入任务在执行' }))
            return
          }

          let payload
          try { payload = JSON.parse(body) } catch (e) {
            res.statusCode = 400
            res.end(JSON.stringify({ error: '请求体不是合法 JSON' }))
            return
          }

          const { type, rows, mapping } = payload
          const file = TYPE_FILE[type]
          if (!file || !Array.isArray(rows) || !rows.length) {
            res.statusCode = 400
            res.end(JSON.stringify({ error: '缺少 type 或 rows' }))
            return
          }
          if (!Array.isArray(mapping) || (!mapping.length && /\.csv$/i.test(file))) {
            res.statusCode = 400
            res.end(JSON.stringify({ error: '缺少字段映射' }))
            return
          }

          const fp = path.join(DATA_DIR, file)
          if (!fs.existsSync(fp)) {
            res.statusCode = 404
            res.end(JSON.stringify({ error: '原始数据文件不存在：' + file }))
            return
          }

          let result
          try {
            const backup = saveBackup([file])
            if (/\.csv$/i.test(file)) {
              result = writeCsv(fp, rows, mapping)
            } else if (type === 'device') {
              result = writeXlsx(fp, rows, ['参数'], ['数值'])
            } else if (type === 'cost') {
              result = writeXlsx(fp, rows, ['参数'], ['值', '数值'])
            } else if (type === 'tariff') {
              result = writeXlsx(fp, rows, ['时段'], ['购电价格元/kWh', '购电价格(元/kWh)', '购电价格'])
            } else {
              throw new Error('该类型暂不支持写回')
            }
            result.backup = path.relative(ROOT, backup).replace(/\\/g, '/')
          } catch (e) {
            res.statusCode = 500
            res.end(JSON.stringify({ error: '写回失败：' + e.message }))
            return
          }

          // 没有任何行匹配时不改动数据，也不触发重算
          if (!result.updated) {
            res.statusCode = 400
            res.end(JSON.stringify({
              error: '未匹配到任何记录，请检查关键列取值是否与原始文件一致',
              ...result
            }))
            return
          }

          job = { running: true, step: '写入完成', log: ['已写回 ' + file + '，更新 ' + result.updated + ' 处'], error: '', startedAt: new Date().toISOString(), finishedAt: '' }
          runScripts(() => {})

          res.end(JSON.stringify({ ok: true, ...result }))
        })
      })
    }
  }
}

export default defineConfig({
  base: './',
  plugins: [vue(), importApi()],
  server: {
    host: '127.0.0.1',
    port: 5173
  },
  build: {
    chunkSizeWarningLimit: 1500
  }
})
