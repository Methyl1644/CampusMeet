import { useState } from 'react'
import { RefreshCw, Sparkles } from 'lucide-react'
import { matchPosts } from '@/api/agent'
import { getApiErrorMessage } from '@/api/auth-feedback'
import type { MatchResult } from '@shared/types'

export default function TeammateMatchesPanel({ postId }: { postId: string }) {
  const [matches, setMatches] = useState<MatchResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    if (loading) return
    setLoading(true)
    setError('')
    try {
      const result = await matchPosts(postId)
      setMatches(result.matches)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, '暂时无法获取推荐，请稍后重试'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section aria-labelledby="teammate-matches-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 id="teammate-matches-title" className="text-base font-bold text-ink">队友推荐</h3>
          <p className="mt-1 text-sm leading-6 text-ink-muted">仅匹配已主动授权的用户，并只使用对方允许用于推荐的资料。</p>
        </div>
        <button type="button" className="btn-secondary" disabled={loading} onClick={() => void load()}>
          {matches ? <RefreshCw aria-hidden="true" className="size-4" /> : <Sparkles aria-hidden="true" className="size-4" />}
          {loading ? '匹配中...' : matches ? '重新推荐' : '推荐队友'}
        </button>
      </div>

      {error && <p role="alert" className="mt-3 border-l-2 border-red-400 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {matches?.length === 0 && <p className="mt-4 text-sm text-ink-muted">暂无已授权且符合条件的候选人。</p>}
      {matches && matches.length > 0 && (
        <ul className="mt-4 divide-y divide-stone border-y border-stone">
          {matches.map((match) => (
            <li key={match.user_id ?? match.candidate_id} className="grid gap-2 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
              <div className="min-w-0">
                <p className="font-semibold text-ink">{match.nickname || `候选用户 ${match.user_id ?? match.candidate_id ?? ''}`}</p>
                <p className="mt-1 text-sm leading-6 text-ink-muted">{match.reason || match.summary || '信息不足，建议先沟通确认。'}</p>
                {match.skills && match.skills.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {match.skills.map((skill) => <span key={skill} className="tag-chip">{skill}</span>)}
                  </div>
                )}
              </div>
              <span className="text-sm font-semibold tabular-nums text-primary-700">{Math.round(match.score)}% 匹配</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
