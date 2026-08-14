// API 函数封装：13 个接口 + imageFileUrl
// 全部通过 client.ts 拦截器解包 {success, data}，失败抛携带 detail 的 Error
// 上传接口（uploadImages）用 FormData 的 files 字段，不设 JSON content-type（拦截器处理）
import { request } from './client'
import type {
  AliasItem,
  AliasPayload,
  ImageItem,
  ImageQuery,
  ImageUploadResult,
  OverviewData,
  Paginated,
  SyncResult,
  SystemInfo,
  VoiceActor,
  VoiceActorPatch,
} from './types'

export * from './types'

/** 图片文件 URL（供 <img>/el-image 直接展示，不走 axios，无需解包） */
export function imageFileUrl(id: number): string {
  return `/admin/api/images/${id}/file`
}

const api = {
  /** 概览统计：总量 + 24h 表现 + 最近请求日志 */
  overview(): Promise<OverviewData> {
    return request({ url: '/overview', method: 'get' })
  },

  /** 声优列表（按名称排序） */
  listVoiceActors(): Promise<VoiceActor[]> {
    return request({ url: '/voice-actors', method: 'get' })
  },

  /** 新增声优（返回新 id） */
  createVoiceActor(name: string, description = ''): Promise<{ id: number }> {
    return request({ url: '/voice-actors', method: 'post', data: { name, description } })
  },

  /** 更新声优描述 / 启用状态 */
  updateVoiceActor(id: number, patch: VoiceActorPatch): Promise<{ updated: boolean }> {
    return request({ url: `/voice-actors/${id}`, method: 'patch', data: patch })
  },

  /** 别名列表（按优先级降序，含目标声优名） */
  listAliases(): Promise<AliasItem[]> {
    return request({ url: '/aliases', method: 'get' })
  },

  /** 新增全局别名 */
  createAlias(payload: AliasPayload): Promise<{ id: number }> {
    return request({ url: '/aliases', method: 'post', data: payload })
  },

  /** 删除别名 */
  deleteAlias(id: number): Promise<{ deleted: boolean }> {
    return request({ url: `/aliases/${id}`, method: 'delete' })
  },

  /** 触发图片目录扫描与数据库同步 */
  syncImages(): Promise<SyncResult> {
    return request({ url: '/sync-images', method: 'post' })
  },

  /** 图片列表（筛选 + 服务端分页） */
  listImages(params: ImageQuery): Promise<Paginated<ImageItem>> {
    return request({ url: '/images', method: 'get', params })
  },

  /** 批量上传图片（multipart/form-data，files 字段） */
  uploadImages(files: File[], actorId: number): Promise<{ results: ImageUploadResult[] }> {
    const form = new FormData()
    for (const file of files) form.append('files', file)
    return request({
      url: '/images/upload',
      method: 'post',
      params: { voice_actor_id: actorId },
      data: form,
    })
  },

  /** 切换图片启用 / 禁用 */
  updateImage(id: number, is_active: boolean): Promise<{ updated: boolean }> {
    return request({ url: `/images/${id}`, method: 'patch', data: { is_active } })
  },

  /** 删除图片（物理文件 + 记录） */
  deleteImage(id: number): Promise<{ deleted: boolean }> {
    return request({ url: `/images/${id}`, method: 'delete' })
  },

  /** bot 进程 CPU/内存占用与系统信息 */
  systemInfo(): Promise<SystemInfo> {
    return request({ url: '/system-info', method: 'get' })
  },
}

export default api
