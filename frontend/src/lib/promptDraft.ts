// 草稿在 sessionStorage 中的键名（带项目前缀，避免与其他键冲突）。
const KEY = 'retouch:prompt-draft'

/**
 * 落地页写入并回填的需求草稿，只活在当前标签页。
 */
export function savePromptDraft(text: string): void {
  // 去除首尾空白后判断：空串视为清空草稿。
  const value = text.trim()
  try {
    // 有内容则写入，无内容则删除键，避免留下空草稿。
    if (value) sessionStorage.setItem(KEY, value)
    else sessionStorage.removeItem(KEY)
  } catch {
    // 隐私模式下 sessionStorage 不可写，草稿丢失不影响主流程
  }
}

// readPromptDraft：读取草稿；无草稿或存储不可读时返回空串。
export function readPromptDraft(): string {
  try {
    // 隐私模式下读取也可能抛异常，故同样用 try/catch 包裹。
    return sessionStorage.getItem(KEY) ?? ''
  } catch {
    // 读取失败时静默返回空串，让调用方无需感知存储是否可用。
    return ''
  }
}
