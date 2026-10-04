/**
 * 能力卡片的示意图：全部用样式拼出产品界面，不依赖任何图片资源。
 * 均为装饰性内容，对辅助技术隐藏。
 */
// 为什么用纯 CSS/样式而不是贴图：
// 1) 这些图只是「产品长什么样」的示意，不是真实截图，用渐变/边框/定位块就能表意；
// 2) 无图片资源即无需管理二进制资产、无加载与体积成本，也不会有裂图，任何主题令牌改动它们自动跟随；
// 3) 矢量化的样式在任意分辨率都清晰。
// 因为不承载信息，每个 preview 的根节点都加 aria-hidden，整块对读屏软件隐藏（符合「装饰性示意图整容器 aria-hidden」约定）。

// 四个候选格子的背景色：四种浅色渐变，靠数组顺序与下面的 index 对应，营造出四个不同方向的错觉。
const TILES = [
  'bg-[linear-gradient(145deg,#dbe9ee,#f4f6f3)]',
  'bg-[linear-gradient(145deg,#e7f0d4,#f4f6f3)]',
  'bg-[linear-gradient(145deg,#f0e3d3,#f4f6f3)]',
  'bg-[linear-gradient(145deg,#e0e5dd,#f4f6f3)]',
]

/** 一句话生成：四个候选方向，其中一个被选中。 */
// 对应能力「一句话生成」：2×2 网格模拟四张候选图，index===1 的那张加品牌色描边与右上角对勾，表示已选中。
export function CandidatesPreview() {
  return (
    <div className="grid aspect-square h-full grid-cols-2 gap-2 p-1" aria-hidden>
      {TILES.map((tone, index) => (
        <div
          key={tone}
          // 选中项（index===1）用 ring-brand 双环高亮，其余用普通细边框，制造「选中一张」的对比
          className={`relative grid place-items-center rounded-[10px] ${tone} ${
            index === 1 ? 'ring-brand ring-2' : 'border-line border'
          }`}
        >
          {/* 格子中央的小色块：示意图里的「商品主体」占位 */}
          <span className="bg-ink/12 h-5 w-4 rounded-[3px]" />
          {index === 1 && (
            // 选中角标：右上角品牌色圆点内嵌一个白色对勾 SVG
            <span className="bg-brand absolute top-1 right-1 grid size-3.5 place-items-center rounded-full">
              <svg viewBox="0 0 24 24" fill="none" className="size-2">
                <path d="M5 13l4.5 4.5L19 7" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

/** 主体级编辑：选区框住主体，指令只作用于框内。 */
// 对应能力「主体级编辑」：一个 4:3 画面里，用虚线框 + 四角控制点圈出主体，底部气泡示意一句编辑指令。
export function SelectionPreview() {
  return (
    <div
      className="border-line relative aspect-[4/3] h-full max-h-full w-auto overflow-hidden rounded-[13px] border bg-[linear-gradient(160deg,#e4eef1,#f4f6f3)]"
      aria-hidden
    >
      {/* 选区框：品牌色虚线边框，用百分比定位/尺寸摆在画面偏左上，模拟框住某个主体 */}
      <div className="border-brand absolute top-[18%] left-[22%] h-[54%] w-[38%] rounded-[6px] border-2 border-dashed">
        {/* 框内的实心色块：被框住的「主体」占位 */}
        <span className="bg-ink/12 absolute inset-1.5 rounded-[4px]" />
        {/* 四角控制点：遍历四个角的定位类名，各画一个白底品牌色描边的小圆点，模拟可拖拽手柄 */}
        {['-top-1 -left-1', '-top-1 -right-1', '-bottom-1 -left-1', '-bottom-1 -right-1'].map((pos) => (
          <span key={pos} className={`bg-paper border-brand absolute size-2 rounded-full border-2 ${pos}`} />
        ))}
      </div>
      {/* 左下角指令气泡：示意「对选区下达的自然语言指令」 */}
      <p className="bg-ink/90 absolute bottom-2.5 left-2.5 rounded-full px-2.5 py-1 text-[10px] text-white">
        把背景换成米色亚麻
      </p>
    </div>
  )
}

// 语义图层示意的数据源：三个图层（文字/主体/背景），各带色块色调 tone 与递增缩进 indent，
// 用缩进营造图层树的层级错落感。
const LAYERS = [
  { name: '文字 · 卖点标注', tone: 'bg-accent/70', indent: 'ml-0' },
  { name: '主体 · 商品', tone: 'bg-brand/60', indent: 'ml-3' },
  { name: '背景 · 场景', tone: 'bg-line-strong', indent: 'ml-6' },
]

/** 语义图层：主体、背景、文字自动分层。 */
// 对应能力「语义图层」：三张带缩进的图层条，每条含色块、图层名与一个「可见」眼睛图标。
export function LayersPreview() {
  return (
    <div className="w-full max-w-[210px] space-y-1.5" aria-hidden>
      {LAYERS.map((layer) => (
        <div
          key={layer.name}
          // 图层条：卡片式外观，末尾拼接该图层的 indent 缩进类，制造层级错落
          className={`border-line bg-paper shadow-control flex items-center gap-2.5 rounded-[10px] border px-2.5 py-2 ${layer.indent}`}
        >
          {/* 左侧色块：用 tone 区分图层类型（文字/主体/背景） */}
          <span className={`size-4 shrink-0 rounded-[4px] ${layer.tone}`} />
          {/* 图层名，truncate 防止过长撑破条目 */}
          <span className="text-muted flex-1 truncate text-[11px]">{layer.name}</span>
          {/* 右侧「可见」眼睛图标：示意该图层的显隐开关 */}
          <svg viewBox="0 0 24 24" fill="none" className="text-faint size-3.5">
            <path d="M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6z" stroke="currentColor" strokeWidth="1.8" />
            <circle cx="12" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.8" />
          </svg>
        </div>
      ))}
    </div>
  )
}

// 多尺寸导出示意的数据源：三种投放比例，各带展示 label 与对应长宽的画框类 frame，
// 直接用不同宽高的方框把「同一套物料的不同尺寸」画出来。
const RATIOS = [
  { label: '1:1', frame: 'h-[62px] w-[62px]' },
  { label: '4:5', frame: 'h-[70px] w-[56px]' },
  { label: '9:16', frame: 'h-[78px] w-[44px]' },
]

/** 物料包交付：一次导出多个投放尺寸。 */
// 对应能力「物料包交付」：三个底部对齐（items-end）的画框，宽高各异对应 1:1 / 4:5 / 9:16 三种尺寸。
export function ExportsPreview() {
  return (
    <div className="flex items-end gap-3" aria-hidden>
      {RATIOS.map((ratio) => (
        <div key={ratio.label} className="flex flex-col items-center gap-1.5">
          {/* 尺寸画框：宽高由 ratio.frame 决定，框内小色块示意居中的主体 */}
          <div
            className={`border-line grid place-items-center rounded-[9px] border bg-[linear-gradient(150deg,#e4eef1,#f4f6f3)] ${ratio.frame}`}
          >
            <span className="bg-ink/15 h-2/5 w-1/3 rounded-[3px]" />
          </div>
          {/* 画框下方的比例标注文字 */}
          <span className="text-faint text-[10px]">{ratio.label}</span>
        </div>
      ))}
    </div>
  )
}
