<script setup lang="ts">
// 图片同步页：触发按钮（点击后 loading）+ 结果区 5 项统计（新增/禁用声优、新增/更新/禁用图片）
// 行为对齐原面板 backend/bot/admin/static/admin.js 的 initSync：
//   - 点击 → 按钮 loading（原面板「正在执行同步中...」）→ POST /sync-images
//   - 成功：结果区展示 5 项统计（el-statistic，数量为 0 也正常展示）+「图片同步完成」提示
//   - 失败：结果区展示后端 detail 错误（el-alert）+ 错误提示；清空上一次的统计结果
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import api from '../api'
import type { SyncResult } from '../api'

// 显式组件名：AdminLayout 的 keep-alive 靠 name 匹配缓存实例
defineOptions({ name: 'SyncView' })

const syncing = ref(false)
const result = ref<SyncResult | null>(null)
const error = ref('')

async function onSync() {
  syncing.value = true
  error.value = ''
  result.value = null // 重新同步时清空上一次结果（对齐原面板点击即清空结果区）
  try {
    result.value = await api.syncImages()
    ElMessage.success('图片同步完成')
  } catch (e) {
    // 拦截器已把后端 {detail} 解包进 Error.message，直接展示
    error.value = e instanceof Error ? e.message : '同步失败'
    ElMessage.error(error.value)
  } finally {
    syncing.value = false
  }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <span class="card-title">图片同步</span>
    </template>

    <div class="sync-bar">
      <span class="sync-desc">扫描图片目录并与数据库比对同步，返回各项变更统计</span>
      <el-button type="primary" :loading="syncing" @click="onSync">开始同步</el-button>
    </div>

    <!-- 同步失败：结果区展示 detail 错误 -->
    <el-alert
      v-if="error"
      class="sync-error"
      type="error"
      show-icon
      :closable="false"
      :title="error"
    />

    <!-- 同步成功：5 项统计（新增/禁用声优、新增/更新/禁用图片），空变更时各计数为 0 正常展示 -->
    <div v-else-if="result" class="stat-grid">
      <el-card shadow="never">
        <el-statistic title="新增声优" :value="result.added_actors" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="禁用声优" :value="result.disabled_actors" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="新增图片" :value="result.added_images" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="更新图片" :value="result.updated_images" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="禁用图片" :value="result.disabled_images" />
      </el-card>
    </div>

    <!-- 未执行过 / 执行中：对齐原面板「正在执行同步中...」的占位态 -->
    <el-empty
      v-else
      class="sync-empty"
      :image-size="80"
      :description="syncing ? '正在执行同步中…' : '尚未执行同步，点击上方按钮开始'"
    />
  </el-card>
</template>

<style scoped>
.card-title {
  font-weight: 600;
}

.sync-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.sync-desc {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.sync-error {
  margin-top: 16px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.sync-empty {
  padding: 24px 0 8px;
}
</style>
