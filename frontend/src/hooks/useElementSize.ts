// 观察元素实际尺寸，供 Konva Stage 这类需要显式宽高的组件使用。
// Konva 的 <Stage> 不支持 CSS 自适应，必须传数字宽高，因此用 ResizeObserver 跟踪容器。
import { useEffect, useRef, useState } from 'react'

/** 观察元素实际尺寸，供 Konva Stage 这类需要显式宽高的组件使用。 */
export function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const element = ref.current
    if (!element) return

    // ResizeObserver：元素尺寸变化（窗口缩放、侧栏开合）都会回调
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      // 取整：Stage 的宽高需要整数像素，避免亚像素抖动
      setSize({ width: Math.round(width), height: Math.round(height) })
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  // ref 挂到容器上，size 供画布使用
  return [ref, size] as const
}
