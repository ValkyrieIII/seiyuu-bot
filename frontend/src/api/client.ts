// API 客户端：axios 实例 + 请求/响应拦截器
// 统一响应契约：成功 {success: true, data}（与后端 ok() 一致）；错误为 HTTP 4xx/5xx + 纯 {detail} 响应体
import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'

const client = axios.create({
  baseURL: '/admin/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：上传接口传 FormData（files 字段），由浏览器自动生成 multipart boundary，
// 必须去掉 JSON content-type，否则后端无法解析 multipart 边界
client.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    config.headers.delete('Content-Type')
  }
  return config
})

// 响应拦截器：解包 {success, data}；失败（HTTP 4xx/5xx 或 2xx 但 success!==true）时抛携带 detail 的 Error
client.interceptors.response.use(
  (response) => {
    const body: unknown = response.data
    if (body && typeof body === 'object' && (body as { success?: unknown }).success === true) {
      // 解包成功：拦截器返回值即 Promise 最终 resolve 值，调用方直接拿到 data（as never 仅对齐 TS 拦截器签名）
      return (body as { data: unknown }).data as never
    }
    // 2xx 但非 {success:true}：正常后端不会走到这里，防御性兜底
    const detail = body && typeof body === 'object' ? (body as { detail?: unknown }).detail : undefined
    throw new Error(typeof detail === 'string' ? detail : `请求失败（HTTP ${response.status}）`)
  },
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const data = error.response?.data as { detail?: unknown } | undefined
      if (data && typeof data.detail === 'string') {
        // 后端错误契约：非 2xx + 纯 {detail}，直接透传 detail 文案
        return Promise.reject(new Error(data.detail))
      }
      if (error.response) {
        return Promise.reject(new Error(`请求失败（HTTP ${error.response.status}）`))
      }
    }
    // 网络错误 / 超时等无响应场景
    return Promise.reject(new Error(error instanceof Error ? error.message : '请求失败'))
  },
)

/** 类型化请求：响应拦截器已解包 {success, data}，await 结果直接就是 data */
export function request<T>(config: AxiosRequestConfig): Promise<T> {
  return client.request(config) as Promise<T>
}

export default client
