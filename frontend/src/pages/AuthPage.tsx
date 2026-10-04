import { useState } from 'react'
// Link 站内链接；Navigate 声明式重定向；useNavigate 编程式跳转；useSearchParams 读写 URL 查询参数。
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'

import BrandMark from '@/components/BrandMark'
// errorMessage 归一化错误文案；useAuthActions 登录/注册 mutation；useCurrentUser 读当前用户。
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'

// 两种模式：登录或注册。
type Mode = 'login' | 'register'

// 两种模式对应的文案表：标题、提交按钮文字、切换目标模式与切换提示。
const COPY: Record<Mode, { title: string; submit: string; switchTo: Mode; switchHint: string }> = {
  login: { title: '登录', submit: '登录', switchTo: 'register', switchHint: '还没有账号？注册' },
  register: {
    title: '创建账号',
    submit: '注册并进入',
    switchTo: 'login',
    switchHint: '已有账号？登录',
  },
}

// 登录 / 注册页：同一个页面用 URL 的 ?mode 参数在两种模式间切换。
export default function AuthPage() {
  // 用查询参数保存当前模式：好处是可被分享/刷新保留，也让浏览器前进后退能切换模式。
  const [params, setParams] = useSearchParams()
  // 仅当 ?mode=register 时为注册，其余（含缺省）都按登录处理。
  const mode: Mode = params.get('mode') === 'register' ? 'register' : 'login'
  const copy = COPY[mode]

  const navigate = useNavigate()
  const { user, isLoading } = useCurrentUser()
  const { login, register } = useAuthActions()
  // 按当前模式选用对应的 mutation，下面提交/报错/加载态都复用它。
  const action = mode === 'login' ? login : register

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  // 已登录用户不该停留在登录页：会话确定后若已登录，直接重定向到创作页。
  if (!isLoading && user) return <Navigate to="/create" replace />

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    // 成功后跳到创作页；replace 让登录页不留在历史里（后退不会又回到登录页）。
    action.mutate({ username, password }, { onSuccess: () => navigate('/create', { replace: true }) })
  }

  const switchMode = () => {
    // 切模式前先 reset：清掉上一模式残留的错误提示与请求状态。
    action.reset()
    setParams({ mode: copy.switchTo })
  }

  return (
    <div className="relative isolate flex min-h-screen items-center justify-center px-6 py-12">
      {/* 顶部光晕装饰，纯视觉，aria-hidden */}
      <div className="bg-glow absolute inset-x-0 top-0 h-[420px]" aria-hidden />

      <div className="relative w-full max-w-sm">
        {/* 返回首页链接 */}
        <Link to="/" className="text-muted hover:text-ink mb-6 inline-flex items-center gap-2 text-sm">
          <span aria-hidden>←</span> 返回首页
        </Link>

        {/* 表单卡片 */}
        <div className="border-line bg-paper rounded-panel shadow-panel border p-8">
          <BrandMark size="sm">
            <span className="text-ink text-sm font-semibold">AI 修图智能体</span>
          </BrandMark>

          {/* 标题随模式变化（登录 / 创建账号） */}
          <h1 className="text-ink mt-6 text-2xl font-semibold tracking-tight">{copy.title}</h1>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {/* 用户名输入（用下方 Field 子组件封装 label + input） */}
            <Field
              label="用户名"
              value={username}
              onChange={setUsername}
              autoComplete="username"
              placeholder="3–32 位字母、数字或下划线"
            />
            {/* 密码输入：autoComplete 按模式区分「现有密码」与「新密码」，配合浏览器/密码管理器 */}
            <Field
              label="密码"
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder="至少 6 位"
            />

            {/* 请求出错时展示归一化后的错误文案 */}
            {action.isError && <p className="text-danger text-sm">{errorMessage(action.error)}</p>}

            {/* 提交按钮：提交中禁用并改文案 */}
            <button
              type="submit"
              disabled={action.isPending}
              className="bg-ink hover:bg-dark rounded-control w-full py-2.5 text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              {action.isPending ? '处理中…' : copy.submit}
            </button>
          </form>

          {/* 模式切换按钮：登录 ↔ 注册 */}
          <button
            type="button"
            onClick={switchMode}
            className="text-muted hover:text-brand-strong mt-5 text-sm transition-colors"
          >
            {copy.switchHint}
          </button>
        </div>
      </div>
    </div>
  )
}

// 表单字段子组件：把「标签 + 受控输入框」打包，登录页的用户名/密码两个输入复用它。
// props：label 标签文字；value/onChange 受控值与回调；type 输入类型；autoComplete 自动填充提示；placeholder 占位符。
function Field({
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  autoComplete?: string
  placeholder?: string
}) {
  return (
    <label className="block">
      <span className="text-muted mb-1.5 block text-sm">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        placeholder={placeholder}
        required
        className="border-line bg-paper text-ink placeholder:text-faint focus:border-brand rounded-control w-full border px-3.5 py-2.5 text-sm outline-none transition-colors"
      />
    </label>
  )
}
