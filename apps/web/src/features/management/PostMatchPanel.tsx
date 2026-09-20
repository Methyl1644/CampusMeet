import { useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, Sparkles } from 'lucide-react'
import type { MatchResult } from '@shared/types'
import { matchPosts } from '@/api/agent'
import { getApiErrorMessage } from '@/api/auth-feedback'

type Candidate = MatchResult & { id: string }

function candidateName(candidate: Candidate) {
  return candidate.nickname?.trim() || '站内用户'
}

function candidateDetail(candidate: Candidate) {
  return [candidate.major, candidate.grade].filter(Boolean).join(' · ') || '校园伙伴'
}

function candidateSkills(candidate: Candidate) {
  return (candidate.skills ?? []).filter((skill) => skill.trim()).slice(0, 6)
}

export default function PostMatchPanel({ postId }: { postId: string }) {
  const [candidates, setCandidates] = useState<Candidate[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    setBusy(true); setError('')
    try {
      const response = await matchPosts(postId)
      const resolved = (response?.matches ?? []).map((match) => {
        const id = match.user_id ?? match.candidate_id ?? ''
        return { ...match, id, reason: match.reason ?? match.summary ?? '' }
      })
      setCandidates(resolved.filter((candidate) => candidate.id))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'AI 匹配暂时不可用，请稍后重试'))
    } finally { setBusy(false) }
  }

  return <section aria-labelledby="post-match-title">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 id="post-match-title" className="text-lg font-bold text-ink">AI 推荐队友</h3>
        <p className="mt-1 text-sm text-ink-muted">仅匹配已主动授权的认证用户，并只使用对方允许用于推荐的资料。推荐结果不含联系方式。</p>
      </div>
      <button type="button" className="btn-secondary shrink-0" disabled={busy} onClick={() => void run()}>
        {busy ? <RefreshCw aria-hidden="true" className="size-4 animate-spin" /> : <Sparkles aria-hidden="true" className="size-4" />}
        {busy ? '匹配中...' : candidates ? '重新推荐' : '推荐队友'}
      </button>
    </div>
    {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    {candidates === null
      ? <p className="mt-3 border-y border-stone py-5 text-sm text-ink-muted">还没有推荐结果，点击上方按钮让 AI 帮你找人。</p>
      : candidates.length === 0
        ? <p className="mt-3 border-y border-stone py-5 text-sm text-ink-muted">暂无可推荐的候选人，可以先等等加入申请。</p>
        : <div className="mt-3 space-y-3">{candidates.map((candidate) => <article key={candidate.id} className="grid gap-3 rounded-card border border-stone bg-paper p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[#EAF3F0] text-sm font-bold text-campus-green">
                {candidateName(candidate).charAt(0)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-ink">{candidateName(candidate)}</span>
                <span className="mt-0.5 block truncate text-xs text-ink-muted">{candidateDetail(candidate)}</span>
              </span>
            </div>
            {candidate.reason && <p className="mt-2 text-sm text-ink-muted">推荐理由：{candidate.reason}</p>}
            {candidateSkills(candidate).length > 0 && <ul className="mt-2 flex flex-wrap gap-1.5">{candidateSkills(candidate).map((skill) => <li key={skill} className="tag-chip">{skill}</li>)}</ul>}
          </div>
          <div className="flex items-center gap-3 sm:flex-col sm:items-end">
            <span className="inline-flex items-center rounded-full border border-[#E6D9BC] bg-[#FBF6EC] px-2.5 py-1 text-xs font-bold text-campus-gold">{Math.round(candidate.score)}% 匹配</span>
            <Link to={`/users/${candidate.id}`} className="btn-secondary min-h-10 px-3">查看主页</Link>
          </div>
        </article>)}</div>}
  </section>
}
