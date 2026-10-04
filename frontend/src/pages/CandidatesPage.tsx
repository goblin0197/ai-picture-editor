import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import type { Asset } from '@/api/assets'
// useRun 合并 SSE 实时进度与快照接口，暴露状态/进度/候选图等。
import { useRun } from '@/hooks/useRun'

// 候选图结果页：展示生成进度，成功后列出候选图供用户选一张进入编辑。
// 刷新页面也能恢复——useRun 会用快照接口重新拉取当前状态。
export default function CandidatesPage() {
  // 从地址 /candidates/:runId 取任务 id；缺省给空串兜底。
  const { runId = '' } = useParams()
  const navigate = useNavigate()
  // picked：当前选中的候选图 id（未选为 null）。
  const [picked, setPicked] = useState<string | null>(null)
  // 订阅该任务：runId 为空串时传 null，useRun 内部据此不建立连接。
  const { status, progress, stage, error, candidates, notFound } = useRun(runId || null)

  // 分支一：任务不存在（快照接口 404），链接可能已失效。
  if (notFound) {
    return <Centered title="任务不存在" hint="链接可能已失效，回到创作页重新开始。" />
  }

  // 分支二：失败或被取消，展示原因并给「返回重试」入口。
  if (status === 'failed' || status === 'canceled') {
    return (
      <Centered title="生成失败" hint={error ?? '未知原因'}>
        <Link
          to="/create"
          className="bg-ink hover:bg-dark rounded-control mt-5 px-4 py-2 text-sm font-medium text-white"
        >
          返回重试
        </Link>
      </Centered>
    )
  }

  // 分支三：尚未成功（queued/running 或状态未知），显示进度条。
  if (status !== 'succeeded') {
    return <Progress percent={progress} stage={stage} />
  }

  // 分支四：成功，渲染候选图网格供挑选。
  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <header className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-ink text-2xl font-semibold tracking-tight">选出一张</h1>
          <p className="text-muted mt-1 text-sm">挑一张满意的进入编辑，其余候选图会保留在素材库。</p>
        </div>
        {/* 未选中时禁用；选定后带 asset 参数跳到编辑页（编辑功能待实现） */}
        <button
          type="button"
          disabled={!picked}
          onClick={() => navigate(`/editor?asset=${picked}`)}
          className="bg-ink hover:bg-dark rounded-control shrink-0 px-4 py-2 text-sm font-medium text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
        >
          进入编辑
        </button>
      </header>

      {/* 候选图网格：逐张渲染，selected 由 picked 决定 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {candidates.map((asset, index) => (
          <Candidate
            key={asset.id}
            asset={asset}
            index={index}
            selected={picked === asset.id}
            onSelect={() => setPicked(asset.id)}
          />
        ))}
      </div>
    </div>
  )
}

// 单张候选图子组件：可点击选择，选中态用边框与「已选」角标标识。
// props：asset 候选图；index 序号（用于左上角编号与 alt）；selected 是否选中；onSelect 选中回调。
function Candidate({
  asset,
  index,
  selected,
  onSelect,
}: {
  asset: Asset
  index: number
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      // 选中时用品牌色边框；未选中常态边框、悬停加深
      className={`rounded-panel group relative block overflow-hidden border-2 bg-white transition-colors ${
        selected ? 'border-brand' : 'border-line hover:border-line-strong'
      }`}
    >
      <img
        src={asset.url}
        alt={`候选图 ${index + 1}`}
        loading="lazy"
        className="block max-h-[52vh] w-full object-contain"
      />
      {/* 左上角序号 */}
      <span className="text-muted bg-paper/90 absolute top-2 left-2 rounded-full px-2 py-0.5 text-xs font-medium backdrop-blur">
        {index + 1}
      </span>
      {/* 右上角「已选」角标：仅选中时出现 */}
      {selected && (
        <span className="bg-brand absolute top-2 right-2 rounded-full px-2 py-0.5 text-xs font-medium text-white">
          已选
        </span>
      )}
    </button>
  )
}

// 进度子组件：把百分比画成进度条，stage 显示当前阶段文案。
function Progress({ percent, stage }: { percent: number; stage: string }) {
  return (
    <Centered title="正在生成" hint={stage || '任务已提交，正在排队'}>
      <div className="bg-line mt-6 h-1 w-64 overflow-hidden rounded-full">
        {/* 进度填充：至少给 4% 宽度，刚排队（0%）时也能看到一小段而非空条 */}
        <div
          className="bg-ink h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.max(percent, 4)}%` }}
        />
      </div>
      {/* tabular-nums 让数字等宽，百分比跳动时不会左右晃动 */}
      <p className="text-faint mt-2 text-xs tabular-nums">{percent}%</p>
    </Centered>
  )
}

// 居中布局子组件：本页多个状态（不存在/失败/进度）复用的「标题 + 提示 + 可选内容」容器。
function Centered({
  title,
  hint,
  children,
}: {
  title: string
  hint: string
  children?: React.ReactNode
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center px-8 text-center">
      <h1 className="text-ink text-xl font-semibold">{title}</h1>
      <p className="text-muted mt-1 max-w-md text-sm">{hint}</p>
      {children}
    </div>
  )
}
