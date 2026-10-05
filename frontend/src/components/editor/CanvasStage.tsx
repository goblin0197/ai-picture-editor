// Konva 画布舞台：按 LayerDocument 渲染画布与可见的位图图层。
// 只做「看」——平移/缩放/适应；图层编辑（S 后续步骤）才需要监听事件。
import { useEffect, useRef } from 'react'
import { Image as KonvaImage, Layer as KonvaLayer, Rect, Stage } from 'react-konva'

import type { Layer, LayerDocument } from '@/api/sessions'
import { useCanvasImage } from '@/hooks/useCanvasImage'
import { useElementSize } from '@/hooks/useElementSize'
import { ZOOM_STEP, useCanvasView } from '@/stores/canvasView'

export default function CanvasStage({
  document,
  urls,
}: {
  document: LayerDocument
  urls: Map<string, string> // asset_id → 签名 URL，由 EditorPage 从图片墙素材表构建
}) {
  // 容器尺寸（Stage 必须显式宽高）
  const [containerRef, size] = useElementSize<HTMLDivElement>()
  // 视图变换来自 zustand store（工具栏的缩放按钮与这里共享同一份状态）
  const { scale, x, y, setViewport, fit, zoomBy, pan } = useCanvasView()
  // 记录上次适应时的「视口×画幅」形状，用于判断是否需要重新适应
  const fitted = useRef('')

  // 容器尺寸变化回写给 store，供 fit/zoomBy 计算使用
  useEffect(() => setViewport(size), [size, setViewport])

  useEffect(() => {
    const shape = `${size.width}x${size.height}:${document.width}x${document.height}`
    // 只在画幅或视口真正变化时重新适应，否则会覆盖用户手动调整的倍率
    if (!size.width || !size.height || fitted.current === shape) return
    fitted.current = shape
    fit(document)
  }, [size, document, fit])

  // 只渲染可见的位图图层；text/shape 图层后续步骤才支持
  const images = document.layers.filter((layer) => layer.visible && layer.kind === 'image')

  return (
    <div ref={containerRef} className="bg-canvas relative h-full w-full overflow-hidden">
      <Stage
        width={size.width}
        height={size.height}
        x={x} // 视图平移（来自 store）
        y={y}
        scaleX={scale} // 视图缩放（来自 store）
        scaleY={scale}
        draggable // 整个舞台可拖拽平移
        onDragMove={(event) => pan({ x: event.target.x(), y: event.target.y() })}
        onWheel={(event) => {
          event.evt.preventDefault() // 阻止页面随滚轮滚动
          // 以鼠标当前位置为锚点缩放：滚轮指向的内容不漂移
          const pointer = event.target.getStage()?.getPointerPosition()
          zoomBy(event.evt.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, pointer ?? undefined)
        }}
      >
        {/* 画布底板：白色矩形 + 阴影，让「画布」与「灰底工作区」有层次区分 */}
        <KonvaLayer listening={false}>
          <Rect
            width={document.width}
            height={document.height}
            fill="#ffffff"
            shadowColor="#141a14"
            shadowBlur={32}
            shadowOpacity={0.16}
          />
        </KonvaLayer>
        {/* 图层内容层；listening=false 表示暂不响应鼠标事件（编辑交互后续步骤再开） */}
        <KonvaLayer listening={false}>
          {images.map((layer) => (
            <ImageLayer
              key={layer.id}
              layer={layer}
              url={layer.asset_id ? urls.get(layer.asset_id) : undefined}
            />
          ))}
        </KonvaLayer>
      </Stage>
    </div>
  )
}

// 单个位图图层：按 transform 应用位置/缩放/旋转/不透明度
function ImageLayer({ layer, url }: { layer: Layer; url: string | undefined }) {
  // 位图解码完成前返回 null（KonvaImage 拿不到 image 不能渲染）
  const image = useCanvasImage(url)
  if (!image) return null

  return (
    <KonvaImage
      image={image}
      x={layer.transform.x}
      y={layer.transform.y}
      width={layer.width}
      height={layer.height}
      scaleX={layer.transform.scale_x}
      scaleY={layer.transform.scale_y}
      rotation={layer.transform.rotation}
      opacity={layer.opacity}
    />
  )
}
