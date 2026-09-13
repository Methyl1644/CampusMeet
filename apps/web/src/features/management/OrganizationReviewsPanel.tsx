import { useCallback, useEffect, useState } from 'react'
import { Check, RefreshCw, X } from 'lucide-react'
import type { OrganizationApplicationSummary } from '@shared/types'
import { getOrganizationApplications, reviewOrganizationApplication } from '@/api/management'
import { getApiErrorMessage } from '@/api/auth-feedback'

export default function OrganizationReviewsPanel() {
  const [applications, setApplications] = useState<OrganizationApplicationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [reasons, setReasons] = useState<Record<string, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setApplications((await getOrganizationApplications('pending')).list)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '组织申请暂时无法加载'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const review = async (applicationId: string, decision: 'approve' | 'reject') => {
    const reason = (reasons[applicationId] || '').trim()
    if (decision === 'reject' && reason.length < 2) {
      setError('驳回申请时请填写至少 2 个字的原因')
      return
    }
    setBusyId(applicationId)
    setError('')
    try {
      await reviewOrganizationApplication(applicationId, { decision, reason, validity_days: 365 })
      await load()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '组织审核提交失败'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section aria-labelledby="organization-reviews-title">
      <div className="flex items-start justify-between gap-3 border-b border-stone pb-5">
        <div>
          <h2 id="organization-reviews-title" className="text-xl font-bold text-ink">组织审核</h2>
          <p className="mt-1 text-sm text-ink-muted">核对组织身份材料，批准后申请人将成为该组织负责人。</p>
        </div>
        <button type="button" className="icon-button" title="刷新组织申请" onClick={() => void load()}>
          <RefreshCw aria-hidden="true" className="size-4" /><span className="sr-only">刷新组织申请</span>
        </button>
      </div>
      {error && <p role="alert" className="my-4 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {loading ? <p role="status" className="py-10 text-center text-sm text-ink-muted">正在加载待审核申请...</p> : applications.length === 0 ? (
        <p className="py-10 text-center text-sm text-ink-muted">目前没有待审核的组织申请</p>
      ) : (
        <div className="divide-y divide-stone">
          {applications.map((application) => (
            <article key={application.application_id} className="grid gap-4 py-5 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,0.7fr)]">
              <div>
                <h3 className="text-base font-bold text-ink">{application.organization_name}</h3>
                <p className="mt-1 text-sm text-ink-muted">{application.org_type}{application.school_scope ? ` · ${application.school_scope}` : ''}</p>
                {application.official_email && <p className="mt-2 break-all text-sm text-ink">官方邮箱：{application.official_email}</p>}
                {application.official_page && <a className="mt-1 block break-all text-sm text-primary-700 underline" href={application.official_page} target="_blank" rel="noreferrer">查看官方页面</a>}
              </div>
              <div>
                <label className="text-sm font-medium text-ink">审核说明
                  <textarea className="input-base mt-1.5 min-h-20 resize-y" value={reasons[application.application_id] || ''} onChange={(event) => setReasons((current) => ({ ...current, [application.application_id]: event.target.value }))} placeholder="批准可留空；驳回时必填" />
                </label>
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                  <button type="button" className="btn-secondary text-red-700" disabled={busyId === application.application_id} onClick={() => void review(application.application_id, 'reject')}>
                    <X aria-hidden="true" className="size-4" />驳回
                  </button>
                  <button type="button" className="btn-primary" disabled={busyId === application.application_id} onClick={() => void review(application.application_id, 'approve')}>
                    <Check aria-hidden="true" className="size-4" />批准一年
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
