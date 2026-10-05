// 画布视图状态（zustand store）：只管「怎么看画布」，不管「画布上有什么」。
// 缩放/平移属于纯视图变换——不进服务端、不写进 LayerDocument、不参与导出。
import { create } from 'zustand'

const MIN_SCALE = 0.05 // 最小倍率：缩小到看不清就没意义了
const MAX_SCALE = 8 // 最大倍率：放大过头只会看到马赛克
// 适应画布时留出四周余量，避免图片贴边
const FIT_RATIO = 0.92

// 每次滚轮/按钮缩放的步长（>1 为放大档）
export const ZOOM_STEP = 1.2

type Size = { width: number; height: number }
type Point = { x: number; y: number }

type CanvasViewState = {
  scale: number // 当前倍率，1 = 实际像素
  x: number // 画布原点的视口横坐标（平移量）
  y: number // 画布原点的视口纵坐标
  viewport: Size // 容器尺寸（CanvasStage 用 ResizeObserver 回写）
  setViewport: (viewport: Size) => void
  fit: (document: Size) => void // 适应画布：整张图居中且留边
  zoomBy: (factor: number, anchor?: Point) => void // 以某点为不动点缩放（滚轮缩放的关键）
  zoomTo: (scale: number) => void // 缩放到指定倍率（工具栏点百分比用）
  pan: (point: Point) => void // 拖拽平移
}

// 倍率夹在上下限之间
const clamp = (scale: number) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale))

/**
 * 观察倍率与位移，只影响编辑器视图，不参与导出。图层缩放另存于 LayerDocument。
 */
export const useCanvasView = create<CanvasViewState>((set, get) => ({
  scale: 1,
  x: 0,
  y: 0,
  viewport: { width: 0, height: 0 },

  setViewport: (viewport) => set({ viewport }),

  fit: (document) => {
    const { viewport } = get()
    // 容器还没量到尺寸（首次渲染前）时不动作
    if (!viewport.width || !viewport.height) return

    // 取「宽高各自能塞下的倍率」中较小的一个，再乘余量系数
    const scale = clamp(
      Math.min(viewport.width / document.width, viewport.height / document.height) * FIT_RATIO,
    )
    // 居中：位移 = (视口 - 文档×倍率) / 2
    set({
      scale,
      x: (viewport.width - document.width * scale) / 2,
      y: (viewport.height - document.height * scale) / 2,
    })
  },

  zoomBy: (factor, anchor) => {
    const { scale, x, y, viewport } = get()
    const next = clamp(scale * factor)
    // 未指定锚点时以视口中心为不动点
    const pivot = anchor ?? { x: viewport.width / 2, y: viewport.height / 2 }
    // 以锚点为不动点，滚轮位置下的画面内容不漂移：
    // 把「锚点到画布原点的向量」按倍率比缩短，保证锚点指向的画布点前后重合
    const ratio = next / scale
    set({
      scale: next,
      x: pivot.x - (pivot.x - x) * ratio,
      y: pivot.y - (pivot.y - y) * ratio,
    })
  },

  // 换算成相对缩放复用 zoomBy 的锚点逻辑
  zoomTo: (scale) => get().zoomBy(scale / get().scale),

  pan: (point) => set(point),
}))
