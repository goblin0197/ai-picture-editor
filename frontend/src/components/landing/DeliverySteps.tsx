// 交付流程四步的数据源：从「描述需求」到「导出物料」的顺序说明，抽成常量便于遍历。
const STEPS = [
  { title: '描述需求', desc: '一句话说清商品、场景与尺寸。' },
  { title: '挑选方向', desc: '从 4 个候选里选中最合适的一张。' },
  { title: '局部精修', desc: '点选主体下指令，反复改到满意。' },
  { title: '导出物料', desc: '按投放渠道一次导出全部尺寸。' },
]

// 落地页「交付流程」区块：把使用流程拆成四步横向排列。
// 无 props，数据来自上面的 STEPS，组件只做遍历渲染。
export default function DeliverySteps() {
  return (
    <section className="mx-auto max-w-5xl px-6 pb-16">
      {/* 用有序列表 <ol> 承载步骤（语义上就是有先后的流程）。 */}
      {/* 移动端单列、用横向分隔线（divide-y）区隔；sm 起变四列并改用竖向分隔线（divide-x、divide-y-0）。 */}
      <ol className="border-line bg-paper rounded-card divide-line grid divide-y border sm:grid-cols-4 sm:divide-x sm:divide-y-0">
        {STEPS.map((step, index) => (
          <li key={step.title} className="p-6">
            {/* 步骤序号徽标：用数组下标 +1 得到 1~4 的圆形编号 */}
            <span className="bg-brand-soft text-brand-strong grid size-7 place-items-center rounded-full text-xs font-semibold">
              {index + 1}
            </span>
            {/* 步骤标题与说明 */}
            <h3 className="text-ink mt-4 text-sm font-medium">{step.title}</h3>
            <p className="text-muted mt-1.5 text-sm leading-relaxed">{step.desc}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
