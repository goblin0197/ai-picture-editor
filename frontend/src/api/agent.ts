// 对话指令领域接口：编辑页左栏「自然语言修图」的类型与请求封装。
import { api } from '@/api/client'
import type { RunStatus } from '@/api/runs'

// PlanStep：规划出的一个执行步骤；run_id 指向下发的 ToolRun（未下发为 null）。
export type PlanStep = {
  tool: string
  label: string
  run_id: string | null
}

// Turn：一轮问答（用户指令 + 模型答复 + 计划步骤）。
// status 只代表规划本身；每步执行进度经 useRun 订阅对应 run_id 获取。
export type Turn = {
  id: string
  revision: number
  goal: string
  reply: string
  status: RunStatus
  error: string | null
  created_at: string
  steps: PlanStep[]
}

// agentApi：对话领域接口。后端是 /api/sessions/{id}/messages 的 GET 与 POST。
export const agentApi = {
  // turns：整段对话记录（按时间正序），打开会话时恢复。
  turns: (sessionId: string) => api.get<Turn[]>(`/sessions/${sessionId}/messages`),
  // send：发送一条指令，同步拿到规划结果（工具的实际执行在 worker 侧异步进行）。
  send: (sessionId: string, text: string) =>
    api.post<Turn>(`/sessions/${sessionId}/messages`, { text }),
}
