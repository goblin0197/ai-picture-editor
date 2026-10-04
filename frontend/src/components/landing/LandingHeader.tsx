import { Link } from 'react-router-dom'

import BrandMark from '@/components/BrandMark'

// 落地页顶部导航栏：左侧品牌标识（回首页），右侧按登录态显示不同入口。
// props.account：当前用户名，登录时为字符串、未登录时为 null，由 LandingPage 从当前用户解出后下发。
export default function LandingHeader({ account }: { account: string | null }) {
  return (
    // sticky top-0 让导航栏滚动时吸顶；z-10 压在内容之上；backdrop-blur + 半透明底色形成毛玻璃效果
    <header className="border-line/70 bg-canvas/80 sticky top-0 z-10 border-b backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
        {/* 左侧品牌区：统一用 BrandMark 组件（不手写 logo），点击回首页；aria-label 提供无障碍名称 */}
        <Link to="/" aria-label="AI 修图智能体首页">
          <BrandMark size="sm">
            <span className="text-ink text-sm font-semibold">AI 修图智能体</span>
          </BrandMark>
        </Link>

        {/* 右侧入口按登录态二选一 */}
        {account ? (
          // 已登录：显示「用户名 · 进入工作台」的按钮，直接进 /create
          <Link
            to="/create"
            className="border-line-strong text-ink hover:bg-soft rounded-control border px-3.5 py-1.5 text-sm font-medium transition-colors"
          >
            {account} · 进入工作台
          </Link>
        ) : (
          // 未登录：显示低调的「登录」文字链接，去 /auth
          <Link to="/auth" className="text-muted hover:text-ink text-sm transition-colors">
            登录
          </Link>
        )}
      </div>
    </header>
  )
}
