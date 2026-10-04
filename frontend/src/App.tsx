// react-router-dom：BrowserRouter 用 HTML5 History API 管理地址；
// Routes/Route 声明路由表；Navigate 用于声明式重定向。
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

// 布局与守卫：RequireAuth 是登录守卫，WorkbenchLayout 是登录后的工作台外壳。
import RequireAuth from '@/layouts/RequireAuth'
import WorkbenchLayout from '@/layouts/WorkbenchLayout'
// 各页面组件（新增页面都要在下面的路由表里注册）。
import AuthPage from '@/pages/AuthPage'
import CandidatesPage from '@/pages/CandidatesPage'
import CreatePage from '@/pages/CreatePage'
import LandingPage from '@/pages/LandingPage'
import PlaceholderPage from '@/pages/PlaceholderPage'

// 应用根组件：只负责声明整张路由表，不承载业务逻辑。
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 公开页：无需登录即可访问 */}
        <Route path="/" element={<LandingPage />} />
        {/* 登录 / 注册页：同一页面用 ?mode 查询参数在两种模式间切换 */}
        <Route path="/auth" element={<AuthPage />} />

        {/* 受保护区域：父 Route 只给 element、不给 path，是一层「嵌套路由」。
            RequireAuth 作守卫——未登录会被重定向到 /auth，登录才放行内部子路由。 */}
        <Route element={<RequireAuth />}>
          {/* 再套一层工作台外壳：带侧边导航，内部用 <Outlet /> 渲染下面这些子页面 */}
          <Route element={<WorkbenchLayout />}>
            <Route path="/create" element={<CreatePage />} />
            {/* /editor 与 /batch 尚未实现，用占位页顶着（对应 AGENTS.md 的 S4、S11 等计划步骤） */}
            <Route path="/editor" element={<PlaceholderPage title="编辑" hint="功能开发中" />} />
            <Route path="/batch" element={<PlaceholderPage title="批量" hint="功能开发中" />} />
            {/* 生成任务的结果页：提交后跳到 /candidates/:runId 看进度与候选图（:runId 是路径参数） */}
            <Route path="/candidates/:runId" element={<CandidatesPage />} />
          </Route>
          {/* /marketing 同样需要登录，但不套工作台外壳（放在 WorkbenchLayout 之外） */}
          <Route path="/marketing" element={<PlaceholderPage title="导出物料" hint="功能开发中" />} />
        </Route>

        {/* 兜底：未匹配到的任意路径都重定向回首页；replace 不留历史记录，避免后退回到坏地址 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
