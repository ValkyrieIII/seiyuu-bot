// 通用 mock 工具：响应构造、URL/查询解析、multipart 解析、占位图
// 本文件不导出 MockMethod，仅作为共享模块被各接口 mock 文件引用
import type { IncomingMessage, ServerResponse } from 'node:http'

/** 与真实后端一致的合法图片扩展名（backend/bot/admin/routes.py VALID_EXTENSIONS） */
export const VALID_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

/** 统一成功响应结构 {success, data}（与后端 ok() 一致） */
export function ok<T>(data: T) {
  return { success: true, data }
}

/** 统一错误响应结构：非 2xx 状态码 + 纯 {detail}（与后端 FastAPI HTTPException 序列化一致，无 success 字段） */
export function fail(detail: string) {
  return { detail }
}

/** 发送 JSON 响应（rawResponse 场景，支持按请求设置状态码） */
export function respond(res: ServerResponse, status: number, data: unknown) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.end(JSON.stringify(data))
}

/** 从 /admin/api/<资源>/<id>(/file) 类 URL 中提取路径参数 id */
export function extractPathId(reqUrl: string | undefined): number | null {
  if (!reqUrl) return null
  const m = reqUrl.match(/\/admin\/api\/(?:voice-actors|aliases|images)\/(\d+)(?:\/|$)/)
  return m ? Number(m[1]) : null
}

/** 解析查询字符串为对象（值与 FastAPI Query 一致，均为字符串） */
export function parseQuery(reqUrl: string | undefined): Record<string, string> {
  const out: Record<string, string> = {}
  if (!reqUrl) return out
  const qs = reqUrl.split('?')[1]
  if (qs) new URLSearchParams(qs).forEach((v, k) => { out[k] = v })
  return out
}

/** FastAPI 风格布尔解析：true/1 → true，false/0 → false，空值/缺省 → undefined（不过滤） */
export function parseBool(v: string | undefined): boolean | undefined {
  if (v === undefined || v === '') return undefined
  return v === 'true' || v === '1'
}

// ---------- multipart/form-data 解析（图片上传接口用） ----------

export interface UploadedFile {
  name: string
  filename: string
  content: Buffer
}

/** 收集请求体原始字节 */
export async function collectBody(req: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = []
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk))
  }
  return Buffer.concat(chunks)
}

/**
 * 极简 multipart/form-data 解析：按 latin1 字节 1:1 映射做字符串切分（偏移无损），
 * 从 Content-Disposition 中提取字段名与文件名（UTF-8 字节转回中文名）。
 */
export function parseMultipart(body: Buffer, contentType: string | undefined): UploadedFile[] {
  const m = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(contentType || '')
  if (!m) return []
  const boundary = `--${m[1] || m[2]}`
  const text = body.toString('latin1')
  const files: UploadedFile[] = []
  for (const part of text.split(boundary)) {
    const headerEnd = part.indexOf('\r\n\r\n')
    if (headerEnd === -1) continue
    const headers = part.slice(0, headerEnd)
    const nameMatch = /name="([^"]*)"/.exec(headers)
    const filenameMatch = /filename="([^"]*)"/.exec(headers)
    if (!nameMatch || !filenameMatch) continue
    // 内容紧随头部空行；末尾去除下一个 boundary 前的换行与最终结束标记 "--"
    let contentStr = part.slice(headerEnd + 4)
    contentStr = contentStr.replace(/\r\n--\s*$/, '').replace(/\r?\n$/, '')
    files.push({
      name: nameMatch[1],
      filename: Buffer.from(filenameMatch[1], 'latin1').toString('utf8'),
      content: Buffer.from(contentStr, 'latin1'),
    })
  }
  return files
}

/** 占位缩略图（320x320 浅灰蓝渐变 PNG），替代 /images/{id}/file 的真实图片文件 */
export const PLACEHOLDER_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAUAAAAFACAIAAABC8jL9AAAC3UlEQVR42u3TsQpAABRAUf//Ozaj0Wi0iESISBlMfuItr06dL7h1i+3+gKQKCcDAgIEBA4OBAQMDBgYMDAYGDAwYGAwMGBgwMGBgMDBgYMDAgIHBwICBAQODgQEDAwYGDAwGBgwMGBgwMBgYMDBgYDAwYGDAwICBwcCAgYGQgcfzBZIyMBgYMDBgYDAwYGDAwICBwcCAgQEDg4EBAwMGBgwMBgYMDBgYMDAYGDAwYGAwMGBgwMCAgcHAgIEBAwMGBgMDBgYMDAYGDAwYGDAwGBgwMBAzcLc/QFIGBgMDBgYMDAYGDAwYGDAwGBgwMGBgMDBgYMDAgIHBwICBAQMDBgYDAwYGDAwGBgwMGBgwMBgYMDBgYMDAYGDAwICBwcCAgQEDAwYGAwMGBmIGbtcLSMrAYGDAwICBwcCAgQEDAwYGAwMGBgwMBgYMDBgYMDAYGDAwYGDAwGBgwMCAgcHAgIEBAwMGBgMDBgYMDBgYDAwYGDAwGBgwMGBgwMBgYMDAQMzAzXwASRkYDAwYGDAwGBgwMGBgwMBgYMDAgIHBwICBAQMDBgYDAwYGDAwYGAwMGBgwMBgYMDBgYMDAYGDAwICBAQODgQEDAwYGAwMGBgwMGBgMDBgYiBm4njYgKQODgQEDAwYGAwMGBgwMGBgMDBgYMDAYGDAwYGDAwGBgwMCAgQEDg4EBAwMGBgMDBgYMDBgYDAwYGDAwYGAwMGBgwMBgYMDAgIEBA4OBAQMDMQNXwwIkZWAwMGBgwMBgYMDAgIEBA4OBAQMDBgYDAwYGDAwYGAwMGBgwMGBgMDBgYMDAYGDAwICBAQODgQEDAwYGDAwGBgwMGBgMDBgYMDBgYDAwYGAgZuCyn4CkDAwGBgwMGBgMDBgYMDBgYDAwYGDAwGBgwMCAgQEDg4EBAwMGBgwMBgYMDBgYDAwYGDAwYGAwMGBgwMCAgcHAgIEBA4OBAQMDBgYMDAYGDAyE+AFUMRPwiMBkqQAAAABJRU5ErkJggg=='
