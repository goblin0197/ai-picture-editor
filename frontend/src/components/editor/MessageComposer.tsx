// 指令输入框：Enter 发送、Shift+Enter 换行；发送中禁用并显示「思考中…」。
import { useState } from 'react'

export default function MessageComposer({
  pending,
  onSend,
}: {
  pending: boolean
  onSend: (text: string) => void
}) {
  const [text, setText] = useState('')
  // 纯空白不发；规划请求进行中不允许连发
  const canSend = text.trim().length > 0 && !pending

  const submit = () => {
    if (!canSend) return
    onSend(text.trim())
    setText('') // 发出即清空——指令已在对话区可见
  }

  return (
    <div className="border-line shrink-0 border-t p-3">
      <textarea
        rows={2}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          // Enter 发送、Shift+Enter 换行；isComposing 排除中文输入法选词时的回车
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault()
            submit()
          }
        }}
        placeholder="说明要怎么改，回车发送"
        aria-label="修图指令"
        className="border-line text-ink placeholder:text-faint rounded-control focus:border-line-strong w-full resize-none border px-3 py-2 text-xs leading-relaxed outline-none transition-colors"
      />
      <button
        type="button"
        onClick={submit}
        disabled={!canSend}
        className="bg-ink hover:bg-dark rounded-control mt-2 w-full py-2 text-xs font-medium text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
      >
        {pending ? '思考中…' : '发送'}
      </button>
    </div>
  )
}
