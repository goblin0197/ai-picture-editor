// 前端应用入口：由 index.html 加载，负责把 React 应用挂载到真实 DOM，
// 并在最外层套上全局 Provider（这里是 React Query 的客户端）。

// React Query：管理服务端状态（请求、缓存、失效）；QueryClientProvider 通过 Context 下发客户端。
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// StrictMode：开发期严格模式，会有意二次调用部分函数以暴露副作用问题（不影响生产构建）。
import { StrictMode } from 'react'
// createRoot：React 18 并发渲染入口，替代旧版 ReactDOM.render。
import { createRoot } from 'react-dom/client'

import App from '@/App'
// 全局样式（Tailwind v4 的 @theme 设计令牌与自定义工具类都在此文件）。
import '@/index.css'

// 创建全局唯一的 React Query 客户端并集中配置默认行为：
// - retry: 1                      请求失败最多自动重试 1 次（默认 3 次，这里更克制）。
// - refetchOnWindowFocus: false   切回窗口时不自动重新拉取，避免频繁请求打扰用户。
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

// 找到 index.html 中的 #root 容器并创建根节点（`!` 断言该元素一定存在）。
createRoot(document.getElementById('root')!).render(
  // StrictMode 仅开发期生效，用于提前发现不安全的副作用。
  <StrictMode>
    {/* QueryClientProvider 把上面创建的客户端注入整棵组件树，之后任意组件都能用 useQuery / useMutation */}
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
