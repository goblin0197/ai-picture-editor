// 占位页：尚未实现的功能（如 /editor、/batch、/marketing）先用它顶着，保证路由可访问。
// props：title 页面标题；hint 说明文案（通常是「功能开发中」）。
export default function PlaceholderPage({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
      <h1 className="text-ink text-xl font-semibold">{title}</h1>
      <p className="text-muted text-sm">{hint}</p>
    </div>
  )
}
