import { useState } from 'react'

// RATIO_LABELS：比例枚举到中文标签的映射；GenerateInput 生成入参类型；Ratio 比例字面量类型。
import { RATIO_LABELS, type GenerateInput, type Ratio } from '@/api/runs'

// 可选比例：直接取映射表的键（顺序即声明顺序）。
const RATIOS = Object.keys(RATIO_LABELS) as Ratio[]
// 可选出图数量档位。
const COUNTS = [1, 2, 4, 6]

// 生成表单：收集提示词、比例、数量、排除项，组装成 GenerateInput 交给父组件提交。
// props：onSubmit 提交回调；pending 是否正在提交（用于禁用按钮）；defaultPrompt 预填提示词（来自草稿）。
export default function GenerateForm({
  onSubmit,
  pending,
  defaultPrompt = '',
}: {
  onSubmit: (input: GenerateInput) => void
  pending: boolean
  defaultPrompt?: string
}) {
  // 以下均为受控状态：输入框的值完全由 React state 掌控。
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [ratio, setRatio] = useState<Ratio>('1:1')
  const [count, setCount] = useState(4)
  const [negative, setNegative] = useState('')
  // advanced：是否展开「排除项」输入。
  const [advanced, setAdvanced] = useState(false)

  // 可提交条件：提示词去空白后非空，且当前没有在提交中。
  const canSubmit = prompt.trim().length > 0 && !pending

  return (
    <form
      onSubmit={(event) => {
        // 阻止浏览器默认的整页刷新式提交
        event.preventDefault()
        if (!canSubmit) return
        // 提交前对文本做 trim；negative 为空则传 undefined 而非空串
        onSubmit({
          prompt: prompt.trim(),
          ratio,
          count,
          negative_prompt: negative.trim() || undefined,
        })
      }}
      className="border-line bg-paper shadow-panel rounded-panel border p-2"
    >
      {/* 提示词输入：多行文本框 */}
      <textarea
        rows={3}
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          // 回车即提交；Shift+Enter 保留换行；isComposing 时不提交，避免中文输入法选词的回车被误当成提交
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault()
            // requestSubmit 会正常触发上面的 onSubmit（含校验），比直接调 submit() 更规范
            event.currentTarget.form?.requestSubmit()
          }
        }}
        placeholder="描述你想要的画面，例如：白色陶瓷马克杯放在浅木色桌面，晨光从左侧照入，背景干净"
        aria-label="画面描述"
        className="text-ink placeholder:text-faint w-full resize-none bg-transparent px-4 pt-3 pb-1 text-[15px] leading-relaxed outline-none"
      />

      {/* 参数行：比例、数量分段选择器 + 排除项开关 + 提交按钮 */}
      <div className="flex flex-wrap items-center gap-2 px-2 pb-1">
        {/* 比例选择：选项文字即比例本身，如 1:1 */}
        <Segmented
          label="比例"
          options={RATIOS.map((value) => ({ value, label: value }))}
          value={ratio}
          onChange={setRatio}
        />
        {/* 数量选择：数字需转成字符串给 label */}
        <Segmented
          label="数量"
          options={COUNTS.map((value) => ({ value, label: String(value) }))}
          value={count}
          onChange={setCount}
        />

        {/* 排除项开关：切换下方高级输入的显示 */}
        <button
          type="button"
          onClick={() => setAdvanced((open) => !open)}
          className="text-muted hover:text-ink rounded-control px-2 py-1.5 text-xs font-medium transition-colors"
        >
          {advanced ? '收起排除项' : '排除项'}
        </button>

        {/* 提交按钮：ml-auto 推到最右；不满足 canSubmit 时禁用 */}
        <button
          type="submit"
          disabled={!canSubmit}
          className="bg-ink hover:bg-dark rounded-control ml-auto px-4 py-2 text-sm font-medium text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
        >
          {pending ? '提交中…' : '生成'}
        </button>
      </div>

      {/* 排除项输入：仅在展开时渲染 */}
      {advanced && (
        <div className="border-line mt-1 border-t px-4 py-3">
          <input
            value={negative}
            onChange={(event) => setNegative(event.target.value)}
            placeholder="不希望出现的内容，例如：文字、水印、多余的手"
            aria-label="排除项"
            className="text-ink placeholder:text-faint w-full bg-transparent text-sm outline-none"
          />
        </div>
      )}
    </form>
  )
}

// 分段选择器子组件：一排互斥的小按钮，选中项高亮。
// 用泛型 T 兼容「字符串比例」与「数字数量」两种取值类型。
// props：label 左侧说明；options 选项数组；value 当前值；onChange 选中回调。
function Segmented<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="border-line rounded-control flex items-center gap-0.5 border p-0.5">
      <span className="text-faint px-1.5 text-xs">{label}</span>
      {options.map((option) => (
        // aria-pressed 表达选中态（无障碍）；选中项用深底白字区分
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          aria-pressed={option.value === value}
          className={`rounded-[6px] px-2 py-1 text-xs font-medium transition-colors ${
            option.value === value ? 'bg-ink text-white' : 'text-muted hover:text-ink'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
