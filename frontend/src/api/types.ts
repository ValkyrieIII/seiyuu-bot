// API 数据类型定义：与 Global Constraints 接口清单逐字段对齐
// 对照 backend/bot/admin/routes.py（真实契约）与 frontend/mock/（开发假数据）
// 字段命名沿用后端 snake_case；created_at 为 ISO 字符串

/** 声优（GET /voice-actors 列表项） */
export interface VoiceActor {
  id: number
  name: string
  description: string
  image_count: number
  is_active: boolean
}

/** 图片（GET /images 分页列表项） */
export interface ImageItem {
  id: number
  voice_actor_id: number
  voice_actor_name: string
  filename: string
  file_path: string
  size_kb: number
  file_hash: string
  is_active: boolean
  /** ISO 字符串；真实后端在记录无时间时返回 null */
  created_at: string | null
}

/** 别名（GET /aliases 列表项，联表返回目标声优名） */
export interface AliasItem {
  id: number
  alias_name: string
  target_voice_actor_id: number
  target_voice_actor_name: string
  priority: number
  is_global: boolean
  is_active: boolean
}

/** 概览统计（GET /overview） */
export interface OverviewData {
  voice_actor_total: number
  image_total: number
  alias_total: number
  request_24h: number
  success_rate_24h: number
  recent_logs: RecentLog[]
}

/** 最近请求日志（overview 内嵌） */
export interface RecentLog {
  id: number
  user_id: number
  group_id: number
  command: string
  status: ObservabilityStatus
  response_time_ms: number
  error_code: string | null
  /** ISO 字符串；真实后端在记录无时间时返回 null */
  created_at: string | null
}

/** 图片同步结果（POST /sync-images） */
export interface SyncResult {
  added_actors: number
  disabled_actors: number
  added_images: number
  updated_images: number
  disabled_images: number
}

/** 系统信息（GET /system-info） */
export interface SystemInfo {
  cpu_percent: number
  memory_mb: number
  memory_total_mb: number
  memory_percent: number
  disk_used_gb: number
  disk_total_gb: number
  disk_percent: number
  uptime_seconds: number
  cpu_model: string
  sampled_at: number
}

export type KnownObservabilityStatus =
  | 'success'
  | 'error'
  | 'cooldown'
  | 'no_image'
  | 'file_missing'

/** Backend may add a state before this frontend is upgraded. */
export type ObservabilityStatus = KnownObservabilityStatus | (string & {})

export interface MetricsPoint {
  bucket: string
  total: number
  success: number
}

export interface TopVoiceActor {
  id: number
  name: string
  requests: number
}

export interface RecentErrorCode {
  error_code: string
  count: number
  last_seen_at: string
}

export interface QueueMetrics {
  accepted: number
  dropped: number
  written: number
  write_failures: number
  failed_events: number
  backlog: number
  capacity: number
}

export interface MetricsData {
  range: '24h' | '7d' | '30d'
  from: string
  to: string
  total_requests: number
  success_rate: number
  duration_ms: { p50: number | null; p95: number | null; p99: number | null }
  active_users: number
  active_groups: number
  status_distribution: Record<string, number>
  time_series: MetricsPoint[]
  top_voice_actors: TopVoiceActor[]
  recent_error_codes: RecentErrorCode[]
  queue: QueueMetrics
  system: SystemInfo
}

export interface DependencyReadiness {
  ready: boolean
  error_code: string | null
}

export interface ReadinessData {
  ready: boolean
  database: DependencyReadiness
  onebot: DependencyReadiness & { connected_bots: number }
}

// ---------- 请求参数与辅助类型 ----------

/** PATCH /voice-actors/:id 请求体（字段可选，至少提供一个） */
export interface VoiceActorPatch {
  description?: string
  is_active?: boolean
}

/** POST /aliases 请求体 */
export interface AliasPayload {
  alias_name: string
  target_voice_actor_id: number
  priority?: number
  description?: string
}

/** GET /images 查询参数（均为可选的筛选/分页项） */
export interface ImageQuery {
  voice_actor_id?: number
  is_active?: boolean
  search?: string
  page?: number
  page_size?: number
}

/** POST /images/upload 单文件结果（status 为 ok/error 联合类型） */
export interface ImageUploadResult {
  filename: string
  status: 'ok' | 'error'
  /** 失败原因（status 为 error 时存在） */
  detail?: string
  /** 以下字段仅成功时存在 */
  id?: number
  voice_actor_id?: number
  size_kb?: number
}

/** 服务端分页响应（GET /images） */
export interface Paginated<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}
