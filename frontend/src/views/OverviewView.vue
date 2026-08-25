<script setup lang="ts">
import { computed, onActivated, onDeactivated, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import api from '../api'
import type { KnownObservabilityStatus, MetricsData, ObservabilityStatus, ReadinessData } from '../api'

defineOptions({ name: 'OverviewView' })

type RangeKey = '24h' | '7d' | '30d'
type TagType = 'success' | 'danger' | 'warning' | 'info' | 'primary'

const rangeKey = ref<RangeKey>('24h')
const loading = ref(false)
const metrics = ref<MetricsData | null>(null)
const readiness = ref<ReadinessData | null>(null)
let timer: number | undefined
let lastError = ''

/** Record forces compile-time coverage whenever KnownObservabilityStatus grows. */
const knownStatusMeta: Record<KnownObservabilityStatus, { label: string; tagType: TagType }> = {
  success: { label: '成功', tagType: 'success' },
  error: { label: '错误', tagType: 'danger' },
  cooldown: { label: '冷却', tagType: 'warning' },
  notfound: { label: '未找到', tagType: 'info' },
  no_image: { label: '无图片', tagType: 'warning' },
  file_missing: { label: '文件缺失', tagType: 'danger' },
}

function statusMetaOf(status: ObservabilityStatus) {
  return knownStatusMeta[status as KnownObservabilityStatus] ?? {
    label: `未知（${status}）`,
    tagType: 'info' as TagType,
  }
}

const maxTrend = computed(() =>
  Math.max(1, ...(metrics.value?.time_series.map((point) => point.total) ?? [1])),
)
const maxActorRequests = computed(() =>
  Math.max(1, ...(metrics.value?.top_voice_actors.map((actor) => actor.requests) ?? [1])),
)
const statusRows = computed(() =>
  Object.entries(metrics.value?.status_distribution ?? {}).map(([status, count]) => ({
    status,
    count,
    percentage: metrics.value?.total_requests
      ? Math.round((count / metrics.value.total_requests) * 1000) / 10
      : 0,
  })),
)

function formatDuration(value: number | null | undefined): string {
  if (value == null) return '-'
  return value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(2)} s`
}

function formatUptime(seconds = 0): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return days ? `${days}天 ${hours}小时` : `${hours}小时 ${minutes}分`
}

function formatBucket(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  if (rangeKey.value === '24h') return `${String(date.getHours()).padStart(2, '0')}:00`
  return `${date.getMonth() + 1}/${date.getDate()}`
}

async function loadAll() {
  loading.value = true
  try {
    const [nextMetrics, nextReadiness] = await Promise.all([
      api.metrics(rangeKey.value),
      api.readiness(),
    ])
    metrics.value = nextMetrics
    readiness.value = nextReadiness
    lastError = ''
  } catch (error) {
    const message = error instanceof Error ? error.message : '加载运行指标失败'
    if (message !== lastError) ElMessage.error(message)
    lastError = message
  } finally {
    loading.value = false
  }
}

function stopTimer() {
  if (timer !== undefined) window.clearInterval(timer)
  timer = undefined
}
function startTimer() {
  stopTimer()
  timer = window.setInterval(() => void loadAll(), 30_000)
}

watch(rangeKey, () => void loadAll())
onMounted(() => { void loadAll(); startTimer() })
onActivated(startTimer)
onDeactivated(stopTimer)
</script>

<template>
  <div class="overview" v-loading="loading">
    <div class="toolbar">
      <el-radio-group v-model="rangeKey">
        <el-radio-button value="24h">24 小时</el-radio-button>
        <el-radio-button value="7d">7 天</el-radio-button>
        <el-radio-button value="30d">30 天</el-radio-button>
      </el-radio-group>
      <el-button type="primary" :loading="loading" @click="loadAll">刷新</el-button>
    </div>

    <div class="stat-grid">
      <el-card shadow="never"><el-statistic title="请求量" :value="metrics?.total_requests ?? 0" /></el-card>
      <el-card shadow="never"><el-statistic title="成功率" :value="metrics?.success_rate ?? 0" :precision="1" suffix="%" /></el-card>
      <el-card shadow="never"><div class="text-stat"><span>P95 耗时</span><strong>{{ formatDuration(metrics?.duration_ms.p95) }}</strong></div></el-card>
      <el-card shadow="never"><el-statistic title="活跃用户" :value="metrics?.active_users ?? 0" /></el-card>
      <el-card shadow="never"><el-statistic title="活跃群" :value="metrics?.active_groups ?? 0" /></el-card>
      <el-card shadow="never"><div class="text-stat"><span>运行时长</span><strong>{{ formatUptime(metrics?.system.uptime_seconds) }}</strong></div></el-card>
    </div>

    <el-row :gutter="16" class="content-row">
      <el-col :xs="24" :lg="16">
        <el-card shadow="never">
          <template #header><span class="card-title">请求趋势</span></template>
          <div class="trend-chart">
            <div v-for="point in metrics?.time_series ?? []" :key="point.bucket" class="trend-column">
              <div class="trend-count">{{ point.total }}</div>
              <div class="trend-track">
                <div class="trend-success" :style="{ height: `${(point.success / maxTrend) * 100}%` }" />
                <div class="trend-failed" :style="{ height: `${((point.total - point.success) / maxTrend) * 100}%` }" />
              </div>
              <div class="trend-label">{{ formatBucket(point.bucket) }}</div>
            </div>
          </div>
          <div class="legend"><span class="dot success-dot" />成功 <span class="dot failed-dot" />其他</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="fill-card">
          <template #header><span class="card-title">状态分布</span></template>
          <div v-for="row in statusRows" :key="row.status" class="status-row">
            <div class="status-head">
              <el-tag :type="statusMetaOf(row.status).tagType" size="small">{{ statusMetaOf(row.status).label }}</el-tag>
              <span>{{ row.count }}</span>
            </div>
            <el-progress :percentage="row.percentage" :stroke-width="8" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="content-row">
      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="fill-card">
          <template #header><span class="card-title">热门声优</span></template>
          <el-empty v-if="!metrics?.top_voice_actors.length" description="暂无数据" :image-size="70" />
          <div v-for="(actor, index) in metrics?.top_voice_actors ?? []" :key="actor.id" class="actor-row">
            <span class="actor-rank">{{ index + 1 }}</span>
            <div class="actor-main">
              <div class="actor-title"><span>{{ actor.name }}</span><span>{{ actor.requests }}</span></div>
              <div class="actor-bar"><span :style="{ width: `${(actor.requests / maxActorRequests) * 100}%` }" /></div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="fill-card">
          <template #header><span class="card-title">系统资源</span></template>
          <div class="resource-row"><span>CPU</span><el-progress :percentage="metrics?.system.cpu_percent ?? 0" /></div>
          <div class="resource-row"><span>内存 {{ metrics?.system.memory_mb ?? 0 }} MB</span><el-progress :percentage="metrics?.system.memory_percent ?? 0" /></div>
          <div class="resource-row"><span>磁盘 {{ metrics?.system.disk_used_gb ?? 0 }} / {{ metrics?.system.disk_total_gb ?? 0 }} GB</span><el-progress :percentage="metrics?.system.disk_percent ?? 0" /></div>
          <div class="percentiles">
            <span>P50 {{ formatDuration(metrics?.duration_ms.p50) }}</span>
            <span>P95 {{ formatDuration(metrics?.duration_ms.p95) }}</span>
            <span>P99 {{ formatDuration(metrics?.duration_ms.p99) }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card shadow="never" class="fill-card">
          <template #header><span class="card-title">就绪与统计队列</span></template>
          <div class="readiness-row"><span>数据库</span><el-tag :type="readiness?.database.ready ? 'success' : 'danger'">{{ readiness?.database.ready ? '可用' : '不可用' }}</el-tag></div>
          <div class="readiness-row"><span>OneBot</span><el-tag :type="readiness?.onebot.ready ? 'success' : 'danger'">{{ readiness?.onebot.ready ? '已连接' : '未连接' }}</el-tag></div>
          <el-divider />
          <div class="queue-grid">
            <div><strong>{{ metrics?.queue.backlog ?? 0 }}</strong><span>当前积压</span></div>
            <div><strong>{{ metrics?.queue.dropped ?? 0 }}</strong><span>累计丢弃</span></div>
            <div><strong>{{ metrics?.queue.write_failures ?? 0 }}</strong><span>写入失败批次</span></div>
            <div><strong>{{ metrics?.queue.failed_events ?? 0 }}</strong><span>失败事件</span></div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="metrics?.recent_error_codes.length" shadow="never" class="content-row">
      <template #header><span class="card-title">最近错误码</span></template>
      <el-table :data="metrics.recent_error_codes" size="small" stripe>
        <el-table-column prop="error_code" label="错误码" />
        <el-table-column prop="count" label="次数" width="100" />
        <el-table-column prop="last_seen_at" label="最近出现" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 16px; }
.text-stat { display: flex; flex-direction: column; }.text-stat span { color: var(--el-text-color-regular); font-size: 14px; }.text-stat strong { margin-top: 8px; color: var(--el-text-color-primary); font-size: 24px; font-weight: 400; line-height: 1.4; }
.content-row { margin-top: 16px; }.fill-card { height: calc(100% - 16px); }.card-title { font-weight: 600; }
.trend-chart { height: 245px; display: flex; align-items: flex-end; gap: 6px; overflow-x: auto; padding: 8px 2px 0; }
.trend-column { min-width: 24px; flex: 1; height: 100%; display: flex; flex-direction: column; align-items: center; }
.trend-count { height: 20px; color: var(--el-text-color-secondary); font-size: 11px; }.trend-track { flex: 1; width: 70%; display: flex; flex-direction: column-reverse; background: var(--el-fill-color-light); border-radius: 3px 3px 0 0; overflow: hidden; }
.trend-success { background: var(--el-color-success); }.trend-failed { background: var(--el-color-danger-light-3); }.trend-label { height: 30px; padding-top: 7px; color: var(--el-text-color-secondary); font-size: 10px; white-space: nowrap; }
.legend { display: flex; justify-content: flex-end; align-items: center; gap: 6px; color: var(--el-text-color-secondary); font-size: 12px; }.dot { width: 8px; height: 8px; border-radius: 50%; margin-left: 8px; }.success-dot { background: var(--el-color-success); }.failed-dot { background: var(--el-color-danger-light-3); }
.status-row { margin-bottom: 13px; }.status-head { display: flex; justify-content: space-between; margin-bottom: 6px; }
.actor-row { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }.actor-rank { width: 22px; color: var(--el-text-color-secondary); text-align: center; }.actor-main { flex: 1; }.actor-title { display: flex; justify-content: space-between; font-size: 14px; }.actor-bar { height: 5px; margin-top: 5px; background: var(--el-fill-color); border-radius: 3px; overflow: hidden; }.actor-bar span { display: block; height: 100%; background: var(--el-color-primary); }
.resource-row { margin-bottom: 18px; }.resource-row > span { display: block; margin-bottom: 7px; font-size: 13px; }.percentiles { display: flex; justify-content: space-between; color: var(--el-text-color-secondary); font-size: 12px; }
.readiness-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }.queue-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }.queue-grid div { display: flex; flex-direction: column; }.queue-grid strong { font-size: 20px; }.queue-grid span { color: var(--el-text-color-secondary); font-size: 12px; }
@media (max-width: 767px) { .toolbar { align-items: flex-start; flex-direction: column; }.trend-column { min-width: 28px; } }
</style>
