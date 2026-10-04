// NavLink：带「当前激活」状态的链接；Outlet：渲染子路由；useNavigate：编程式跳转。
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import BrandMark from '@/components/BrandMark'
// useAuthActions 提供登录/注册/退出的 mutation；useCurrentUser 读当前用户。
import { useAuthActions, useCurrentUser } from '@/hooks/useAuth'

// 侧边导航配置表：to 目标路由，label 文字，icon 是 SVG path 的 d 属性（用来画线性图标）。
const NAV_ITEMS = [
  { to: '/create', label: '创作', icon: 'M12 4v16m8-8H4' },
  { to: '/editor', label: '编辑', icon: 'M4 20h4L20 8l-4-4L4 16v4z' },
  { to: '/batch', label: '批量', icon: 'M4 6h16M4 12h16M4 18h10' },
]

// 导航图标子组件：把配置里的 path 字符串画成统一风格的线性图标。
// aria-hidden：纯装饰元素，读屏软件跳过它（文字标签才是可读内容）。
function NavIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="size-5 shrink-0" aria-hidden>
      <path d={path} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

/** 工作台外壳：左侧导航默认收起为图标，悬停展开文字。 */
export default function WorkbenchLayout() {
  const navigate = useNavigate()
  const { user } = useCurrentUser()
  const { logout } = useAuthActions()

  // 退出登录：清掉服务端会话后跳回首页；replace 避免用户按后退又回到工作台（此时已无会话）。
  const signOut = () =>
    logout.mutate(undefined, { onSuccess: () => navigate('/', { replace: true }) })

  return (
    <div className="flex h-screen overflow-hidden">
      {/* 侧边栏：默认宽 w-16 只露图标；group + hover:w-52 让整栏悬停时展开，
          栏内文字用 opacity-0 → group-hover:opacity-100 配合淡入（收起时只留图标） */}
      <nav className="group bg-paper border-line flex w-16 flex-col border-r py-4 transition-[width] duration-200 hover:w-52">
        <BrandMark size="sm" className="mb-6 px-5">
          {/* 品牌文字：栏收起时透明，悬停展开时淡入 */}
          <span className="text-ink truncate text-sm font-semibold opacity-0 transition-opacity group-hover:opacity-100">
            AI 修图智能体
          </span>
        </BrandMark>

        {/* 主导航区：遍历 NAV_ITEMS 渲染各入口 */}
        <ul className="flex flex-1 flex-col gap-1 px-2">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              {/* NavLink 会根据当前地址自动算出 isActive，用它切换选中/未选中样式 */}
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-[12px] px-3 py-2.5 text-sm transition-colors ${
                    isActive
                      ? 'bg-brand-soft text-brand-strong font-medium'
                      : 'text-muted hover:bg-soft hover:text-ink'
                  }`
                }
              >
                <NavIcon path={item.icon} />
                {/* 文字同样跟随侧栏悬停淡入 */}
                <span className="truncate opacity-0 transition-opacity group-hover:opacity-100">
                  {item.label}
                </span>
              </NavLink>
            </li>
          ))}
        </ul>

        {/* 底部：退出登录。title 悬停提示带用户名，收起态也能看清当前是谁 */}
        <div className="border-line mt-2 border-t px-2 pt-3">
          <button
            type="button"
            onClick={signOut}
            title={user ? `${user.username} · 退出登录` : '退出登录'}
            className="text-muted hover:bg-soft hover:text-ink flex w-full items-center gap-3 rounded-[12px] px-3 py-2.5 text-sm transition-colors"
          >
            {/* 头像位：取用户名首字母大写；取不到用户时兜底显示「?」 */}
            <span className="bg-brand-soft text-brand-strong grid size-5 shrink-0 place-items-center rounded-full text-[11px] font-semibold">
              {user?.username.slice(0, 1).toUpperCase() ?? '?'}
            </span>
            <span className="truncate opacity-0 transition-opacity group-hover:opacity-100">
              退出登录
            </span>
          </button>
        </div>
      </nav>

      {/* 右侧主内容区：子路由页面通过 Outlet 渲染在这里 */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
