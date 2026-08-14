<script setup lang="ts">
// 概览页：总量统计（5 个 el-statistic）+ 最近 20 条请求表格 + 系统资源占用
// 默认 30s 自动刷新（el-radio-group 可选 10s/30s/60s/关闭，与原面板刷新行为一致），另有手动刷新按钮
// 数据源：Task 3 的 api.overview() + api.systemInfo()，dev 模式由 mock 拦截 /admin/api/*
import { computed, onActivated, onDeactivated, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import api from '../api'
import type { OverviewData, RecentLog, SystemInfo } from '../api'

// 显式组件名：AdminLayout 的 keep-alive 靠 name 匹配缓存实例
defineOptions({ name: 'OverviewView' })

const loading = ref(false)
const overview = ref<OverviewData | null>(null)
const systemInfo = ref<SystemInfo | null>(null)

/** 自动刷新间隔（秒），0 表示关闭；默认 30s */
const autoRefreshSeconds = ref(30)

/** 最近请求：最多渲染 20 条（前端兜底，防止后端返回超量数据） */
const recentLogs = computed<RecentLog[]>(() => overview.value?.recent_logs?.slice(0, 20) ?? [])

let timer: number | undefined
let lastErrorMsg = ''

/** 请求状态 → 中文文案 + el-tag 颜色（success/error/cooldown） */
const statusMeta: Record<RecentLog['status'], { label: string; tagType: 'success' | 'danger' | 'warning' }> = {
  success: { label: '成功', tagType: 'success' },
  error: { label: '失败', tagType: 'danger' },
  cooldown: { label: '冷却', tagType: 'warning' },
}

/** 状态元信息兜底：未知/异常 status 按 success 显示，避免取 undefined 后 .tagType 崩溃整表渲染 */
function statusMetaOf(status: string): { label: string; tagType: 'success' | 'danger' | 'warning' } {
  return statusMeta[status as RecentLog['status']] ?? statusMeta.success
}

/** ISO 时间 → "MM-DD HH:mm:ss"；真实后端可能返回 null，显示 '-' */
function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/** 耗时：<1000ms 显示毫秒，否则显示秒；为 null/undefined（真实后端可能缺省）时显示 '-' */
function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '-'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

/** 内存占用百分比（0-100），用于 el-progress */
const memoryPercent = computed<number>(() => {
  const info = systemInfo.value
  if (!info || !info.memory_total_mb) return 0
  return Math.min(100, Math.round(((info.memory_mb || 0) / info.memory_total_mb) * 100))
})

function cpuProgressFormat(_percent: number): string {
  return systemInfo.value ? `${systemInfo.value.cpu_percent.toFixed(1)}%` : '0%'
}

function memoryProgressFormat(_percent: number): string {
  const info = systemInfo.value
  if (!info) return '0 / 0 MB'
  return `${info.memory_mb.toFixed(1)} / ${info.memory_total_mb} MB`
}

async function loadAll() {
  loading.value = true
  try {
    const [o, s] = await Promise.all([api.overview(), api.systemInfo()])
    overview.value = o
    systemInfo.value = s
    lastErrorMsg = ''
  } catch (e) {
    // 自动刷新失败时只提示一次，避免 30s 一次重复弹窗
    const msg = e instanceof Error ? e.message : '加载失败'
    if (msg !== lastErrorMsg) {
      lastErrorMsg = msg
      ElMessage.error(msg)
    }
  } finally {
    loading.value = false
  }
}

function stopTimer() {
  if (timer !== undefined) {
    window.clearInterval(timer)
    timer = undefined
  }
}

/** 按当前选择的间隔重建定时器（切换间隔 / 初次挂载时调用） */
function restartTimer() {
  stopTimer()
  if (autoRefreshSeconds.value > 0) {
    timer = window.setInterval(() => void loadAll(), autoRefreshSeconds.value * 1000)
  }
}

onMounted(() => {
  void loadAll()
  restartTimer()
})

// keep-alive 缓存后组件不卸载：切走暂停自动刷新定时器，切回恢复，避免后台空跑
onActivated(() => {
  restartTimer()
})

onDeactivated(stopTimer)
</script>

<template>
  <div class="overview">
    <!-- 顶部：5 个总量统计 -->
    <div class="stat-grid">
      <el-card shadow="never">
        <el-statistic title="声优总数" :value="overview?.voice_actor_total ?? 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="图片总数" :value="overview?.image_total ?? 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="别名总数" :value="overview?.alias_total ?? 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="24h 请求量" :value="overview?.request_24h ?? 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic
          title="24h 成功率"
          :value="overview?.success_rate_24h ?? 0"
          :precision="1"
          suffix="%"
        />
      </el-card>
    </div>

    <!-- 最近请求 + 系统信息 -->
    <el-row :gutter="16" class="content-row">
      <el-col :span="16">
        <el-card shadow="never" class="logs-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">最近 20 条请求</span>
              <div class="refresh-controls">
                <el-radio-group v-model="autoRefreshSeconds" size="small" @change="restartTimer">
                  <el-radio-button :value="10">10s</el-radio-button>
                  <el-radio-button :value="30">30s</el-radio-button>
                  <el-radio-button :value="60">60s</el-radio-button>
                  <el-radio-button :value="0">关闭</el-radio-button>
                </el-radio-group>
                <el-button size="small" type="primary" :loading="loading" @click="loadAll">
                  刷新
                </el-button>
              </div>
            </div>
          </template>
          <el-table :data="recentLogs" :loading="loading" stripe size="default">
            <el-table-column label="时间" min-width="150">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="用户" prop="user_id" min-width="110" />
            <el-table-column label="状态" min-width="90">
              <template #default="{ row }">
                <el-tag :type="statusMetaOf(row.status).tagType" size="small">
                  {{ statusMetaOf(row.status).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="耗时" min-width="90">
              <template #default="{ row }">
                {{ formatDuration(row.response_time_ms) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="sys-card">
          <template #header>
            <span class="card-title">系统信息</span>
          </template>
          <div class="sys-row">
            <div class="sys-label">CPU 占用</div>
            <el-progress
              :percentage="systemInfo?.cpu_percent ?? 0"
              :format="cpuProgressFormat"
              :stroke-width="14"
            />
          </div>
          <div class="sys-row">
            <div class="sys-label">内存占用</div>
            <el-progress
              :percentage="memoryPercent"
              :format="memoryProgressFormat"
              :stroke-width="14"
            />
          </div>
          <div class="sys-model" title="CPU 型号">
            {{ systemInfo?.cpu_model ?? '加载中…' }}
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.content-row {
  margin-top: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.card-title {
  font-weight: 600;
}

.refresh-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sys-row {
  margin-bottom: 18px;
}

.sys-label {
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.sys-model {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  word-break: break-all;
}
</style>
