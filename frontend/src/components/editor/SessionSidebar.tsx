// 编辑器左栏：以「对话」为主体——当前会话的指令对话 + 输入框；
// 历史会话列表折叠收纳，展开时才显示（把纵向空间尽量留给对话）。
import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'

import AgentConversation from '@/components/editor/AgentConversation'
import MessageComposer from '@/components/editor/MessageComposer'
import { useSendMessage } from '@/hooks/useAgent'
import { useSessions } from '@/hooks/useSessions'
import { formatDateTime } from '@/lib/format'

export default function SessionSidebar({ activeId }: { activeId: string }) {
  // 历史对话默认收起，尽量把纵向空间留给当前对话
  const [historyOpen, setHistoryOpen] = useState(false)

  return (
    <aside className="border-line bg-paper flex w-72 shrink-0 flex-col border-r">
      {/* 顶栏：新对话入口 + 历史列表开关 */}
      <div className="border-line flex items-center gap-2 border-b p-3">
        <Link
          to="/create"
          className="border-line text-ink hover:bg-soft rounded-control flex-1 py-2 text-center text-sm font-medium transition-colors"
        >
          新对话
        </Link>
        <button
          type="button"
          onClick={() => setHistoryOpen((open) => !open)}
          aria-pressed={historyOpen}
          className={`rounded-control px-3 py-2 text-xs font-medium transition-colors ${
            historyOpen
              ? 'bg-brand-soft text-brand-strong'
              : 'text-muted hover:bg-soft hover:text-ink'
          }`}
        >
          历史
        </button>
      </div>

      {historyOpen && <SessionList activeId={activeId} />}

      {/* 主体：有会话时显示对话区，无会话时给引导文案 */}
      {activeId ? (
        <Conversation sessionId={activeId} />
      ) : (
        <p className="text-faint min-h-0 flex-1 px-4 py-4 text-xs leading-relaxed">
          打开一个历史对话，或回到创作页开始新的一张。
        </p>
      )}
    </aside>
  )
}

// 当前会话的对话区：历史轮次列表 + 底部输入框；send 成功后失效轮次缓存刷新列表
function Conversation({ sessionId }: { sessionId: string }) {
  const send = useSendMessage(sessionId)

  return (
    <>
      <AgentConversation sessionId={sessionId} />
      <MessageComposer pending={send.isPending} onSend={(text) => send.mutate(text)} />
    </>
  )
}

// 历史会话列表（折叠内容）：上限 52 高度内滚动；NavLink 高亮当前会话
function SessionList({ activeId }: { activeId: string }) {
  const { data: sessions = [], isPending } = useSessions()

  if (isPending) {
    return <p className="text-faint border-line border-b px-4 py-3 text-xs">加载中…</p>
  }

  if (sessions.length === 0) {
    return <p className="text-faint border-line border-b px-4 py-3 text-xs">还没有会话</p>
  }

  return (
    <ul className="border-line max-h-52 shrink-0 space-y-0.5 overflow-y-auto border-b p-2">
      {sessions.map((session) => (
        <li key={session.id}>
          {/* NavLink 在路径匹配时自动加 active 类；这里手动比对 id 控制高亮 */}
          <NavLink
            to={`/editor/${session.id}`}
            className={`block rounded-[10px] px-2.5 py-2 transition-colors ${
              session.id === activeId
                ? 'bg-brand-soft text-brand-strong'
                : 'text-muted hover:bg-soft hover:text-ink'
            }`}
          >
            <span className="block truncate text-xs font-medium">{session.title}</span>
            <span className="text-faint block text-[10px] tabular-nums">
              {formatDateTime(session.updated_at)}
            </span>
          </NavLink>
        </li>
      ))}
    </ul>
  )
}
