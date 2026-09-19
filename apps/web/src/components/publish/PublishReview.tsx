import type { RefObject } from 'react'
import { ArrowLeft, Check, ImagePlus, LoaderCircle, X } from 'lucide-react'
import type { PostDraft, PostPurpose, StandardTag } from '@shared/types'
import { fieldLabels, missingFields, requiredFields } from '@/features/publish/publishState'
import type { FieldStates, PublishContext } from '@/features/publish/publishState'

interface Props {
  headingRef: RefObject<HTMLHeadingElement>
  draft: PostDraft
  states: FieldStates
  context: PublishContext
  purpose: PostPurpose
  updateField: (field: keyof PostDraft, value: string | number | string[]) => void
  tags: string[]
  setTags: (tags: string[]) => void
  candidates: StandardTag[]
  cover: { file: File; preview: string; id?: string } | null
  upload: (file: File) => Promise<void>
  removeCover: () => void
  uploading: boolean
  locked: boolean
  publishingSeconds: number
  publish: () => void
  back: () => void
}

export function PublishReview(props: Props) {
  const { headingRef, draft, states, context, purpose, updateField, tags, setTags, candidates, cover, upload, removeCover, uploading, locked, publishingSeconds, publish, back } = props
  const required = requiredFields(context, purpose)
  const missing = missingFields(draft, states, context, purpose)
  const fields = [...required, ...(['description'] as const).filter((field) => !required.includes(field))]
  const inherited = context.inherited_tags.map((tag) => tag.tag_id)
  const attached = [...new Set([...inherited, ...tags])]
  return <section className="publish-review p-5 sm:p-7">
    <h2 tabIndex={-1} ref={headingRef} className="text-2xl font-bold mb-6 outline-none">请检查和修改</h2>
    <fieldset disabled={locked} className="publish-review-fields">
      {fields.map((field) => <div key={field} className={field === 'description' || field === 'needed_roles' ? 'publish-field-wide' : ''}>
        <label htmlFor={`publish-${field}`} className="publish-field-label">{purpose === 'official_signup' && field === 'target_members' ? '报名人数上限' : fieldLabels[field]}{required.includes(field) && <span aria-hidden="true" className="text-rose-600"> *</span>}</label>
        {field === 'needed_roles' ? <>
          <input id={`publish-${field}`} value={draft.needed_roles.join('、')} onChange={(event) => updateField(field, event.target.value.split(/[、,，]/).map((v) => v.trim()).filter(Boolean))} maxLength={400} aria-invalid={missing.includes(field)} placeholder="策划、设计、开发…" />
          <label className="flex items-center gap-2 mt-2 text-sm text-gray-600"><input type="checkbox" checked={states.needed_roles?.status === 'none'} onChange={(event) => updateField(field, event.target.checked ? [] : [''])} />没有特定角色要求</label>
        </> : field === 'description' ? <textarea id={`publish-${field}`} rows={4} value={draft.description} maxLength={5000} onChange={(event) => updateField(field, event.target.value)} aria-invalid={missing.includes(field)} /> : field === 'target_members' ?
          <input id={`publish-${field}`} type="number" min={1} max={purpose === 'official_signup' ? context.max_members : 100} value={draft.target_members || ''} onChange={(event) => updateField(field, Number(event.target.value))} aria-invalid={missing.includes(field)} /> :
          <input id={`publish-${field}`} value={draft[field]} readOnly={field === 'activity_name' && Boolean(context.activity)} maxLength={field === 'activity_name' ? 120 : 80} onChange={(event) => updateField(field, event.target.value)} aria-invalid={missing.includes(field)} />}
      </div>)}
    </fieldset>
    <section className="mt-6" aria-label="帖子标签"><h3 className="font-semibold mb-3">标签 <span className="text-sm font-normal text-gray-500">{attached.length}/8</span></h3>
      <div className="flex flex-wrap gap-2">{context.inherited_tags.map((tag) => <span className="publish-tag is-inherited" key={tag.tag_id} title="来自关联活动，不可移除">{tag.canonical_name}</span>)}
        {tags.filter((id) => !inherited.includes(id)).map((id) => <button className="publish-tag" key={id} disabled={locked} onClick={() => setTags(tags.filter((tag) => tag !== id))} aria-label={`移除标签 ${candidates.find((tag) => tag.tag_id === id)?.canonical_name || id}`}>{candidates.find((tag) => tag.tag_id === id)?.canonical_name || id}<X size={12} /></button>)}
        {candidates.filter((tag) => !attached.includes(tag.tag_id)).map((tag) => <button className="publish-tag is-candidate" key={tag.tag_id} disabled={locked || attached.length >= 8} onClick={() => setTags([...tags, tag.tag_id])}>{tag.canonical_name}</button>)}
        {!attached.length && !candidates.length && <span className="text-sm text-gray-500">发布时将自动匹配</span>}
      </div>
    </section>
    <section className="mt-6" aria-label="帖子封面"><h3 className="font-semibold mb-3">封面 <span className="text-sm font-normal text-gray-500">选填，留空由小蓝鲸自动生成</span></h3>
      {cover ? <div className="flex flex-wrap items-start gap-3"><img src={cover.preview} alt="帖子封面预览" className="publish-cover" /><div><button className="publish-icon" title="移除封面" aria-label="移除封面" disabled={locked} onClick={removeCover}><X size={18} /></button>{uploading ? <p role="status" className="text-sm mt-2">上传中…</p> : !cover.id ? <button className="text-sm mt-2 block" onClick={() => void upload(cover.file)} disabled={locked}>重试上传</button> : <p className="text-sm text-emerald-700 mt-2">已上传</p>}</div></div> : <label className={`publish-cover-picker ${locked ? 'is-disabled' : ''}`}><ImagePlus size={20} /><span>添加封面</span><input type="file" className="sr-only" accept="image/jpeg,image/png,image/webp" aria-label="添加封面" disabled={locked} onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); event.target.value = '' }} /></label>}
    </section>
    {locked && !uploading && (
      <div className="publish-submit-status" role="status" aria-live="polite">
        <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
        <div>
          <p className="font-semibold text-ink">{publishingSeconds < 8 ? '正在校验并保存内容' : publishingSeconds < 20 ? '正在创建帖子与封面' : '仍在安全处理中'}</p>
          <p className="mt-1 text-xs leading-5 text-ink-muted">已等待 {publishingSeconds} 秒。内容已保留，请保持此页开启；重复点击不会创建重复帖子。</p>
        </div>
      </div>
    )}
    <div className="flex flex-wrap gap-3 justify-between mt-8"><button className="btn btn-secondary" disabled={locked || uploading} onClick={back}><ArrowLeft size={17} />继续对话</button><button className="btn btn-primary" disabled={locked || uploading} onClick={publish}><Check size={17} />{locked ? '正在安全提交' : '确认发布'}</button></div>
  </section>
}
