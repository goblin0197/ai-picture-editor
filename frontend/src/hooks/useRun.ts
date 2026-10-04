import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { isTerminal, runsApi, type GenerateInput, type Run, type RunStatus } from '@/api/runs'

// Progress：SSE 帧只携带进度相关字段（不含候选图），从 Run 中挑出这几项。
type Progress = Pick<Run, 'id' | 'status' | 'progress' | 'stage' | 'error'>

// 单个任务快照的缓存键，按 run id 区分，避免不同任务互相覆盖。
const runKey = (id: string) => ['run', id]

// useGenerate：提交文生图任务的变更 hook（提交后应跳转到结果页，不原地等待 worker）。
export function useGenerate() {
  return useMutation({ mutationFn: (input: GenerateInput) => runsApi.generate(input) })
}

/**
 * 合并两个进度来源：SSE 提供实时状态，快照接口提供候选图与刷新后的恢复能力。
 */
export function useRun(runId: string | null) {
  const queryClient = useQueryClient()
  // live：来自 SSE 的最新进度帧；初始为空，收到第一帧后才有值。
  const [live, setLive] = useState<Progress | null>(null)

  // snapshot：快照查询。提供候选图（SSE 帧里没有），也用于刷新 / 重进页面后的状态恢复。
  const snapshot = useQuery({
    queryKey: runKey(runId ?? ''),
    queryFn: () => runsApi.get(runId as string),
    // runId 为空时（如尚未提交任务）不发起查询。
    enabled: Boolean(runId),
  })

  useEffect(() => {
    // 没有任务 id 时不建立 SSE 连接。
    if (!runId) return

    // 直连 SSE 端点获取实时进度；注意 /events 不在 /api 下，是独立的推送通道（便于反代单独关缓冲）。
    const source = new EventSource(`/events/runs/${runId}`)
    // 失效快照缓存以触发重新拉取：用于取回终态后的候选图，或在连接异常时兜底刷新。
    const refresh = () => void queryClient.invalidateQueries({ queryKey: runKey(runId) })

    source.onmessage = (event) => {
      // 每帧是一个 Progress 的 JSON，解析后写入 live 状态驱动 UI 更新。
      const payload = JSON.parse(event.data) as Progress
      setLive(payload)
      if (isTerminal(payload.status)) {
        // 到终态：服务端会主动断开，这里也主动 close，并刷新快照以取回候选图。
        source.close()
        refresh()
      }
    }
    // 连接中断时回退到快照接口，避免界面停在过期进度上
    source.onerror = refresh

    // 清理函数：runId 变化或组件卸载时关闭旧连接，防止连接泄漏，也防止旧任务的帧串到新任务。
    return () => source.close()
  }, [runId, queryClient])

  const run = snapshot.data
  // 切换任务后旧连接的残留帧不应影响新任务
  // 仅当 live 帧的 id 与当前 runId 一致时才采用；否则视为上一个任务的残留帧，直接忽略。
  const current = live?.id === runId ? live : null
  // 状态优先取实时帧，其次退回快照——实时帧更新更快。
  const status: RunStatus | undefined = current?.status ?? run?.status

  // 合并输出：进度 / 阶段 / 错误优先用实时帧，回退到快照，再回退到默认值；
  // 候选图只来自快照（SSE 帧不含）；notFound 由快照查询是否报错（如 404）决定。
  return {
    status,
    progress: current?.progress ?? run?.progress ?? 0,
    stage: current?.stage ?? run?.stage ?? '',
    error: current?.error ?? run?.error ?? null,
    candidates: run?.candidates ?? [],
    isLoading: snapshot.isPending,
    notFound: snapshot.isError,
  }
}
