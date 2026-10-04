import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES, assetsApi } from '@/api/assets'

// 素材列表的 react-query 缓存键；上传成功后据此失效以触发重新拉取。
const ASSETS_KEY = ['assets']

/** 前置校验类型与体积，避免明显不合规的文件白跑一次网络请求。 */
export function checkFile(file: File): string | null {
  if (!ACCEPTED_TYPES.includes(file.type)) return '仅支持 JPG、PNG 与 WebP'
  if (file.size > MAX_UPLOAD_BYTES) return '文件超过 20 MB 上限'
  return null
}

// useAssets：读取素材列表。limit 可选，透传给接口控制返回条数。
export function useAssets(limit?: number) {
  return useQuery({ queryKey: ASSETS_KEY, queryFn: () => assetsApi.list(limit) })
}

// useUploadAsset：上传素材的变更 hook。
export function useUploadAsset() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => assetsApi.upload(file),
    // 上传成功后失效 ['assets']，让列表查询自动重新拉取，新素材即时出现在列表里。
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ASSETS_KEY }),
  })
}
