// 落地页首屏「英雄区」（Hero）：整页最先看到的区块。
// 由徽标、主标题、副标题、需求输入框（PromptComposer）、场景快捷标签、事实清单组成。
// 它自己持有需求输入的 state，符合「交互下沉到分区组件」的约定；提交与跳转由父级 LandingPage 注入。
import { useRef, useState } from 'react'

import PromptComposer from './PromptComposer'

// 场景快捷标签的数据源：每项含展示用的 label 与点击后回填到输入框的整段示例 prompt。
// 抽成常量而非写死在 JSX 里，既便于增删场景，也让下面的渲染只负责 map。
const SCENARIOS = [
  {
    label: '商品主图',
    prompt: '把这件商品放在纯白背景上，居中构图，柔和顶光，边缘干净，输出 1:1 主图。',
  },
  {
    label: '场景氛围图',
    prompt: '把商品放到温暖的木质桌面场景，侧逆光、浅景深，保留商品原有材质与颜色。',
  },
  {
    label: '模特上身',
    prompt: '生成模特手持该商品的半身展示图，简洁室内背景、自然光，商品细节清晰可辨。',
  },
  {
    label: '促销海报',
    prompt: '做一张大促海报：主标题「新品首发」，副标题「限时 8 折」，突出商品，右侧留出文字区。',
  },
  {
    label: '多尺寸物料',
    prompt: '基于这张商品图输出一套投放物料，包含 1:1、4:5、9:16 三个尺寸，主体不被裁切。',
  },
]

// 输入框下方的「事实清单」文案：降低尝试门槛的三条卖点，纯展示、无交互。
const FACTS = ['无需设计经验', '支持 JPG / PNG / WebP', '1:1 / 4:5 / 9:16 一次导出']

// props：
// - initialPrompt：初始需求文案，来自 LandingPage 的草稿回填（readPromptDraft）。
// - submitLabel：提交按钮文案（「免费开始」或「进入工作台」，随登录态而定）。
// - onStart：提交回调，父级在其中「存草稿 + 跳转」，本组件不关心跳去哪。
export default function LandingHero({
  initialPrompt,
  submitLabel,
  onStart,
}: {
  initialPrompt: string
  submitLabel: string
  onStart: (prompt: string) => void
}) {
  // 受控输入状态：输入框内容由这里的 prompt 唯一持有，PromptComposer 只负责显示与回传变更。
  // 用 initialPrompt 作初值，实现草稿回填。
  const [prompt, setPrompt] = useState(initialPrompt)
  // 指向底层 <textarea> 的 ref：点击场景标签回填后，用它把光标重新聚焦回输入框。
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 场景标签点击回填：把该场景的示例 prompt 写入受控状态，并立刻聚焦输入框，
  // 让用户可以直接在示例基础上继续修改，而不用先手动点一下输入框。
  const pick = (text: string) => {
    setPrompt(text)
    inputRef.current?.focus()
  }

  return (
    // relative + isolate + overflow-hidden：为下面两层绝对定位的装饰层建立定位上下文与独立层叠上下文，
    // 并裁掉溢出容器的光晕/网格，避免它们盖到相邻区块。
    <section className="relative isolate overflow-hidden">
      {/* 两层纯装饰背景：顶部光晕（bg-glow）与网格底纹（bg-grid），均为 index.css 里的 @utility。 */}
      {/* 它们只提供视觉氛围、不承载信息，故加 aria-hidden 让读屏软件跳过，避免朗读无意义节点。 */}
      <div className="bg-glow absolute inset-x-0 -top-24 h-[560px]" aria-hidden />
      <div className="bg-grid absolute inset-x-0 -top-24 h-[560px]" aria-hidden />

      {/* 容器给到 4xl，让 14 字标题在桌面端稳定单行；正文与输入框各自再收窄 */}
      <div className="relative mx-auto max-w-4xl px-6 pt-16 pb-14 text-center sm:pt-24">
        {/* 顶部小徽标（面向人群）。animate-rise 是统一的入场动画（自下浮入 + 淡入）， */}
        {/* 配合 style 里递增的 animationDelay 做「错峰入场」：徽标、标题、正文、输入框、标签、清单 */}
        {/* 依次 40→120→200→280→360→440ms 亮相，形成自上而下的节奏。降级由 index.css 的 prefers-reduced-motion 全局处理。 */}
        <p
          className="border-line bg-paper/80 text-muted animate-rise inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs backdrop-blur"
          style={{ animationDelay: '40ms' }}
        >
          {/* 前面的小圆点是装饰，标注 aria-hidden */}
          <span className="bg-accent size-1.5 rounded-full" aria-hidden />
          面向电商运营与内容创作者
        </p>

        {/* 主标题：字号随断点放大（2rem → 2.7rem → 3.25rem），text-balance 让折行更均衡 */}
        <h1
          className="text-ink animate-rise mt-6 text-[2rem] leading-[1.2] font-semibold tracking-tight text-balance sm:text-[2.7rem] lg:text-[3.25rem]"
          style={{ animationDelay: '120ms' }}
        >
          一句话，交付
          {/* 给「可上架」三个字加马克笔式高亮：外层 relative + whitespace-nowrap 防止高亮词被折行拆开 */}
          <span className="relative mx-1 whitespace-nowrap">
            {/* CJK 字身占满字框，高亮块需覆盖整个字高才像马克笔而非删除线 */}
            {/* 该 span 是绝对定位的色块：inset-x 负值向左右各外扩 7px，top/bottom 收进一点让色块贴合字身， */}
            {/* -skew-x-6 轻微斜切模拟手绘笔触，纯装饰故 aria-hidden。 */}
            <span
              className="bg-accent/55 absolute inset-x-[-7px] top-[14%] bottom-[8%] -skew-x-6 rounded-[3px]"
              aria-hidden
            />
            {/* 文字用 relative 叠在色块之上，否则会被绝对定位的高亮块盖住 */}
            <span className="relative">可上架</span>
          </span>
          的商品物料
        </h1>

        {/* 副标题：概述智能体能自动编排的整条能力链路 */}
        <p
          className="text-muted animate-rise mx-auto mt-5 max-w-xl leading-relaxed"
          style={{ animationDelay: '200ms' }}
        >
          描述需求即可从零生成，也可上传商品图继续编辑。抠图、换背景、局部精修、扩图、图层拆分与多尺寸导出，全部由智能体自动编排。
        </p>

        {/* 需求输入面板：把受控状态 prompt 与其 setter 交给 PromptComposer。 */}
        {/* onSubmit（回车/点按钮）与 onAttach（上传商品图）都走同一个 onStart：先存草稿再跳转。 */}
        {/* inputRef 下传，供场景标签回填后聚焦使用。 */}
        <div className="animate-rise mx-auto mt-9 max-w-3xl" style={{ animationDelay: '280ms' }}>
          <PromptComposer
            value={prompt}
            onChange={setPrompt}
            onSubmit={() => onStart(prompt)}
            onAttach={() => onStart(prompt)}
            submitLabel={submitLabel}
            placeholder="描述你想要的商品图，例：把这双跑鞋放到清晨的城市街道，侧逆光，输出 1:1 主图与 9:16 竖版…"
            inputRef={inputRef}
          />
        </div>

        {/* 场景快捷标签行：遍历 SCENARIOS 渲染成一排药丸按钮，点击调用 pick 回填示例并聚焦输入框 */}
        <div
          className="animate-rise mt-5 flex flex-wrap justify-center gap-2"
          style={{ animationDelay: '360ms' }}
        >
          {SCENARIOS.map((scenario) => (
            <button
              key={scenario.label}
              type="button"
              onClick={() => pick(scenario.prompt)}
              className="border-line bg-paper/70 text-muted hover:border-brand hover:text-brand-strong rounded-full border px-3.5 py-1.5 text-xs transition-colors"
            >
              {scenario.label}
            </button>
          ))}
        </div>

        {/* 事实清单：遍历 FACTS 渲染三条卖点，每条前置一个装饰小圆点（aria-hidden） */}
        <ul
          className="text-faint animate-rise mt-10 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs"
          style={{ animationDelay: '440ms' }}
        >
          {FACTS.map((fact) => (
            <li key={fact} className="flex items-center gap-1.5">
              <span className="bg-line-strong size-1 rounded-full" aria-hidden />
              {fact}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
