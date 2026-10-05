// 编辑会话领域接口：类型定义 + sessionsApi 请求封装。
// 后端对应 app/layers.py（文档结构）与 routers/sessions.py（接口）。
import type { Asset } from '@/api/assets'
import { api } from '@/api/client'

// LayerKind：图层类别，与后端 LayerKind 枚举的取值对齐。
export type LayerKind = 'image' | 'text' | 'shape'

// Transform：相对画布左上角的位置与形变；缩放是倍率而非像素。
export type Transform = {
  x: number
  y: number
  scale_x: number
  scale_y: number
  rotation: number
}

// Layer：单个图层描述（不含像素，位图经 asset_id 引用素材）。
export type Layer = {
  id: string
  kind: LayerKind
  name: string
  width: number
  height: number
  asset_id: string | null // 仅 image 图层有值
  transform: Transform
  opacity: number
  visible: boolean
  locked: boolean
}

// LayerDocument：一份完整画布文档；后端把它整体存进 JSONB，是画布的权威描述。
export type LayerDocument = {
  width: number
  height: number
  layers: Layer[]
}

// Session：会话摘要（列表用）；document/assets 只在详情里返回。
export type Session = {
  id: string
  title: string
  revision: number // 切图/采用候选时递增，用于判断本地状态是否过期
  original_asset_id: string
  current_asset_id: string
  created_at: string
  updated_at: string
}

// SessionDetail：会话详情 = 摘要 + 画布文档 + 图片墙。
export type SessionDetail = Session & {
  document: LayerDocument
  assets: Asset[]
}

// HistoryEntry：一条编辑历史；action 的中文文案见 ACTION_LABELS。
export type HistoryEntry = {
  seq: number
  action: string
  params: Record<string, unknown>
  result: Record<string, unknown>
  created_at: string
}

// SessionCreateInput：建会话入参。current 进画布，asset_ids 其余进图片墙。
export type SessionCreateInput = {
  current_asset_id: string
  asset_ids?: string[]
  title?: string
}

// SessionPatchInput：改会话入参，两个都可选（部分更新）。
export type SessionPatchInput = {
  title?: string
  current_asset_id?: string
}

// ACTION_LABELS：历史动作名 → 中文展示文案；未知的动作名直接原样展示。
export const ACTION_LABELS: Record<string, string> = {
  create_session: '新建会话',
  switch_current: '切换当前图',
}

// sessionsApi：会话领域接口。
export const sessionsApi = {
  // create：建会话。候选页「进入编辑」与创作页点素材都走这里。
  create: (input: SessionCreateInput) => api.post<SessionDetail>('/sessions', input),
  // list：会话列表（侧栏「历史对话」）。
  list: () => api.get<Session[]>('/sessions'),
  // get：会话详情，编辑页刷新/直链进入时恢复全部状态。
  get: (id: string) => api.get<SessionDetail>(`/sessions/${id}`),
  // patch：部分更新（改名 / 切换画布当前图）。
  patch: (id: string, input: SessionPatchInput) =>
    api.patch<SessionDetail>(`/sessions/${id}`, input),
  // history：编辑历史（最新在前）。
  history: (id: string) => api.get<HistoryEntry[]>(`/sessions/${id}/history`),
}
