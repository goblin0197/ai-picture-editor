// 编辑页：/editor（无参数=会话选择提示）与 /editor/:sessionId（工作区）。
// 布局从左到右：会话侧栏 → 工具栏/画布/图片墙 →（可选）图层面板。
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import CanvasStage from '@/components/editor/CanvasStage'
import EditorToolbar from '@/components/editor/EditorToolbar'
import ImageWall from '@/components/editor/ImageWall'
import LayerPanel from '@/components/editor/LayerPanel'
import SessionSidebar from '@/components/editor/SessionSidebar'
import { usePatchSession, useSession } from '@/hooks/useSessions'

export default function EditorPage() {
  // 无 :sessionId 时为空串——展示「选择一个会话」提示
  const { sessionId = '' } = useParams()

  return (
    <div className="flex h-full">
      <SessionSidebar activeId={sessionId} />
      {sessionId ? (
        <Workspace sessionId={sessionId} />
      ) : (
        <Notice title="选择一个会话" hint="从左侧打开历史对话，或回到创作页开始新的一张。">
          <CreateLink />
        </Notice>
      )}
    </div>
  )
}

// 工作区：拉取会话详情并组装工具栏 / 画布 / 图片墙 / 图层面板
function Workspace({ sessionId }: { sessionId: string }) {
  // 图层面板默认收起，点工具栏「图层」展开
  const [layersOpen, setLayersOpen] = useState(false)
  const { data: session, isError } = useSession(sessionId)
  // 改名 / 切换当前图都走 patch；isPending 用于禁用图片墙防连点
  const patch = usePatchSession(sessionId)

  // asset_id → 签名 URL 的映射：画布图层经它取图（Memo 避免每次渲染重建 Map）
  const urls = useMemo(
    () => new Map((session?.assets ?? []).map((asset) => [asset.id, asset.url])),
    [session?.assets],
  )

  if (isError) {
    return (
      <Notice title="会话不存在" hint="链接可能已失效，回到创作页新建一个。">
        <CreateLink />
      </Notice>
    )
  }

  // 详情未返回时的占位（useSession 已按 id 启用查询，必有返回）
  if (!session) {
    return <Notice title="加载中" hint="正在读取会话状态" />
  }

  return (
    <>
      <div className="flex min-w-0 flex-1 flex-col">
        {/* 顶栏：改名/缩放/图层面板开关 */}
        <EditorToolbar
          title={session.title}
          revision={session.revision}
          document={session.document}
          layersOpen={layersOpen}
          onRename={(title) => patch.mutate({ title })}
          onToggleLayers={() => setLayersOpen((open) => !open)}
        />

        {/* 画布占满剩余高度（min-h-0 允许 flex 子项收缩，否则会被内容撑开） */}
        <div className="min-h-0 flex-1">
          <CanvasStage document={session.document} urls={urls} />
        </div>

        {/* 图片墙：点缩略图 = 切换画布当前图 */}
        <ImageWall
          assets={session.assets}
          currentId={session.current_asset_id}
          disabled={patch.isPending}
          onPick={(current_asset_id) => patch.mutate({ current_asset_id })}
        />
      </div>

      {/* 图层面板浮在右侧，收起时不占位 */}
      {layersOpen && <LayerPanel session={session} />}
    </>
  )
}

// 「去创作」按钮：无会话/会话失效时的出口
function CreateLink() {
  return (
    <Link
      to="/create"
      className="bg-ink hover:bg-dark rounded-control mt-5 px-4 py-2 text-sm font-medium text-white"
    >
      去创作
    </Link>
  )
}

// 居中提示块：本页多种状态（未选择/加载中/不存在）复用
function Notice({
  title,
  hint,
  children,
}: {
  title: string
  hint: string
  children?: React.ReactNode
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
      <h1 className="text-ink text-lg font-semibold">{title}</h1>
      <p className="text-muted mt-1 max-w-sm text-sm">{hint}</p>
      {children}
    </div>
  )
}
