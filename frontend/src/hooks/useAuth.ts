import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { authApi, type Credentials, type User } from '@/api/auth'
import { ApiError } from '@/api/client'

// 当前用户的 react-query 缓存键，读写共用同一个键。
const ME_KEY = ['auth', 'me']

/** 会话状态以服务端 Cookie 为准，前端不持有令牌，只缓存当前用户。 */
export function useCurrentUser() {
  const { data, isPending } = useQuery({
    queryKey: ME_KEY,
    queryFn: () => authApi.me(),
    // 401 表示未登录，是正常状态而非网络故障，重试没有意义，故关闭重试。
    retry: false,
    // 用户信息基本不变，登录 / 登出时会主动改缓存，故设为永不过期，避免多余的重新请求。
    staleTime: Infinity,
    // 未登录是正常状态，不作为错误向上抛
    throwOnError: false,
  })
  // data 可能为 undefined（未登录 / 加载中），统一归一化为 null 便于调用方判断登录态。
  return { user: data ?? null, isLoading: isPending }
}

// useAuthActions：登录 / 注册 / 登出三个变更操作的封装。
export function useAuthActions() {
  const queryClient = useQueryClient()
  // 登录 / 注册成功后，把返回的用户直接写进缓存，省去一次额外的 me 请求。
  const cacheUser = (user: User) => queryClient.setQueryData(ME_KEY, user)

  const login = useMutation({
    mutationFn: (body: Credentials) => authApi.login(body),
    onSuccess: cacheUser,
  })
  const register = useMutation({
    mutationFn: (body: Credentials) => authApi.register(body),
    onSuccess: cacheUser,
  })
  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    // 登出后清空整个 react-query 缓存，而非只删 ME_KEY：
    // 防止上一个用户的素材、任务等私有数据残留，被下一个登录者看到。
    onSuccess: () => queryClient.clear(),
  })

  return { login, register, logout }
}

// errorMessage：把任意异常归一化为可展示的中文文案。
// ApiError 用其 message（多为后端 detail），普通 Error 用其 message，未知类型给兜底文案。
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return error instanceof Error ? error.message : '请求失败，请稍后重试'
}
