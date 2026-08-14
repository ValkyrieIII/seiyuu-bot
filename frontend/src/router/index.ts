// 应用路由表：hash 模式（createWebHashHistory，与原面板 hash 路由习惯一致）
// 顶层布局路由 AdminLayout 挂 5 个子页；Task 5-8 将逐个替换占位组件为真实页面
import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

import AdminLayout from '../layouts/AdminLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: AdminLayout,
    redirect: '/overview',
    children: [
      {
        path: 'overview',
        name: 'overview',
        meta: { title: '概览' },
        component: () => import('../views/OverviewView.vue'),
      },
      {
        path: 'actors',
        name: 'actors',
        meta: { title: '声优管理' },
        component: () => import('../views/ActorsView.vue'),
      },
      {
        path: 'images',
        name: 'images',
        meta: { title: '图片管理' },
        component: () => import('../views/ImagesView.vue'),
      },
      {
        path: 'aliases',
        name: 'aliases',
        meta: { title: '别名管理' },
        component: () => import('../views/AliasesView.vue'),
      },
      {
        path: 'sync',
        name: 'sync',
        meta: { title: '图片同步' },
        component: () => import('../views/SyncView.vue'),
      },
    ],
  },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
