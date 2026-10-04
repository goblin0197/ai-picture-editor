// formatBytes：把字节数格式化为人类可读的 B / KB / MB 文案。
// 小于 1KB 用 B，小于 1MB 用整数 KB，其余用保留一位小数的 MB。
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

// formatDateTime：把 ISO 时间字符串格式化为「月-日 时:分」的中文本地时间。
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
