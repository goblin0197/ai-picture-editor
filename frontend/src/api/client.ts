// 通用请求出口：本文件封装所有对后端 /api 的 HTTP 调用，
// 并把错误统一归一化为 ApiError，供上层各领域 API 模块（auth/assets/runs）复用。

// ApiError：归一化的接口错误。
// 除标准 Error 的 message 外，额外携带 HTTP 状态码 status，
// 便于上层据此区分「401 未登录」等场景（见 useCurrentUser 对 401 的处理）。
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// request：底层请求封装，所有 api.* 方法最终都走这里。
// 泛型 T 为后端 JSON 反序列化后的出参类型。
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // 用相对路径 /api 前缀发起请求：前后端同源，开发环境由 Vite 代理到后端端口，
  // 生产由 FastAPI 同源托管——绝不能硬编码绝对地址，否则会破坏 httpOnly Cookie 的同源携带。
  const response = await fetch(`/api${path}`, {
    ...init,
    // 默认按 JSON 提交；把调用方传入的 headers 展开在后面，允许其覆盖默认值。
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok) {
    // 非 2xx：尝试解析后端错误体（通常是 { detail: "..." }）。
    // 后端也可能返回非 JSON（如网关层错误），故用 .catch(() => null) 兜底，
    // 解析失败降级为 null，而不是让 await 再抛一个解析异常盖掉真正的错误。
    const detail = await response.json().catch(() => null)
    // 优先用后端给的 detail 文案，缺失时退回 HTTP 状态短语；status 一并带上供上层判断。
    throw new ApiError(response.status, detail?.detail ?? response.statusText)
  }
  // 204 No Content 没有响应体，调用 .json() 会抛错，因此直接返回 undefined（如登出接口）；
  // 其余情况解析 JSON 为 T。
  return response.status === 204 ? (undefined as T) : response.json()
}

// api：对外暴露的四个 HTTP 动词快捷方法，统一走上面的 request。
export const api = {
  // GET：无请求体。
  get: <T>(path: string) => request<T>(path),
  // POST：body 为空时不序列化，避免把 undefined 变成字符串 "undefined"。
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  // PATCH：同 POST，body 可选。
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: body === undefined ? undefined : JSON.stringify(body) }),
  // DELETE：无请求体。
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
