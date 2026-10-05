// 编辑器顶部工具栏：会话标题行内改名、画幅/修订号信息、缩放控制与图层面板开关。
import { useState } from 'react'

import type { LayerDocument } from '@/api/sessions'
import { ZOOM_STEP, useCanvasView } from '@/stores/canvasView'

export default function EditorToolbar({
  title,
  revision,
  document,
  layersOpen,
  onRename,
  onToggleLayers,
}: {
  title: string
  revision: number
  document: LayerDocument
  layersOpen: boolean
  onRename: (title: string) => void
  onToggleLayers: () => void
}) {
  // 缩放操作直接调 store；与画布滚轮共享同一份视图状态
  const { scale, fit, zoomBy, zoomTo } = useCanvasView()

  return (
    <header className="border-line bg-paper flex h-14 shrink-0 items-center gap-3 border-b px-4">
      <TitleField value={title} onCommit={onRename} />

      {/* 画幅尺寸与修订号：修订号在切图/采用候选后递增，可据此判断状态新鲜度 */}
      <span className="text-faint shrink-0 text-xs tabular-nums">
        {document.width} × {document.height} · 第 {revision} 版
      </span>

      {/* 缩放控制组：－ / 百分比（点按回到 100%） / ＋ / 适应 */}
      <div className="border-line rounded-control ml-auto flex shrink-0 items-center gap-0.5 border p-0.5">
        <ZoomButton label="缩小" onClick={() => zoomBy(1 / ZOOM_STEP)}>
          －
        </ZoomButton>
        <button
          type="button"
          onClick={() => zoomTo(1)}
          title="实际像素"
          className="text-muted hover:text-ink w-14 rounded-[6px] px-1 py-1 text-xs font-medium tabular-nums transition-colors"
        >
          {Math.round(scale * 100)}%
        </button>
        <ZoomButton label="放大" onClick={() => zoomBy(ZOOM_STEP)}>
          ＋
        </ZoomButton>
        <button
          type="button"
          onClick={() => fit(document)}
          className="text-muted hover:text-ink rounded-[6px] px-2 py-1 text-xs font-medium transition-colors"
        >
          适应
        </button>
      </div>

      {/* 图层面板开关：按下态用品牌浅底标识 */}
      <button
        type="button"
        onClick={onToggleLayers}
        aria-pressed={layersOpen}
        className={`rounded-control shrink-0 px-3 py-1.5 text-xs font-medium transition-colors ${
          layersOpen ? 'bg-brand-soft text-brand-strong' : 'text-muted hover:bg-soft hover:text-ink'
        }`}
      >
        图层
      </button>
    </header>
  )
}

// 缩放按钮：仅包一层无障碍 label 与样式
function ZoomButton({
  label,
  onClick,
  children,
}: {
  label: string
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className="text-muted hover:text-ink grid size-7 place-items-center rounded-[6px] text-sm transition-colors"
    >
      {children}
    </button>
  )
}

// 标题输入框：受控草稿 + 失焦提交模式；Esc 放弃、Enter 等价失焦。
function TitleField({ value, onCommit }: { value: string; onCommit: (title: string) => void }) {
  // draft 为 null 表示未编辑，此时直接跟随服务端标题
  const [draft, setDraft] = useState<string | null>(null)

  const commit = () => {
    const next = draft?.trim()
    setDraft(null) // 无论是否提交都退出编辑态，回到跟随服务端标题
    // 空串/未变化不发起请求
    if (next && next !== value) onCommit(next)
  }

  return (
    <input
      value={draft ?? value}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === 'Enter') event.currentTarget.blur()
        if (event.key === 'Escape') setDraft(null)
      }}
      aria-label="会话标题"
      className="text-ink hover:bg-soft focus:bg-soft min-w-0 flex-1 rounded-[8px] px-2 py-1 text-sm font-medium outline-none"
    />
  )
}
