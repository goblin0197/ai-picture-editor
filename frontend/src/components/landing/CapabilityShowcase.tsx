import type { ReactNode } from 'react'

import { CandidatesPreview, ExportsPreview, LayersPreview, SelectionPreview } from './previews'

// 能力展示区的数据源：四项核心能力，每项含标题、说明文案，以及一张纯样式示意图（preview）。
// preview 直接放 JSX 节点（ReactNode），把「展示什么图」与「怎么排版卡片」解耦——
// 下面的渲染只管把 preview 塞进卡片框里，示意图各自的实现都在 previews.tsx。
const CAPABILITIES: { title: string; desc: string; preview: ReactNode }[] = [
  {
    title: '一句话生成',
    desc: '无需上传图片，描述需求即可拿到 4 个候选方向，挑中的那张直接进入编辑。',
    preview: <CandidatesPreview />,
  },
  {
    title: '主体级编辑',
    desc: '点选画面里的任意物体后再下指令，改动被约束在选区内，不会外溢到其他区域。',
    preview: <SelectionPreview />,
  },
  {
    title: '语义图层',
    desc: '主体、背景、文字自动分层，任意物体也可按需独立成层，随时回到上一版重做。',
    preview: <LayersPreview />,
  },
  {
    title: '物料包交付',
    desc: '卖点标注与 1:1、4:5、9:16 尺寸一次导出，主体不裁切，直接上架投放。',
    preview: <ExportsPreview />,
  },
]

// 落地页「能力」区块：一段区块标题 + 两列能力卡片网格。
// 无 props，数据全部来自上面的 CAPABILITIES 常量，组件只做遍历渲染。
export default function CapabilityShowcase() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-16">
      {/* 区块头部：小标签「能力」+ 主标题 + 一句总述，宽度收窄到 xl 保证阅读舒适 */}
      <header className="max-w-xl">
        <p className="text-brand-strong text-sm font-medium">能力</p>
        <h2 className="text-ink mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
          不只是生成一张好看的图
        </h2>
        <p className="text-muted mt-3 leading-relaxed">
          从候选方向到局部精修，再到分层与多尺寸交付，整条链路都在同一个工作台里完成。
        </p>
      </header>

      {/* 能力卡片网格：移动端单列、sm 起两列；遍历 CAPABILITIES 逐张渲染 */}
      <div className="mt-10 grid gap-5 sm:grid-cols-2">
        {CAPABILITIES.map((item) => (
          <article
            key={item.title}
            className="border-line bg-paper rounded-card hover:shadow-lift border p-6 transition-shadow"
          >
            {/* 示意图容器：固定高度 h-44 的画框，把对应的 preview 居中放入，overflow-hidden 裁掉溢出 */}
            <div className="bg-soft border-line/70 mb-6 flex h-44 items-center justify-center overflow-hidden rounded-[14px] border px-5 py-4">
              {item.preview}
            </div>
            {/* 卡片文案：能力标题 + 说明 */}
            <h3 className="text-ink font-medium">{item.title}</h3>
            <p className="text-muted mt-2 text-sm leading-relaxed">{item.desc}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
