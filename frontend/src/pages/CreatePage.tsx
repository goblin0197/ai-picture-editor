import { useNavigate } from 'react-router-dom'

import AssetCard from '@/components/AssetCard'
import GenerateForm from '@/components/GenerateForm'
import ImageDropzone from '@/components/ImageDropzone'
// errorMessage：把各类错误归一化成可展示文案。
import { errorMessage } from '@/hooks/useAuth'
// useAssets 拉取历史素材列表；useUploadAsset 上传新素材（成功后自动失效素材缓存）。
import { useAssets, useUploadAsset } from '@/hooks/useAssets'
// useGenerate：提交文生图任务。
import { useGenerate } from '@/hooks/useRun'
// 编辑会话：把历史素材一键建成会话并跳进编辑器。
import { useCreateSession } from '@/hooks/useSessions'
// 提示词草稿的读写：暂存在 sessionStorage，避免误刷新丢失输入。
import { readPromptDraft, savePromptDraft } from '@/lib/promptDraft'

// 创作页：工作台首页。自上而下是生成表单、上传入口、历史素材网格。
export default function CreatePage() {
  const navigate = useNavigate()
  // assets 默认空数组，避免首次渲染时为 undefined；isPending 表示素材列表仍在加载。
  const { data: assets = [], isPending } = useAssets()
  const upload = useUploadAsset()
  const generate = useGenerate()
  const createSession = useCreateSession()

  // openEditor：把一张素材建成编辑会话并跳进编辑器；标题留空由后端给默认值。
  const openEditor = (assetId: string) =>
    createSession.mutate(
      { current_asset_id: assetId },
      { onSuccess: (session) => navigate(`/editor/${session.id}`) },
    )

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <h1 className="text-ink mb-6 text-2xl font-semibold tracking-tight">创作</h1>

      {/* 生成表单：预填上次草稿；提交成功后清空草稿并跳到结果页 */}
      <GenerateForm
        defaultPrompt={readPromptDraft()}
        pending={generate.isPending}
        onSubmit={(input) =>
          generate.mutate(input, {
            onSuccess: (run) => {
              // 任务已建：清掉草稿，随即跳到 /candidates/:runId；
              // 不原地等结果——任务由 worker 异步产出，结果页靠快照接口恢复
              savePromptDraft('')
              navigate(`/candidates/${run.id}`)
            },
          })
        }
      />
      {/* 生成提交失败时的错误提示 */}
      {generate.isError && (
        <p className="text-danger mt-2 text-sm">{errorMessage(generate.error)}</p>
      )}

      {/* 上传区：把选中的文件交给 upload mutation；上传中禁用拖放区 */}
      <section className="mt-10">
        <h2 className="text-muted mb-3 text-sm font-medium">上传已有图片</h2>
        <ImageDropzone
          onFile={(file) => upload.mutate(file, { onSuccess: (asset) => openEditor(asset.id) })}
          disabled={upload.isPending || createSession.isPending}
        />
        {upload.isError && (
          <p className="text-danger mt-2 text-sm">{errorMessage(upload.error)}</p>
        )}
      </section>

      {/* 历史素材：三态渲染——加载中 / 空 / 网格 */}
      <section className="mt-10">
        <h2 className="text-muted mb-3 text-sm font-medium">历史素材</h2>

        {isPending ? (
          <p className="text-faint text-sm">加载中…</p>
        ) : assets.length === 0 ? (
          <p className="text-faint text-sm">还没有素材，先描述画面或上传一张图片。</p>
        ) : (
          // 响应式网格：随宽度从 2 列增到 4 列
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {assets.map((asset) => (
              <AssetCard key={asset.id} asset={asset} onSelect={() => openEditor(asset.id)} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
