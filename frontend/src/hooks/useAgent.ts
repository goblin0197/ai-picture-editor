// 对话领域的 React Query 封装：轮次列表查询 + 发消息变更。
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { agentApi } from '@/api/agent'

// 轮次列表的缓存键：挂在会话详情键之下（['session', id, 'messages']），层级语义一致
const turnsKey = (sessionId: string) => ['session', sessionId, 'messages']

// useTurns：会话的整段对话记录。
export function useTurns(sessionId: string) {
  return useQuery({ queryKey: turnsKey(sessionId), queryFn: () => agentApi.turns(sessionId) })
}

// useSendMessage：发一条指令。成功后失效轮次缓存，让新的一轮（含模型答复）立即出现。
export function useSendMessage(sessionId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (text: string) => agentApi.send(sessionId, text),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: turnsKey(sessionId) }),
  })
}
