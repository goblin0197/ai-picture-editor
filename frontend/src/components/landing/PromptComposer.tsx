import type { RefObject } from 'react'

// 「上传商品图」按钮里的图标：内联 SVG（一张带山峰的图片框），无外部资源依赖。
// 纯装饰，故 aria-hidden；尺寸由 size-4 控制，颜色用 currentColor 跟随按钮文字色。
function AttachIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="size-4" aria-hidden>
      <rect x="3" y="4.5" width="18" height="15" rx="3" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3.5 16l4.6-4a2 2 0 0 1 2.6 0l5.3 4.6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="15.5" cy="9.5" r="1.6" fill="currentColor" />
    </svg>
  )
}

// 提交按钮里的箭头图标：同为内联 SVG，装饰性 aria-hidden，颜色继承按钮文字色。
function SubmitIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="size-4" aria-hidden>
      <path d="M5 12h13M13 6.5l5.5 5.5L13 17.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/**
 * 需求输入面板：受控组件，只负责采集与提交，不关心提交后去哪。
 * Enter 提交、Shift + Enter 换行，与主流对话式产品保持一致。
 */
// props：
// - value / onChange：受控值与变更回调，真正的状态由父级（LandingHero）持有。
// - onSubmit：回车或点提交按钮时触发；onAttach：点「上传商品图」时触发。二者在父级都指向同一入口。
// - submitLabel / placeholder：按钮文案与输入占位符，随登录态与场景而变。
// - inputRef：可选，父级用来在回填场景示例后聚焦 textarea。
export default function PromptComposer({
  value,
  onChange,
  onSubmit,
  onAttach,
  submitLabel,
  placeholder,
  inputRef,
}: {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onAttach: () => void
  submitLabel: string
  placeholder: string
  inputRef?: RefObject<HTMLTextAreaElement | null>
}) {
  return (
    // 用 <form> 包裹，让「回车提交」与「点击提交按钮」走同一条 onSubmit 路径。
    // preventDefault 阻止表单默认的整页刷新式提交，改由 onSubmit 回调接管。
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
      className="border-line bg-paper shadow-panel rounded-panel focus-within:border-brand relative border p-2 text-left transition-colors"
    >
      {/* 多行需求输入框：受控（value + onChange），resize-none 禁止用户手动拉伸以保持版式 */}
      <textarea
        ref={inputRef}
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          // 回车提交、Shift+Enter 换行的分流逻辑。
          // 关键在 !event.nativeEvent.isComposing：中文/日文等输入法在候选词阶段，
          // 用户按 Enter 是「确认候选词」，此时 isComposing 为 true。若不排除这种情况，
          // 就会在用户刚敲定拼音时误触发提交，把半句话直接发出去。排除后只有真正的回车才提交。
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault()
            onSubmit()
          }
        }}
        placeholder={placeholder}
        aria-label="描述你想要的商品物料"
        className="text-ink placeholder:text-faint w-full resize-none bg-transparent px-4 pt-3 pb-1 text-[15px] leading-relaxed outline-none"
      />

      {/* 输入框下方的操作条：左「上传商品图」，右「提示 + 提交按钮」 */}
      <div className="flex items-center justify-between gap-3 px-2 pb-1">
        {/* 上传入口：type="button" 避免被当成表单提交；点击走 onAttach */}
        <button
          type="button"
          onClick={onAttach}
          className="text-muted hover:border-line-strong hover:text-ink border-line rounded-control flex items-center gap-1.5 border px-2.5 py-1.5 text-xs font-medium transition-colors"
        >
          <AttachIcon />
          上传商品图
        </button>

        <div className="flex items-center gap-3">
          {/* 快捷键提示，仅在 sm 及以上宽度显示（移动端隐藏，因无物理键盘） */}
          <span className="text-faint hidden text-xs sm:block">Enter 发送 · Shift + Enter 换行</span>
          {/* 提交按钮：type="submit" 触发上面的 <form onSubmit>，与回车提交共用一条路径 */}
          <button
            type="submit"
            className="bg-ink hover:bg-dark rounded-control flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white transition-colors"
          >
            {submitLabel}
            <SubmitIcon />
          </button>
        </div>
      </div>
    </form>
  )
}
