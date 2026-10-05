// 右侧信息面板：图层列表、画布属性、编辑历史三个区块。
import type { Asset } from '@/api/assets'
import { ACTION_LABELS, type Layer, type SessionDetail } from '@/api/sessions'
import { useSessionHistory } from '@/hooks/useSessions'
import { formatBytes, formatDateTime } from '@/lib/format'

export default function LayerPanel({ session }: { session: SessionDetail }) {
  // 当前画布显示的素材（属性区展示它的格式/大小/透明通道）
  const current = session.assets.find((asset) => asset.id === session.current_asset_id)
  // 编辑历史（最新在前）
  const { data: history = [] } = useSessionHistory(session.id)

  return (
    <aside className="border-line bg-paper w-72 shrink-0 overflow-y-auto border-l">
      <Section title="图层">
        <ul className="space-y-1">
          {session.document.layers.map((layer) => (
            <LayerRow key={layer.id} layer={layer} />
          ))}
        </ul>
      </Section>

      <Section title="属性">
        <Properties document={session.document} current={current} revision={session.revision} />
      </Section>

      <Section title="编辑记录">
        {history.length === 0 ? (
          <p className="text-faint text-xs">暂无记录</p>
        ) : (
          <ol className="space-y-1.5">
            {history.map((entry) => (
              <li key={entry.seq} className="flex items-baseline justify-between gap-2 text-xs">
                {/* 未知动作名直接原样展示，保证向前兼容 */}
                <span className="text-ink">{ACTION_LABELS[entry.action] ?? entry.action}</span>
                <span className="text-faint shrink-0 tabular-nums">
                  {formatDateTime(entry.created_at)}
                </span>
              </li>
            ))}
          </ol>
        )}
      </Section>
    </aside>
  )
}

// 单行图层：名称 + 尺寸 + 锁定标记（锁定态对应底图）
function LayerRow({ layer }: { layer: Layer }) {
  return (
    <li className="border-line rounded-control flex items-center gap-2 border px-2.5 py-2">
      <span className="text-ink min-w-0 flex-1 truncate text-xs font-medium">{layer.name}</span>
      <span className="text-faint shrink-0 text-[10px] tabular-nums">
        {layer.width} × {layer.height}
      </span>
      {layer.locked && <span className="text-faint shrink-0 text-[10px]">已锁定</span>}
    </li>
  )
}

// 属性区：画布尺寸、修订号，以及当前素材的格式/大小/透明通道
function Properties({
  document,
  current,
  revision,
}: {
  document: { width: number; height: number }
  current: Asset | undefined
  revision: number
}) {
  // 用 [label, value] 数组统一渲染成 dl
  const rows: [string, string][] = [
    ['画布', `${document.width} × ${document.height}`],
    ['修订号', String(revision)],
  ]
  if (current) {
    rows.push(['格式', current.image_format])
    rows.push(['大小', formatBytes(current.size_bytes)])
    rows.push(['透明通道', current.has_alpha ? '有' : '无'])
  }

  return (
    <dl className="space-y-1.5 text-xs">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-2">
          <dt className="text-muted">{label}</dt>
          <dd className="text-ink tabular-nums">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

// 通用区块壳：标题 + 内容，区块间用分隔线
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-line border-b px-4 py-4 last:border-b-0">
      <h2 className="text-muted mb-2.5 text-xs font-medium">{title}</h2>
      {children}
    </section>
  )
}
