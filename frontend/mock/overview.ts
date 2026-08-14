// GET /admin/api/overview —— 概览统计
// 响应字段与 backend/bot/admin/routes.py overview() 逐字段对齐：
// voice_actor_total/image_total/alias_total 取内存数据实时值（增删改后随之变化）
import type { MockMethod } from 'vite-plugin-mock'
import { ok } from './_utils'
import { actors, images, aliases } from './_data'

// 最近 20 条请求日志（相对模块加载时间生成，保持“最新”观感），覆盖 success/error/cooldown 三种状态
const now = Date.now()
// [user_id, group_id, status, response_time_ms, 分钟前, error_message]
const logsSeed: Array<[number, number, 'success' | 'error' | 'cooldown', number, number, string | null]> = [
  [288403733, 864501236, 'success', 187, 3, null],
  [2675338092, 934210578, 'success', 342, 8, null],
  [3499812267, 1056723489, 'cooldown', 12, 11, '冷却中，剩余 45 秒'],
  [1528967345, 768431025, 'success', 254, 17, null],
  [4012238765, 1012345678, 'error', 892, 23, '图片文件不存在或已损坏'],
  [3345617789, 892345671, 'success', 128, 29, null],
  [2890123456, 976543218, 'success', 465, 36, null],
  [3109876543, 853210476, 'cooldown', 9, 45, '冷却中，剩余 32 秒'],
  [3567210988, 1029384756, 'success', 213, 52, null],
  [2746159042, 918273645, 'error', 675, 61, '别名解析失败：未找到目标声优'],
  [3301876542, 876543219, 'success', 391, 70, null],
  [4023567891, 987654321, 'success', 154, 82, null],
  [2954310876, 908172635, 'cooldown', 14, 95, '冷却中，剩余 18 秒'],
  [3812093456, 819273645, 'success', 502, 110, null],
  [4123876540, 1072635489, 'error', 923, 128, '目录扫描失败：权限不足'],
  [3265987412, 901234567, 'success', 236, 145, null],
  [3571290864, 861204537, 'success', 448, 168, null],
  [3945621780, 790123456, 'success', 173, 190, null],
  [3158702345, 680123457, 'success', 367, 215, null],
  [2754310987, 570123458, 'success', 289, 240, null],
]

const recentLogs = logsSeed.map(([user_id, group_id, status, response_time_ms, minutesAgo, error_message], index) => ({
  id: 1000 + index,
  user_id,
  group_id,
  command: 'voice_actor',
  status,
  response_time_ms,
  error_message,
  created_at: new Date(now - minutesAgo * 60_000).toISOString().slice(0, 19),
}))

export default [
  {
    url: '/admin/api/overview',
    method: 'get',
    timeout: 400,
    response: () =>
      ok({
        voice_actor_total: actors.length,
        image_total: images.length,
        alias_total: aliases.length,
        request_24h: 217,
        success_rate_24h: 93.1,
        recent_logs: recentLogs,
      }),
  },
] satisfies MockMethod[]
