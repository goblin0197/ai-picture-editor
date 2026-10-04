// Asset 类型：素材的元信息（含可直接放进 <img> 的签名 URL）。
import type { Asset } from '@/api/assets'
// 展示用格式化工具：把字节数、时间戳转成人类可读文本。
import { formatBytes, formatDateTime } from '@/lib/format'

// 素材卡片：在网格里展示单张素材的缩略图与元信息。
// props：asset 要展示的素材；onSelect 可选，点击整卡时回调（用于「选图」等场景）。
export default function AssetCard({ asset, onSelect }: { asset: Asset; onSelect?: () => void }) {
  return (
    // 整卡是一个 button，方便键盘聚焦与点击选择；group 供内部图片做悬停放大
    <button
      type="button"
      onClick={onSelect}
      className="border-line bg-paper hover:border-brand group overflow-hidden rounded-[18px] border text-left transition-colors"
    >
      {/* 缩略图区：正方形容器，object-contain 保证整图完整显示、不裁剪 */}
      <div className="bg-canvas relative aspect-square">
        <img
          src={asset.url}
          alt=""
          loading="lazy"
          className="size-full object-contain transition-transform group-hover:scale-[1.02]"
        />
        {/* 「透明底」角标：仅当素材含 alpha 通道时显示（如已抠好的主体图） */}
        {asset.has_alpha && (
          <span className="bg-ink/80 absolute top-2 left-2 rounded px-1.5 py-0.5 text-[10px] text-white">
            透明底
          </span>
        )}
      </div>

      {/* 元信息区：尺寸、格式 + 体积、创建时间 */}
      <dl className="text-muted space-y-0.5 px-3 py-2.5 text-xs">
        <div className="text-ink font-medium">
          {asset.width} × {asset.height}
        </div>
        <div>
          {asset.image_format} · {formatBytes(asset.size_bytes)}
        </div>
        <div className="text-faint">{formatDateTime(asset.created_at)}</div>
      </dl>
    </button>
  )
}
