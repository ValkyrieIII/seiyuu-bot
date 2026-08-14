<script setup lang="ts">
// 应用根组件：Element Plus 中文 locale（zh-cn）+ 路由出口
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>

<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>
