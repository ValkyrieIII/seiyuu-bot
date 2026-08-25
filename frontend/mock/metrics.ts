import type { MockMethod } from 'vite-plugin-mock'
import { ok, parseQuery } from './_utils'

function buildSeries(range: string) {
  const count = range === '24h' ? 24 : range === '7d' ? 7 : 30
  const step = range === '24h' ? 3_600_000 : 86_400_000
  const now = Date.now()
  return Array.from({ length: count }, (_, index) => {
    const total = 5 + ((index * 7) % 19)
    return {
      bucket: new Date(now - (count - 1 - index) * step).toISOString().slice(0, 19),
      total,
      success: Math.max(0, total - (index % 5 === 0 ? 2 : 1)),
    }
  })
}

export default [{
  url: '/admin/api/metrics',
  method: 'get',
  response: ({ url }: { url?: string }) => {
    const range = parseQuery(url).range || '24h'
    const time_series = buildSeries(range)
    const total = time_series.reduce((sum, point) => sum + point.total, 0)
    return ok({
      range,
      from: time_series[0]?.bucket,
      to: new Date().toISOString(),
      total_requests: total,
      success_rate: 92.6,
      duration_ms: { p50: 186, p95: 641, p99: 1180 },
      active_users: 83,
      active_groups: 12,
      status_distribution: { success: total - 18, error: 4, cooldown: 7, notfound: 3, no_image: 2, file_missing: 2 },
      time_series,
      top_voice_actors: [
        { id: 1, name: '中岛由贵', requests: 62 },
        { id: 2, name: '花澤香菜', requests: 48 },
        { id: 3, name: '水树奈奈', requests: 31 },
      ],
      recent_error_codes: [{ error_code: 'IMAGE_FILE_MISSING', count: 2, last_seen_at: new Date().toISOString() }],
      queue: { accepted: 1024, dropped: 1, written: 1000, write_failures: 1, failed_events: 23, backlog: 0, capacity: 2048 },
      system: { cpu_percent: 8.2, memory_mb: 236.4, memory_total_mb: 8192, memory_percent: 2.9, disk_used_gb: 26.1, disk_total_gb: 80, disk_percent: 32.6, uptime_seconds: 912345, cpu_model: 'Mock CPU', sampled_at: Date.now() / 1000 },
    })
  },
}] satisfies MockMethod[]
