import { Link } from 'react-router-dom'

// 落地页底部的行动号召横幅（CTA）：深色卡片再放一个入口按钮，作最后的转化引导。
// props 由 LandingPage 下发：label 是按钮文案、to 是跳转目标（二者同样来自登录态决定的 entry）。
// 这里用声明式 <Link> 跳转（无需先存草稿，故不复用 Hero 的 onStart 回调）。
export default function StartBanner({ label, to }: { label: string; to: string }) {
  return (
    <section className="mx-auto max-w-5xl px-6 pb-20">
      {/* 深墨底色卡片：relative + isolate + overflow-hidden 为内部光晕装饰层建立层叠上下文并裁边 */}
      <div className="bg-ink rounded-panel relative isolate overflow-hidden px-8 py-14 text-center">
        {/* 顶部径向渐变光晕：纯装饰，用品牌强调色在卡片上方晕开一层微光，故 aria-hidden */}
        <div
          className="absolute inset-0 bg-[radial-gradient(52%_60%_at_50%_-10%,rgb(217_255_110/0.22),transparent_70%)]"
          aria-hidden
        />

        {/* 文案与按钮层：relative 叠在上面的绝对定位光晕之上，否则会被光晕层盖住 */}
        <div className="relative">
          <h2 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            把商品图交给智能体
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-white/65">
            登录即可开始，第一句需求就能拿到可上架的候选图。
          </p>

          {/* 主按钮：强调色底色，跳转到 to，文案用 label */}
          <Link
            to={to}
            className="bg-accent text-ink rounded-control mt-8 inline-flex px-6 py-3 text-sm font-medium transition-opacity hover:opacity-90"
          >
            {label}
          </Link>
        </div>
      </div>
    </section>
  )
}
