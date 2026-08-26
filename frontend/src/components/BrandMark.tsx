// ReactNode 仅用于类型标注；verbatimModuleSyntax 开启时类型导入必须写 import type。
import type { ReactNode } from 'react'

// 两档尺寸对应的图标外框（尺寸 + 圆角）。用 as const 固定成字面量类型，
// 好让下面的 size 参数能被约束为 'sm' | 'md'。
const GLYPH_SIZE = {
  sm: 'size-6 rounded-[7px]',
  md: 'size-8 rounded-[10px]',
} as const

/** 品牌标识：ink 底 + accent 图层符号，落地页、登录页与工作台共用一处。 */
// props：size 选图标大小档位；className 供外部追加布局样式；children 放 logo 右侧文字（可选）。
export default function BrandMark({
  size = 'md',
  className = '',
  children,
}: {
  size?: keyof typeof GLYPH_SIZE
  className?: string
  children?: ReactNode
}) {
  return (
    // 外层 inline-flex 让「图标 + 文字」水平对齐；className 拼在后面便于外部微调间距/内边距
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      {/* 图标方块：ink 底色 + accent 前景色，纯装饰所以 aria-hidden */}
      <span
        className={`bg-ink text-accent grid shrink-0 place-items-center ${GLYPH_SIZE[size]}`}
        aria-hidden
      >
        {/* 图形：一个方框叠一条折角描边，构成「图层」意象；stroke 用 currentColor 继承上层的 text-accent */}
        <svg viewBox="0 0 24 24" fill="none" className="size-[62%]">
          <rect x="3.5" y="3.5" width="12" height="12" rx="3.5" stroke="currentColor" strokeWidth="2" />
          <path
            d="M8.5 20.5H17a3.5 3.5 0 0 0 3.5-3.5V8.5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="15.5" cy="3.5" r="1.55" fill="currentColor" />
        </svg>
      </span>
      {/* 可选文字：由调用方通过 children 传入（如「AI 修图智能体」） */}
      {children}
    </span>
  )
}
