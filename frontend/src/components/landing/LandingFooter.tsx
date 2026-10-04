import BrandMark from '@/components/BrandMark'

// 落地页页脚：一行展示品牌标识与一句话产品定位，无 props、无交互。
// 品牌标识同样复用 BrandMark 组件（三处：落地页、登录页、工作台共用，不手写 logo）。
export default function LandingFooter() {
  return (
    <footer className="border-line border-t">
      {/* 内容行：移动端纵向堆叠居中，sm 起横向两端对齐（品牌在左、定位语在右） */}
      <div className="text-faint mx-auto flex max-w-5xl flex-col items-center justify-between gap-3 px-6 py-8 text-xs sm:flex-row">
        <BrandMark size="sm">
          <span className="text-muted font-medium">AI 修图智能体</span>
        </BrandMark>
        <p>为电商运营与内容创作者打造的商品物料工作台</p>
      </div>
    </footer>
  )
}
