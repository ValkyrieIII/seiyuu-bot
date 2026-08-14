<script setup lang="ts">
// 管理后台整体布局：左侧导航 + 顶栏 + 内容区（路由出口）
// 菜单项与路由一一对应，el-menu 的 router 模式直接以 path 为 index 完成 hash 导航
// 配色沿用原面板风格：深蓝侧边栏（#1c2a3d）+ 暖色内容底（#f5f0e8）+ 品牌红强调（#c2473a）
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <div class="admin-logo">seiyuu-bot 管理后台</div>
      <el-menu
        class="admin-menu"
        :default-active="route.path"
        router
        background-color="#1c2a3d"
        text-color="#c8c0b8"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/overview">概览</el-menu-item>
        <el-menu-item index="/actors">声优管理</el-menu-item>
        <el-menu-item index="/images">图片管理</el-menu-item>
        <el-menu-item index="/aliases">别名管理</el-menu-item>
        <el-menu-item index="/sync">图片同步</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="admin-body">
      <el-header class="admin-header" height="56px">
        <span class="admin-header-title">{{ route.meta.title }}</span>
      </el-header>
      <el-main class="admin-main">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  height: 100vh;
}

.admin-aside {
  display: flex;
  flex-direction: column;
  background-color: #1c2a3d;
}

.admin-logo {
  height: 56px;
  line-height: 56px;
  padding: 0 16px;
  color: #fff;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-menu {
  flex: 1;
  border-right: none;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background-color: #c2473a;
}

.admin-body {
  min-width: 0;
}

.admin-header {
  display: flex;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
}

.admin-header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.admin-main {
  background-color: #f5f0e8;
}
</style>
