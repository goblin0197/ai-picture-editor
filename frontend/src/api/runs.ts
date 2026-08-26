import { api } from '@/api/client'
import type { Asset } from '@/api/assets'

// Ratio：输出比例，与后端 ratios.py 声明的交付尺寸对齐。
export type Ratio = '1:1' | '4:5' | '3:4' | '9:16' | '16:9'

// RunStatus：任务生命周期状态。queued / running 为进行中，其余三个为终态。
export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled'

// Run：一次工具任务（如文生图）的完整快照。
// progress 为 0~1 进度，stage 为当前阶段文案，candidates 为产出的候选图。
export type Run = {
  id: string
  tool: string
  status: RunStatus
  progress: number
  stage: string
  error: string | null
  prompt: string | null
  candidates: Asset[]
}

// GenerateInput：发起文生图的入参。
// negative_prompt 与 reference_asset_ids 可选（部分提供方不支持参考图）。
export type GenerateInput = {
  prompt: string
  ratio: Ratio
  count: number
  negative_prompt?: string
  reference_asset_ids?: string[]
}

// RATIO_LABELS：比例枚举到中文展示文案的映射，供下拉选择等 UI 使用。
export const RATIO_LABELS: Record<Ratio, string> = {
  '1:1': '方形 1:1',
  '4:5': '竖版 4:5',
  '3:4': '竖版 3:4',
  '9:16': '长图 9:16',
  '16:9': '横版 16:9',
}

// isTerminal：判断任务是否已到终态（成功 / 失败 / 取消）。
// useRun 收到终态帧后据此关闭 SSE 连接。
export function isTerminal(status: RunStatus) {
  return status === 'succeeded' || status === 'failed' || status === 'canceled'
}

// runsApi：任务领域接口。
export const runsApi = {
  // generate：提交文生图任务。后端建记录并投递队列后即返回，不会同步等结果。
  generate: (input: GenerateInput) => api.post<Run>('/generations', input),
  // get：按 id 读取任务快照，用于刷新恢复与获取候选图。
  get: (id: string) => api.get<Run>(`/runs/${id}`),
}
