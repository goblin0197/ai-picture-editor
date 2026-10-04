// react-router-dom：Navigate 声明式重定向；Outlet 渲染匹配到的子路由。
import { Navigate, Outlet } from 'react-router-dom'

// 读取当前登录用户的 hook（内部走 React Query 请求 /api/auth/me，会话以服务端 Cookie 为准）。
import { useCurrentUser } from '@/hooks/useAuth'

// 登录守卫：作为受保护路由的父级 element 使用。
// 它自己不渲染页面内容，只负责判断「放行子路由」还是「踢回登录页」。
export default function RequireAuth() {
  // user：当前用户（未登录为 null）；isLoading：是否还在首次拉取会话状态。
  const { user, isLoading } = useCurrentUser()

  // 会话结果尚未确定时先显示占位「加载中」——
  // 否则会在拿到结果前先闪一下登录页，把已登录用户误判为未登录。
  if (isLoading) {
    return <div className="text-muted flex h-screen items-center justify-center text-sm">加载中…</div>
  }
  // 已登录 → 用 Outlet 渲染子路由（工作台各页）；
  // 未登录 → 重定向到 /auth，replace 不在历史里留下受保护地址，避免登录后按后退又跳回来。
  return user ? <Outlet /> : <Navigate to="/auth" replace />
}
