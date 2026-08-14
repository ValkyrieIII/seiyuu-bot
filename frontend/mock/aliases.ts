// 别名管理接口：
//   GET    /admin/api/aliases          列表（按 priority 降序、id 降序；联表返回 target_voice_actor_name）
//   POST   /admin/api/aliases          新增全局别名（副作用：写入内存数组，列表立即可查）
//   DELETE /admin/api/aliases/:id      删除（副作用：从内存数组移除，列表不再出现）
// 行为与状态码/错误信息与 backend/bot/admin/routes.py 逐字段对齐
import type { MockMethod } from 'vite-plugin-mock'
import { ok, fail, respond, extractPathId } from './_utils'
import { actors, aliases, nextAliasId } from './_data'
import type { MockAlias } from './_data'

const listAliases = () =>
  ok(
    [...aliases]
      .sort((a, b) => b.priority - a.priority || b.id - a.id)
      .map((al) => {
        const actor = actors.find((a) => a.id === al.target_voice_actor_id)
        return {
          id: al.id,
          alias_name: al.alias_name,
          target_voice_actor_id: al.target_voice_actor_id,
          target_voice_actor_name: actor?.name ?? '(未知)',
          priority: al.priority,
          is_global: al.is_global,
          is_active: al.is_active,
        }
      }),
  )

export default [
  {
    url: '/admin/api/aliases',
    method: 'get',
    timeout: 300,
    response: listAliases,
  },
  {
    url: '/admin/api/aliases',
    method: 'post',
    timeout: 400,
    async rawResponse(req, res) {
      const body = await this.parseJson()
      const aliasName = String(body?.alias_name ?? '').trim()
      if (!aliasName) {
        respond(res, 400, fail('alias_name cannot be empty'))
        return
      }
      const targetId = Number(body?.target_voice_actor_id)
      if (!actors.some((a) => a.id === targetId)) {
        respond(res, 404, fail('target voice actor not found'))
        return
      }
      if (aliases.some((al) => al.alias_name === aliasName && al.is_global)) {
        respond(res, 409, fail('alias already exists'))
        return
      }
      const alias: MockAlias = {
        id: nextAliasId(),
        alias_name: aliasName,
        target_voice_actor_id: targetId,
        priority: Number(body?.priority) || 0,
        description: String(body?.description ?? '').trim(),
        is_global: true,
        is_active: true,
      }
      aliases.push(alias)
      respond(res, 200, ok({ id: alias.id }))
    },
  },
  {
    url: '/admin/api/aliases/:id',
    method: 'delete',
    timeout: 400,
    rawResponse(req, res) {
      const id = extractPathId(req.url)
      const idx = aliases.findIndex((al) => al.id === id)
      if (idx === -1) {
        respond(res, 404, fail('alias not found'))
        return
      }
      aliases.splice(idx, 1)
      respond(res, 200, ok({ deleted: true }))
    },
  },
] satisfies MockMethod[]
