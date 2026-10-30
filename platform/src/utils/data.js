// 数据加载与公共工具
const cache = {}

export function loadJSON (name) {
  if (!cache[name]) {
    cache[name] = fetch(import.meta.env.BASE_URL + 'data/' + name)
      .then(r => {
        if (!r.ok) throw new Error('加载失败: ' + name)
        return r.json()
      })
  }
  return cache[name]
}

// 格式化数字：千分位
export function fmt (v, digits = 0) {
  if (v === null || v === undefined || isNaN(v)) return '--'
  return Number(v).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  })
}

// 当前时间字符串
export function nowStr () {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()) +
    ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds())
}

// ECharts 公共深色主题片段（绿色零碳主题）
export const chartTheme = {
  textStyle: { color: '#9ccbbb', fontFamily: 'Microsoft YaHei' },
  legend: {
    textStyle: { color: '#9ccbbb', fontSize: 11 },
    itemWidth: 14,
    itemHeight: 8,
    icon: 'roundRect'
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#2a6b4a' } },
    axisTick: { show: false },
    axisLabel: { color: '#5f8a78', fontSize: 10 },
    splitLine: { show: false }
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#5f8a78', fontSize: 10 },
    splitLine: { lineStyle: { color: 'rgba(20, 67, 45, .5)', type: 'dashed' } }
  },
  tooltip: {
    backgroundColor: 'rgba(6, 28, 18, .95)',
    borderColor: '#1c5c3e',
    textStyle: { color: '#e0f7ec', fontSize: 12 }
  }
}
