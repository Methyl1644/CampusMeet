import axios, { type AxiosInstance } from 'axios'
import type { ApiResponse } from '@shared/types'
import { useAuthStore } from '@/store/authStore'

const baseURL = import.meta.env.VITE_API_BASE_URL || ''

const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 65000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截：自动携带 token
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一处理
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const token = useAuthStore.getState().token
    const isLocalDemo = import.meta.env.DEV && token === 'local-demo-token'
    if (error.response?.status === 401 && !isLocalDemo) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

/** GET 请求 */
export async function get<T>(url: string, params?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  const res = await client.get<ApiResponse<T>>(url, { params, signal })
  return res.data.data
}

/** POST 请求 */
export async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await client.post<ApiResponse<T>>(url, body)
  return res.data.data
}

/** PATCH 请求 */
export async function patch<T>(url: string, body?: unknown): Promise<T> {
  const res = await client.patch<ApiResponse<T>>(url, body)
  return res.data.data
}

export { client }
export default client
