// GET /admin/api/system-info —— bot 进程 CPU/内存占用与系统信息
// 字段与 backend/bot/admin/routes.py system_info() 逐字段对齐
import type { MockMethod } from 'vite-plugin-mock'
import { ok } from './_utils'

export default [
  {
    url: '/admin/api/system-info',
    method: 'get',
    timeout: 200,
    response: () =>
      ok({
        cpu_percent: 23.5,
        memory_mb: 412.6,
        memory_total_mb: 8192,
        cpu_model: 'Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz',
      }),
  },
] satisfies MockMethod[]
