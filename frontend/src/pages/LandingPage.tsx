// 落地页（首页）：路由 "/" 的页面组件。
// 遵循「页面组件只做组装」的约定——本文件不写任何具体 UI 与交互样式，
// 只把落地页的各个分区组件按顺序拼起来，并把「登录态」这一处跨分区共享的
// 状态在顶层算好后作为 props 下发。真正的输入状态、动效、示意图都下沉在各分区里。
import { useNavigate } from 'react-router-dom'

import CapabilityShowcase from '@/components/landing/CapabilityShowcase'
import DeliverySteps from '@/components/landing/DeliverySteps'
import LandingFooter from '@/components/landing/LandingFooter'
import LandingHeader from '@/components/landing/LandingHeader'
import LandingHero from '@/components/landing/LandingHero'
import StartBanner from '@/components/landing/StartBanner'
import { useCurrentUser } from '@/hooks/useAuth'
import { readPromptDraft, savePromptDraft } from '@/lib/promptDraft'

export default function LandingPage() {
  // 命令式跳转句柄：用户点击「开始」类按钮后由代码触发导航，而非 <Link> 声明式跳转。
  const navigate = useNavigate()
  // 当前登录用户；未登录时 user 为空。据此决定按钮文案与跳转目标（见下方 entry）。
  const { user } = useCurrentUser()

  // 未登录一律先去登录页，登录态直接进工作台
  // entry 把「按钮文案 + 跳转目标」打包成一个对象，页面里所有「开始」入口
  //（Hero 的提交按钮、底部 StartBanner、顶部 Header）都复用它，保证文案与去向一致。
  const entry = user ? { label: '进入工作台', to: '/create' } : { label: '免费开始', to: '/auth' }

  // Hero 区的提交回调：先把用户已经写好的需求草稿存起来，再跳转。
  const start = (prompt: string) => {
    // savePromptDraft：把这句需求写进 sessionStorage 草稿。
    // 因为跳转后（登录页 /auth 或工作台 /create）会渲染另一棵组件树，Hero 里的输入
    // state 随之销毁；先落草稿，落地到工作台时再用 readPromptDraft 回填，避免用户白写一遍。
    savePromptDraft(prompt)
    // 按登录态跳转到对应入口。
    navigate(entry.to)
  }

  return (
    // 最外层撑满整屏并纵向排布：头部、主体自适应撑高（flex-1）、页脚始终贴底。
    <div className="flex min-h-screen flex-col">
      {/* 顶部导航：把用户名传下去，登录态显示「进入工作台」，否则显示「登录」 */}
      <LandingHeader account={user?.username ?? null} />

      {/* 主体区：flex-1 占据头尾之间的剩余空间，把页脚推到底部 */}
      <main className="flex-1">
        {/* 首屏英雄区：需求输入 + 场景标签。initialPrompt 用草稿回填输入框， */}
        {/* submitLabel/onStart 来自上面的 entry/start，把「存草稿 + 跳转」逻辑注入进去 */}
        <LandingHero
          initialPrompt={readPromptDraft()}
          submitLabel={entry.label}
          onStart={start}
        />
        {/* 能力展示区：四张能力卡片 + 纯样式示意图 */}
        <CapabilityShowcase />
        {/* 交付流程区：四步说明从描述到导出的链路 */}
        <DeliverySteps />
        {/* 底部行动号召横幅：再放一个入口，文案与去向同样取自 entry */}
        <StartBanner label={entry.label} to={entry.to} />
      </main>

      {/* 页脚：品牌标识与一句话定位 */}
      <LandingFooter />
    </div>
  )
}
