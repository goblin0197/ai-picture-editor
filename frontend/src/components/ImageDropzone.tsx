import { useRef, useState } from 'react'

// ACCEPTED_TYPES：允许的图片 MIME 列表（同时给 <input accept> 与本地校验用）。
import { ACCEPTED_TYPES } from '@/api/assets'
// checkFile：上传前的本地校验（类型/体积），返回错误文案或 null。
import { checkFile } from '@/hooks/useAssets'

// props：onFile 校验通过后回调所选文件；disabled 上传中禁用；hint 自定义副提示文案。
type Props = {
  onFile: (file: File) => void
  disabled?: boolean
  hint?: string
}

// 图片拖放上传区：支持「点击选择」与「拖拽放入」两种方式，并在交给上层前先本地校验。
export default function ImageDropzone({ onFile, disabled, hint }: Props) {
  // 隐藏 <input type=file> 的引用：点击可视区域时借它弹出系统文件选择框。
  const inputRef = useRef<HTMLInputElement>(null)
  // dragging：是否有文件正拖在区域上方（用于高亮边框）。
  const [dragging, setDragging] = useState(false)
  // error：本地校验失败的提示（格式/体积不符）。
  const [error, setError] = useState<string | null>(null)

  // 统一收文件入口：先本地校验，通过才向上抛给 onFile；不通过则把错误显示出来。
  const accept = (file: File | undefined) => {
    if (!file) return
    const problem = checkFile(file)
    setError(problem)
    if (!problem) onFile(file)
  }

  return (
    <div>
      {/* 可视拖放区做成 button：既能点击（触发下面隐藏的 input），也能承接拖拽事件 */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        // dragOver 必须 preventDefault，否则浏览器默认会把图片当成导航打开，drop 也就收不到
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          // 只取第一个文件（本组件按单张处理）
          accept(event.dataTransfer.files[0])
        }}
        // 拖拽悬停时高亮，否则用常态样式；disabled 时整体降透明度
        className={`flex w-full flex-col items-center gap-1.5 rounded-[18px] border border-dashed px-6 py-10 transition-colors disabled:opacity-50 ${
          dragging ? 'border-brand bg-brand-soft' : 'border-line-strong bg-paper hover:border-brand'
        }`}
      >
        {/* 主文案：上传中显示「上传中…」，否则提示可拖可点 */}
        <span className="text-ink text-sm font-medium">
          {disabled ? '上传中…' : '拖入图片，或点击选择'}
        </span>
        {/* 副文案：默认列出格式与大小限制，可由 hint 覆盖 */}
        <span className="text-faint text-xs">{hint ?? 'JPG / PNG / WebP，单张不超过 20 MB'}</span>
      </button>

      {/* 真正的文件输入框：隐藏起来，只通过上面的按钮触发 */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        hidden
        onChange={(event) => {
          accept(event.target.files?.[0])
          // 清空 value：否则连续选同一个文件不会再次触发 onChange
          event.target.value = ''
        }}
      />

      {/* 本地校验错误提示（网络上传错误由父组件展示） */}
      {error && <p className="text-danger mt-2 text-sm">{error}</p>}
    </div>
  )
}
