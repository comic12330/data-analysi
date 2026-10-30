<template>
  <header class="topnav">
    <div class="tn-brand">
      <span class="tn-logo">
        <svg viewBox="0 0 24 24" width="16" height="16"><path d="M13 2 L5 14 h5 l-1 8 8-12 h-5 z" fill="currentColor"/></svg>
      </span>
      <span class="tn-name">源网荷储仿真平台</span>
    </div>
    <nav class="tn-nav">
      <router-link to="/dashboard" :class="{ active: route.name === 'dashboard' }">仿真大屏</router-link>
      <router-link to="/data" :class="{ active: route.name === 'data' }">数据管理</router-link>
      <router-link to="/report" :class="{ active: route.name === 'report' }">报告生成</router-link>
      <router-link to="/optimize" :class="{ active: route.name === 'optimize' }">智能优化</router-link>
    </nav>
    <div class="tn-right">
      <span class="tn-project">{{ project.name }} <i class="run">● 运行中</i></span>
      <span class="tn-clock num">{{ now }}</span>
      <span class="tn-avatar">ZH</span>
    </div>
  </header>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { nowStr } from '../utils/data'

defineProps({
  project: { type: Object, required: true }
})

const route = useRoute()
const now = ref(nowStr())
let timer = null
onMounted(() => { timer = setInterval(() => { now.value = nowStr() }, 1000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.topnav {
  height: 46px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 28px;
  background: linear-gradient(90deg, rgba(6, 28, 18, .96), rgba(11, 46, 30, .92));
  border-bottom: 1px solid var(--panel-border);
  flex-shrink: 0;
}
.tn-brand { display: flex; align-items: center; gap: 8px; }
.tn-logo {
  width: 24px; height: 24px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--cyan), #1db977);
  color: #04150d;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 10px rgba(62, 230, 143, .4);
}
.tn-name { font-size: 14px; font-weight: 700; letter-spacing: 1px; color: var(--txt-1); white-space: nowrap; }
@media (max-width: 1080px) {
  .tn-project { display: none; }
}
@media (max-width: 860px) {
  .tn-name { display: none; }
}

.tn-nav { display: flex; gap: 4px; height: 100%; }
.tn-nav a {
  position: relative;
  display: flex;
  align-items: center;
  padding: 0 18px;
  font-size: 13.5px;
  color: var(--txt-2);
  transition: color .2s;
}
.tn-nav a:hover { color: var(--txt-1); }
.tn-nav a.active { color: var(--cyan); font-weight: 600; }
.tn-nav a.active::after {
  content: '';
  position: absolute;
  left: 14px; right: 14px; bottom: 0;
  height: 2px;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
  border-radius: 2px 2px 0 0;
}

.tn-right { margin-left: auto; display: flex; align-items: center; gap: 14px; }
.tn-project { font-size: 12px; color: var(--txt-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px; min-width: 0; }
.tn-project .run { font-style: normal; color: var(--green); font-size: 11px; }
.tn-clock { font-size: 12.5px; color: var(--txt-2); }
.tn-avatar {
  width: 26px; height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2ec98a, var(--cyan));
  color: #04150d;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
