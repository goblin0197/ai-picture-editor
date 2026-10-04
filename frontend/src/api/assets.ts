import { ApiError } from '@/api/client'

// AssetKind：素材的用途分类，贯穿抠图 / 换背景 / 导出等各环节。
export type AssetKind =
  | 'original'
  | 'generated'
  | 'subject'
  | 'background'
  | 'mask'
  | 'marketing'
  | 'export'

// Asset：单个素材的出参模型。
// url 为后端签发的签名 URL（有时效），width / height / size_bytes 等来自实际解码结果。
export type Asset = {
  id: string
  kind: AssetKind
  source: 'upload' | 'generate' | 'tool'
  image_format: string
  width: number
  height: number
  size_bytes: number
  has_alpha: boolean
  created_at: string
  url: string
}

// 上传体积上限 20 MB，与后端校验保持一致（前端先行拦截，省一次网络往返）。
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024
// 允许的图片 MIME 类型（最终以后端按实际解码结果为准，这里仅做前置过滤）。
export const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

// assetsApi：素材领域接口。注意上传 / 列表均直接用 fetch 而非通用 api，原因见方法内注释。
export const assetsApi = {
  // upload：上传单个文件。
  async upload(file: File): Promise<Asset> {
    // 用 FormData 承载文件，对应 multipart/form-data 表单上传。
    const body = new FormData()
    body.append('file', file)

    // 这里刻意不走通用 api：api 会强制加 'Content-Type: application/json'，
    // 而 multipart 需要浏览器自动生成带 boundary 的 Content-Type。
    // 故直接用 fetch，并且不手动设 Content-Type，让浏览器补上正确的 boundary。
    const response = await fetch('/api/assets', { method: 'POST', body })
    if (!response.ok) {
      // 仍沿用与通用 api 一致的错误归一化：解析后端 detail，失败则用兜底文案，并带上 status。
      const detail = await response.json().catch(() => null)
      throw new ApiError(response.status, detail?.detail ?? '上传失败')
    }
    return response.json()
  },

  // list：拉取当前用户的素材列表（后端已按 user_id 过滤，默认最多 50 条）。
  async list(limit = 50): Promise<Asset[]> {
    // GET 无请求体、无需 FormData，用通用 api.get 亦可；此处与 upload 保持一致直接用 fetch。
    const response = await fetch(`/api/assets?limit=${limit}`)
    if (!response.ok) throw new ApiError(response.status, '读取素材失败')
    return response.json()
  },
}
