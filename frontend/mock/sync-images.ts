// POST /admin/api/sync-images —— 触发图片目录扫描与数据库同步
// 响应五项统计，字段与 backend/bot/admin/routes.py sync_images() 逐字段对齐
import type { MockMethod } from 'vite-plugin-mock'
import { ok } from './_utils'

export default [
  {
    url: '/admin/api/sync-images',
    method: 'post',
    timeout: 800,
    response: () =>
      ok({
        added_actors: 1,
        disabled_actors: 0,
        added_images: 3,
        updated_images: 2,
        disabled_images: 0,
      }),
  },
] satisfies MockMethod[]
