// 声优管理接口：
//   GET   /admin/api/voice-actors          列表（按名称排序）
//   POST  /admin/api/voice-actors          新增（副作用：写入内存数组，列表立即可查）
//   PATCH /admin/api/voice-actors/:id      更新 description / is_active
// 行为与状态码/错误信息与 backend/bot/admin/routes.py 逐字段对齐
import type { MockMethod } from 'vite-plugin-mock'
import { ok, fail, respond, extractPathId } from './_utils'
import { actors, nextActorId } from './_data'
import type { MockActor } from './_data'

export default [
  {
    url: '/admin/api/voice-actors',
    method: 'get',
    timeout: 300,
    response: () =>
      ok(
        [...actors]
          .sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'))
          .map((a) => ({ id: a.id, name: a.name, description: a.description, image_count: a.image_count, is_active: a.is_active })),
      ),
  },
  {
    url: '/admin/api/voice-actors',
    method: 'post',
    timeout: 400,
    async rawResponse(req, res) {
      const body = await this.parseJson()
      const name = String(body?.name ?? '').trim()
      if (!name) {
        respond(res, 400, fail('name cannot be empty'))
        return
      }
      if (actors.some((a) => a.name === name)) {
        respond(res, 409, fail('voice actor already exists'))
        return
      }
      const actor: MockActor = {
        id: nextActorId(),
        name,
        description: String(body?.description ?? '').trim(),
        image_count: 0,
        is_active: true,
      }
      actors.push(actor)
      respond(res, 200, ok({ id: actor.id }))
    },
  },
  {
    url: '/admin/api/voice-actors/:id',
    method: 'patch',
    timeout: 400,
    async rawResponse(req, res) {
      const id = extractPathId(req.url)
      const actor = actors.find((a) => a.id === id)
      if (!actor) {
        respond(res, 404, fail('voice actor not found'))
        return
      }
      const body = await this.parseJson()
      const hasDescription = body?.description !== undefined && body?.description !== null
      const hasIsActive = body?.is_active !== undefined && body?.is_active !== null
      if (!hasDescription && !hasIsActive) {
        respond(res, 400, fail('no fields to update'))
        return
      }
      if (hasDescription) actor.description = String(body.description).trim()
      if (hasIsActive) actor.is_active = Boolean(body.is_active)
      respond(res, 200, ok({ updated: true }))
    },
  },
] satisfies MockMethod[]
