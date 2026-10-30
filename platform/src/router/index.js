import { createRouter, createWebHashHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/data', name: 'data', component: () => import('../views/DataManageView.vue') },
  { path: '/report', name: 'report', component: () => import('../views/ReportGenView.vue') },
  { path: '/optimize', name: 'optimize', component: () => import('../views/OptimizeView.vue') }
]

export default createRouter({
  history: createWebHashHistory(),
  routes
})
