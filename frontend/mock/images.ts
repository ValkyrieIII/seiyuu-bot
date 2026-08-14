// 图片管理接口：
//   GET  /admin/api/images?voice_actor_id&is_active&search&page&page_size  列表（筛选 + 服务端分页）
//   POST /admin/api/images/upload?voice_actor_id=  multipart files[]        上传（副作用：写入内存数组 + 声优 image_count+1）
//   PATCH  /admin/api/images/:id     更新 is_active
//   DELETE /admin/api/images/:id     删除（副作用：移除记录 + 声优 image_count-1）
//   GET  /admin/api/images/:id/file  返回图片文件（mock 用占位图）
// 行为与状态码/错误信息与 backend/bot/admin/routes.py 逐字段对齐
import { extname } from 'node:path'
import { createHash } from 'node:crypto'
import type { MockMethod } from 'vite-plugin-mock'
import { ok, fail, respond, extractPathId, parseQuery, parseBool, collectBody, parseMultipart, VALID_EXTENSIONS, PLACEHOLDER_PNG } from './_utils'
import { actors, images, nextImageId } from './_data'
import type { MockImage } from './_data'

const toImageDto = (img: MockImage) => {
  const actor = actors.find((a) => a.id === img.voice_actor_id)
  return {
    id: img.id,
    voice_actor_id: img.voice_actor_id,
    voice_actor_name: actor?.name ?? '(未知)',
    filename: img.filename,
    file_path: img.file_path,
    size_kb: img.size_kb,
    file_hash: img.file_hash,
    is_active: img.is_active,
    created_at: img.created_at,
  }
}

export default [
  {
    url: '/admin/api/images',
    method: 'get',
    timeout: 400,
    response: ({ query }) => {
      const q = query as Record<string, string>
      const voiceActorId = q.voice_actor_id ? Number(q.voice_actor_id) : undefined
      const isActive = parseBool(q.is_active)
      const search = (q.search ?? '').trim().toLowerCase()
      // 分页参数对齐后端：page >= 1，page_size 默认 20、上限 100
      let page = Number(q.page)
      if (!Number.isInteger(page) || page < 1) page = 1
      let pageSize = Number(q.page_size)
      if (!Number.isInteger(pageSize) || pageSize < 1) pageSize = 20
      if (pageSize > 100) pageSize = 100

      const rows = [...images]
        .filter((img) => voiceActorId === undefined || img.voice_actor_id === voiceActorId)
        .filter((img) => isActive === undefined || img.is_active === isActive)
        .filter((img) => !search || img.filename.toLowerCase().includes(search))
        .sort((a, b) => b.created_at.localeCompare(a.created_at))

      const total = rows.length
      const items = rows.slice((page - 1) * pageSize, page * pageSize).map(toImageDto)
      return ok({ total, page, page_size: pageSize, items })
    },
  },
  {
    url: '/admin/api/images/upload',
    method: 'post',
    timeout: 800,
    async rawResponse(req, res) {
      const query = parseQuery(req.url)
      const actorId = Number(query.voice_actor_id)
      if (!Number.isInteger(actorId)) {
        respond(res, 400, fail('voice_actor_id is required'))
        return
      }
      const actor = actors.find((a) => a.id === actorId && a.is_active)
      if (!actor) {
        respond(res, 404, fail('voice actor not found or inactive'))
        return
      }

      const files = parseMultipart(await collectBody(req), req.headers['content-type'])

      // 该声优目录下现有最大序号（对齐后端 max_seq 逻辑，新文件名继续递增）
      let maxSeq = 0
      for (const img of images) {
        if (img.voice_actor_id !== actorId) continue
        const m = /_(\d+)$/.exec(img.filename.replace(/\.[^.]+$/, ''))
        if (m) maxSeq = Math.max(maxSeq, Number(m[1]))
      }

      const results: Array<Record<string, unknown>> = []
      for (const file of files) {
        const ext = extname(file.filename).toLowerCase()
        if (!VALID_EXTENSIONS.includes(ext)) {
          results.push({ filename: file.filename, status: 'error', detail: `unsupported file type: ${ext}` })
          continue
        }
        const fileHash = createHash('md5').update(file.content).digest('hex')
        const sizeKb = Math.max(1, Math.floor(file.content.length / 1024))
        maxSeq += 1
        const newFilename = `${actor.name}_${String(maxSeq).padStart(3, '0')}${ext}`
        const image: MockImage = {
          id: nextImageId(),
          voice_actor_id: actorId,
          filename: newFilename,
          file_path: `/app/images/${actor.name}/${newFilename}`,
          size_kb: sizeKb,
          file_hash: fileHash,
          is_active: true,
          created_at: new Date().toISOString().slice(0, 19),
        }
        images.push(image)
        actor.image_count += 1
        results.push({ filename: newFilename, status: 'ok', id: image.id, voice_actor_id: actorId, size_kb: sizeKb })
      }
      respond(res, 200, ok({ results }))
    },
  },
  {
    url: '/admin/api/images/:id/file',
    method: 'get',
    timeout: 200,
    rawResponse(req, res) {
      const id = extractPathId(req.url)
      if (!images.some((img) => img.id === id)) {
        respond(res, 404, fail('image not found'))
        return
      }
      // 占位图：返回内置 320x320 PNG（真实后端返回磁盘图片文件）
      const buf = Buffer.from(PLACEHOLDER_PNG, 'base64')
      res.statusCode = 200
      res.setHeader('Content-Type', 'image/png')
      res.setHeader('Content-Length', String(buf.length))
      res.setHeader('Cache-Control', 'no-cache')
      res.end(buf)
    },
  },
  {
    url: '/admin/api/images/:id',
    method: 'patch',
    timeout: 400,
    async rawResponse(req, res) {
      const id = extractPathId(req.url)
      const image = images.find((img) => img.id === id)
      if (!image) {
        respond(res, 404, fail('image not found'))
        return
      }
      const body = await this.parseJson()
      if (typeof body?.is_active !== 'boolean') {
        respond(res, 400, fail('is_active is required'))
        return
      }
      image.is_active = body.is_active
      respond(res, 200, ok({ updated: true }))
    },
  },
  {
    url: '/admin/api/images/:id',
    method: 'delete',
    timeout: 400,
    rawResponse(req, res) {
      const id = extractPathId(req.url)
      const idx = images.findIndex((img) => img.id === id)
      if (idx === -1) {
        respond(res, 404, fail('image not found'))
        return
      }
      const [removed] = images.splice(idx, 1)
      const actor = actors.find((a) => a.id === removed.voice_actor_id)
      if (actor) actor.image_count = Math.max(0, actor.image_count - 1)
      respond(res, 200, ok({ deleted: true }))
    },
  },
] satisfies MockMethod[]
