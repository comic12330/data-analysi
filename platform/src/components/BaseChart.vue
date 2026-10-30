<template>
  <div ref="el" class="base-chart"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true }
})

const el = ref(null)
let chart = null
let ro = null

onMounted(() => {
  chart = echarts.init(el.value)
  chart.setOption(props.option)
  ro = new ResizeObserver(() => chart && chart.resize())
  ro.observe(el.value)
})

watch(() => props.option, opt => {
  if (chart) chart.setOption(opt, { notMerge: true })
}, { deep: true })

onBeforeUnmount(() => {
  ro && ro.disconnect()
  chart && chart.dispose()
  chart = null
})
</script>

<style scoped>
.base-chart { width: 100%; height: 100%; }
</style>
