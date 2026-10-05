// 会话领域的 React Query 封装：查询键、缓存写入与失效策略集中在这里。
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { sessionsApi, type SessionCreateInput, type SessionPatchInput } from '@/api/sessions'

// 列表一个键；详情/历史按会话 id 分键，避免互相覆盖。
const LIST_KEY = ['sessions']
const detailKey = (id: string) => ['session', id]
const historyKey = (id: string) => ['session', id, 'history']

// useSessions：会话列表（侧栏「历史对话」）。
export function useSessions() {
  return useQuery({ queryKey: LIST_KEY, queryFn: sessionsApi.list })
}

// useSession：单个会话详情；id 为空（/editor 无参数时）不发起查询。
export function useSession(id: string | null) {
  return useQuery({
    queryKey: detailKey(id ?? ''),
    queryFn: () => sessionsApi.get(id as string),
    enabled: Boolean(id),
  })
}

// useSessionHistory：会话的编辑历史（图层面板「编辑记录」区）。
export function useSessionHistory(id: string | null) {
  return useQuery({
    queryKey: historyKey(id ?? ''),
    queryFn: () => sessionsApi.history(id as string),
    enabled: Boolean(id),
  })
}

// useCreateSession：建会话。成功后直接把详情写入缓存（跳转过去免 loading），
// 并失效列表让侧栏出现新会话。
export function useCreateSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: SessionCreateInput) => sessionsApi.create(input),
    onSuccess: (detail) => {
      queryClient.setQueryData(detailKey(detail.id), detail)
      void queryClient.invalidateQueries({ queryKey: LIST_KEY })
    },
  })
}

// usePatchSession：改名 / 切换画布当前图。成功后同步详情缓存，
// 并失效列表（侧栏的标题/时间要变）与历史（多了 switch_current 等记录）。
export function usePatchSession(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: SessionPatchInput) => sessionsApi.patch(id, input),
    onSuccess: (detail) => {
      queryClient.setQueryData(detailKey(id), detail)
      void queryClient.invalidateQueries({ queryKey: LIST_KEY })
      void queryClient.invalidateQueries({ queryKey: historyKey(id) })
    },
  })
}
