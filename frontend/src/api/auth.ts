import { api } from '@/api/client'

// User：后端返回的当前用户信息（仅暴露 id 与用户名，不含敏感字段）。
export type User = { id: string; username: string }
// Credentials：注册 / 登录共用的凭据入参。
export type Credentials = { username: string; password: string }

// authApi：账号领域的接口封装，全部走通用 api（同源相对路径）。
export const authApi = {
  // 注册：成功后后端会种下会话 Cookie，并返回新用户。
  register: (body: Credentials) => api.post<User>('/auth/register', body),
  // 登录：校验通过后同样种 Cookie 并返回用户。
  login: (body: Credentials) => api.post<User>('/auth/login', body),
  // 登出：清除服务端会话（后端返回 204，故泛型为 void）。
  logout: () => api.post<void>('/auth/logout'),
  // me：读取当前登录用户；未登录时后端返回 401，上层据此判定为未认证。
  me: () => api.get<User>('/auth/me'),
}
