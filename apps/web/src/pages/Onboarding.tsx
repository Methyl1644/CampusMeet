import { useEffect, useMemo, useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Clock3,
  Eye,
  GraduationCap,
  RefreshCw,
  Search,
  UserRound,
} from 'lucide-react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '@/api/auth-feedback'
import { completeOnboarding, getOnboarding, saveOnboarding } from '@/api/onboarding'
import { useToast } from '@/components/Toast'
import CampusMark from '@/components/CampusMark'
import ChoiceChips from '@/components/onboarding/ChoiceChips'
import OnboardingShell from '@/components/onboarding/OnboardingShell'
import {
  canContinue,
  canEditOnboarding,
  canEnterOnboarding,
  type OnboardingLoadStatus,
} from '@/components/onboarding/onboardingState'
import { useAuthStore } from '@/store/authStore'
import { requiredRoute } from '@/router/authRouting'
import { COMMON_SKILLS } from '@shared/constants'
import type { OnboardingDraft, OnboardingUpdate } from '@shared/types'

const INTEREST_OPTIONS = [
  '人工智能',
  '产品设计',
  '数学建模',
  '学术科研',
  '软件开发',
  '创新创业',
  '摄影',
  '音乐',
  '阅读',
  '羽毛球',
  '跑步',
  '篮球',
  '旅行',
  '户外徒步',
  '志愿服务',
  '校园文化',
  '语言学习',
  '辩论表达',
  '数据分析',
  '电影',
] as const

const GOAL_OPTIONS = [
  '比赛组队',
  '学习交流',
  '科研合作',
  '兴趣社交',
  '志愿活动',
  '寻找长期伙伴',
] as const

const AVAILABILITY_OPTIONS = ['工作日白天', '工作日晚间', '周末白天', '周末晚间'] as const
const SKILL_OPTIONS = [...new Set(COMMON_SKILLS)]

const VISIBILITY_OPTIONS = [
  ['major', '专业'],
  ['grade', '年级'],
  ['interests', '兴趣'],
  ['skills', '技能'],
  ['availability', '空闲时间'],
] as const

const DEFAULT_VISIBILITY: Record<string, boolean> = {
  major: true,
  grade: true,
  interests: true,
  skills: true,
  availability: false,
}

const STEP_META = [
  {
    label: '身份',
    title: '你希望大家怎么称呼你？',
    tipTitle: '真实、好认就够了',
    tip: '昵称会出现在组队帖、申请和消息里。之后仍可在个人资料中修改。',
  },
  {
    label: '校园资料',
    title: '你在南大的学习坐标',
    tipTitle: '让合作更有上下文',
    tip: '专业与年级能帮助队友判断课程背景和项目节奏，不需要写得过细。',
  },
  {
    label: '兴趣',
    title: '最近有哪些方向吸引你？',
    tipTitle: '至少选三个',
    tip: '兴趣用于活动与队友推荐。选择你愿意真正投入时间的方向。',
  },
  {
    label: '目标',
    title: '你想在 CampusMate 遇见什么？',
    tipTitle: '可以有不止一个答案',
    tip: '参与目标会帮助我们区分短期组队、长期合作与轻松的校园连接。',
  },
  {
    label: '技能 / 时间',
    title: '把你的节奏告诉未来队友',
    tipTitle: '这一页可以跳过',
    tip: '明确技能和可投入时间，能减少组队后的反复确认。留空也不会影响完成。',
  },
  {
    label: '预览',
    title: '看看大家会如何认识你',
    tipTitle: '由你决定公开范围',
    tip: '关闭勾选后，对应内容不会出现在公开资料中。私密账号信息始终不会展示。',
  },
] as const

const clampStep = (step: number) => Math.max(1, Math.min(6, step))

function toUpdate(draft: OnboardingDraft, step: number): OnboardingUpdate {
  return {
    step,
    nickname: draft.nickname,
    avatar: draft.avatar,
    major: draft.major,
    grade: draft.grade,
    interests: draft.interests,
    looking_for: draft.looking_for,
    skills: draft.skills,
    availability: draft.availability,
    bio: draft.bio,
    profile_visibility: draft.profile_visibility,
  }
}

export default function Onboarding() {
  const location = useLocation()
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  const redirectTo = requiredRoute(user, location.pathname)
  if (redirectTo) {
    return <Navigate to={redirectTo} replace />
  }

  return <OnboardingFlow />
}

function OnboardingFlow() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const { user, setUser, updateUser } = useAuthStore()
  const [draft, setDraft] = useState<OnboardingDraft | null>(null)
  const [step, setStep] = useState(1)
  const [direction, setDirection] = useState(1)
  const [loadStatus, setLoadStatus] = useState<OnboardingLoadStatus>('loading')
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [isSaving, setIsSaving] = useState(false)
  const [interestQuery, setInterestQuery] = useState('')
  const [showAllInterests, setShowAllInterests] = useState(false)

  useEffect(() => {
    let active = true
    setLoadStatus('loading')
    setDraft(null)
    getOnboarding()
      .then((savedDraft) => {
        if (!active) return
        if (savedDraft.onboarding_completed) {
          updateUser({ onboarding_completed: true, onboarding_step: 6 })
          navigate('/home', { replace: true })
          return
        }
        const temporaryNickname = user?.email.split('@')[0] ?? ''
        const nickname =
          savedDraft.onboarding_step === 1 && savedDraft.nickname === temporaryNickname
            ? ''
            : savedDraft.nickname ?? ''
        setDraft({
          ...savedDraft,
          nickname,
          major: savedDraft.major ?? '',
          grade: savedDraft.grade ?? '',
          interests: savedDraft.interests ?? [],
          looking_for: savedDraft.looking_for ?? [],
          skills: savedDraft.skills ?? [],
          availability: savedDraft.availability ?? {},
          bio: savedDraft.bio ?? '',
          profile_visibility: {
            ...DEFAULT_VISIBILITY,
            ...(savedDraft.profile_visibility ?? {}),
          },
        })
        setStep(clampStep(savedDraft.onboarding_step || 1))
        setLoadStatus('ready')
      })
      .catch((error) => {
        if (active) {
          setDraft(null)
          setLoadStatus('error')
          showToast(getApiErrorMessage(error, '资料加载失败，请稍后重试'), 'error')
        }
      })

    return () => {
      active = false
    }
  }, [loadAttempt, navigate, showToast, updateUser, user?.email])

  const visibleInterests = useMemo(() => {
    if (!draft) return []
    const query = interestQuery.trim().toLocaleLowerCase('zh-CN')
    if (query) {
      return INTEREST_OPTIONS.filter((option) => option.toLocaleLowerCase('zh-CN').includes(query))
    }
    if (showAllInterests) return [...INTEREST_OPTIONS]
    return [...new Set([...draft.interests, ...INTEREST_OPTIONS.slice(0, 12)])]
  }, [draft, interestQuery, showAllInterests])

  const saveAndGo = async (nextStep: number) => {
    if (isSaving || !canEnterOnboarding(loadStatus, draft)) return
    setIsSaving(true)
    try {
      const savedDraft = await saveOnboarding(toUpdate(draft, nextStep))
      setDraft((current) => ({
        ...current,
        ...savedDraft,
        bio: savedDraft.bio ?? '',
        profile_visibility: {
          ...DEFAULT_VISIBILITY,
          ...(savedDraft.profile_visibility ?? {}),
        },
      }))
      setDirection(nextStep > step ? 1 : -1)
      setStep(nextStep)
    } catch (error) {
      showToast(getApiErrorMessage(error, '保存失败，本页内容已保留'), 'error')
    } finally {
      setIsSaving(false)
    }
  }

  const handleContinue = async () => {
    if (!canEnterOnboarding(loadStatus, draft) || !canContinue(step, draft) || isSaving) return
    if (step < 6) {
      await saveAndGo(step + 1)
      return
    }

    setIsSaving(true)
    try {
      await saveOnboarding(toUpdate(draft, 6))
      const completedUser = await completeOnboarding()
      setUser(completedUser)
      showToast('资料已完成，欢迎来到 CampusMate', 'success')
      navigate('/home', { replace: true })
    } catch (error) {
      showToast(getApiErrorMessage(error, '完成失败，本页内容已保留'), 'error')
    } finally {
      setIsSaving(false)
    }
  }

  const handleBack = () => {
    if (step > 1) void saveAndGo(step - 1)
  }

  const setAvailability = (key: string, selected: boolean) => {
    if (!draft) return
    setDraft((current) => {
      if (!current) return current
      return {
        ...current,
        availability: { ...current.availability, [key]: selected },
      }
    })
  }

  if (loadStatus === 'loading') {
    return (
      <main className="onboarding-page items-center justify-center px-5">
        <div role="status" className="flex items-center gap-2 text-sm text-ink-muted">
          <Clock3 aria-hidden="true" className="size-[18px] text-primary-600" />
          正在恢复你的资料
        </div>
      </main>
    )
  }

  if (!canEnterOnboarding(loadStatus, draft)) {
    return (
      <main className="onboarding-page items-center justify-center px-5">
        <section className="w-full max-w-md text-center" aria-labelledby="onboarding-load-error-title">
          <CampusMark />
          <h1 id="onboarding-load-error-title" className="mt-8 text-2xl font-semibold text-ink">
            暂时无法载入资料
          </h1>
          <p className="mt-3 text-sm leading-6 text-ink-muted">
            你的已保存内容没有被更改。重新载入后再继续完善资料。
          </p>
          <button
            type="button"
            onClick={() => setLoadAttempt((current) => current + 1)}
            className="btn-primary mt-6 min-h-11 px-5"
          >
            <RefreshCw aria-hidden="true" className="size-[18px]" />
            重新载入
          </button>
        </section>
      </main>
    )
  }

  const meta = STEP_META[step - 1]
  const valid = canContinue(step, draft)
  const stageDisabled = !canEditOnboarding(loadStatus, draft, isSaving)

  return (
    <OnboardingShell
      step={step}
      direction={direction}
      isSaving={isSaving}
      stageDisabled={stageDisabled}
      canGoBack={step > 1}
      continueDisabled={!valid}
      continueLabel={step === 6 ? '完成资料' : '继续'}
      tipTitle={meta.tipTitle}
      tip={meta.tip}
      onBack={handleBack}
      onContinue={() => void handleContinue()}
    >
      <p className="text-sm font-semibold text-primary-700">{meta.label}</p>
      <h1 className="mt-2 max-w-2xl text-3xl font-semibold leading-tight text-ink sm:text-4xl">
        {meta.title}
      </h1>

      {step === 1 && (
        <div className="mt-8 max-w-xl">
          <div className="mb-7 flex items-center gap-4">
            <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary-100 text-2xl font-semibold text-primary-700">
              {draft.avatar ? (
                <img src={draft.avatar} alt="头像预览" className="size-full object-cover" />
              ) : (
                draft.nickname.trim().charAt(0) || <UserRound aria-hidden="true" className="size-7" />
              )}
            </div>
            <label className="min-w-0 flex-1 text-sm font-medium text-ink" htmlFor="onboarding-avatar">
              头像链接 <span className="font-normal text-ink-muted">（可选）</span>
              <input
                id="onboarding-avatar"
                type="url"
                value={draft.avatar ?? ''}
                onChange={(event) => setDraft({ ...draft, avatar: event.target.value })}
                placeholder="https://"
                className="input-base mt-2"
              />
            </label>
          </div>
          <label htmlFor="onboarding-nickname" className="block text-sm font-medium text-ink">
            昵称
          </label>
          <input
            id="onboarding-nickname"
            value={draft.nickname}
            maxLength={40}
            autoComplete="nickname"
            autoFocus
            onChange={(event) => setDraft({ ...draft, nickname: event.target.value })}
            placeholder="例如：小紫"
            className="input-base mt-2 min-h-12 text-base"
          />
          <p className="mt-2 min-h-5 text-sm text-red-700" aria-live="polite">
            {draft.nickname.trim() ? '' : '请填写昵称'}
          </p>
        </div>
      )}

      {step === 2 && (
        <div className="mt-8 grid max-w-2xl gap-6 sm:grid-cols-2">
          <label htmlFor="onboarding-major" className="block text-sm font-medium text-ink">
            院系 / 专业
            <span className="relative mt-2 block">
              <GraduationCap aria-hidden="true" className="pointer-events-none absolute left-3 top-3.5 size-[18px] text-ink-muted" />
              <input
                id="onboarding-major"
                value={draft.major}
                maxLength={80}
                autoFocus
                onChange={(event) => setDraft({ ...draft, major: event.target.value })}
                placeholder="例如：软件学院"
                className="input-base min-h-12 pl-10 text-base"
              />
            </span>
          </label>
          <label htmlFor="onboarding-grade" className="block text-sm font-medium text-ink">
            年级
            <select
              id="onboarding-grade"
              value={draft.grade}
              onChange={(event) => setDraft({ ...draft, grade: event.target.value })}
              className="input-base mt-2 min-h-12 text-base"
            >
              <option value="">请选择</option>
              <option>本科一年级</option>
              <option>本科二年级</option>
              <option>本科三年级</option>
              <option>本科四年级</option>
              <option>硕士研究生</option>
              <option>博士研究生</option>
              <option>教职工</option>
            </select>
          </label>
          <p className="min-h-5 text-sm text-red-700 sm:col-span-2" aria-live="polite">
            {draft.major.trim() && draft.grade.trim() ? '' : '请填写专业并选择年级'}
          </p>
        </div>
      )}

      {step === 3 && (
        <div className="mt-8 max-w-2xl">
          <label htmlFor="interest-search" className="sr-only">搜索兴趣</label>
          <div className="relative">
            <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-3.5 size-[18px] text-ink-muted" />
            <input
              id="interest-search"
              type="search"
              value={interestQuery}
              onChange={(event) => setInterestQuery(event.target.value)}
              placeholder="搜索兴趣"
              className="input-base min-h-12 pl-10 text-base"
            />
          </div>
          <div className="mt-5 min-h-[190px]">
            <ChoiceChips
              label="兴趣方向"
              options={visibleInterests}
              selected={draft.interests}
              onChange={(interests) => setDraft({ ...draft, interests })}
            />
            {visibleInterests.length === 0 && (
              <p className="py-5 text-sm text-ink-muted">没有匹配的标准兴趣</p>
            )}
          </div>
          {!interestQuery && (
            <button
              type="button"
              onClick={() => setShowAllInterests((current) => !current)}
              className="mt-3 inline-flex min-h-10 items-center gap-1.5 text-sm font-semibold text-primary-700 hover:text-primary-800"
            >
              {showAllInterests ? '收起' : '更多选择'}
              {showAllInterests ? (
                <ChevronUp aria-hidden="true" className="size-4" />
              ) : (
                <ChevronDown aria-hidden="true" className="size-4" />
              )}
            </button>
          )}
          <p className="mt-2 min-h-5 text-sm text-ink-muted" aria-live="polite">
            已选择 {new Set(draft.interests.map((item) => item.trim()).filter(Boolean)).size} / 至少 3 个
          </p>
        </div>
      )}

      {step === 4 && (
        <div className="mt-8 max-w-2xl">
          <ChoiceChips
            label="参与目标"
            options={GOAL_OPTIONS}
            selected={draft.looking_for}
            onChange={(looking_for) => setDraft({ ...draft, looking_for })}
          />
          <p className="mt-4 min-h-5 text-sm text-ink-muted">可多选，也可以暂时跳过</p>
        </div>
      )}

      {step === 5 && (
        <div className="mt-8 max-w-2xl space-y-8">
          <div>
            <h2 className="font-sans text-sm font-semibold text-ink">你能带来的技能</h2>
            <div className="mt-3">
              <ChoiceChips
                label="技能"
                options={SKILL_OPTIONS}
                selected={draft.skills}
                onChange={(skills) => setDraft({ ...draft, skills })}
              />
            </div>
          </div>
          <div>
            <h2 className="font-sans text-sm font-semibold text-ink">常用空闲时段</h2>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {AVAILABILITY_OPTIONS.map((option) => (
                <label key={option} className="flex min-h-11 items-center gap-3 rounded-card border border-stone bg-paper px-3.5 py-2.5 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={draft.availability[option] === true}
                    onChange={(event) => setAvailability(option, event.target.checked)}
                    className="size-4 accent-primary-600"
                  />
                  {option}
                </label>
              ))}
            </div>
          </div>
          <label htmlFor="weekly-hours" className="block text-sm font-semibold text-ink">
            每周可投入时间
            <select
              id="weekly-hours"
              value={typeof draft.availability.weekly_hours === 'string' ? draft.availability.weekly_hours : ''}
              onChange={(event) => setDraft({
                ...draft,
                availability: { ...draft.availability, weekly_hours: event.target.value },
              })}
              className="input-base mt-2 min-h-11 font-normal"
            >
              <option value="">暂不填写</option>
              <option>每周 1-3 小时</option>
              <option>每周 4-6 小时</option>
              <option>每周 7-10 小时</option>
              <option>每周 10 小时以上</option>
            </select>
          </label>
        </div>
      )}

      {step === 6 && (
        <div className="mt-7 grid max-w-3xl gap-7 lg:grid-cols-[minmax(0,1fr)_240px]">
          <div className="min-w-0">
            <label htmlFor="onboarding-bio" className="block text-sm font-semibold text-ink">
              一句话介绍 <span className="font-normal text-ink-muted">（可选）</span>
            </label>
            <textarea
              id="onboarding-bio"
              value={draft.bio ?? ''}
              maxLength={500}
              rows={3}
              onChange={(event) => setDraft({ ...draft, bio: event.target.value })}
              placeholder="你在关注什么，又期待怎样的合作？"
              className="input-base mt-2 resize-none text-base"
            />
            <fieldset className="mt-6">
              <legend className="text-sm font-semibold text-ink">公开资料</legend>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {VISIBILITY_OPTIONS.map(([key, label]) => (
                  <label key={key} className="flex min-h-10 items-center gap-2.5 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={draft.profile_visibility[key] !== false}
                      onChange={(event) => setDraft({
                        ...draft,
                        profile_visibility: {
                          ...draft.profile_visibility,
                          [key]: event.target.checked,
                        },
                      })}
                      className="size-4 accent-primary-600"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>

          <section className="rounded-card border border-stone bg-paper p-4 shadow-panel" aria-label="公开资料预览">
            <div className="flex items-center justify-between gap-3">
              <div className="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary-100 font-semibold text-primary-700">
                {draft.avatar ? (
                  <img src={draft.avatar} alt="" className="size-full object-cover" />
                ) : (
                  draft.nickname.trim().charAt(0) || <UserRound aria-hidden="true" className="size-5" />
                )}
              </div>
              <Eye aria-hidden="true" className="size-[18px] text-primary-600" />
            </div>
            <h2 className="mt-3 break-words font-sans text-lg font-semibold text-ink">{draft.nickname || '你的昵称'}</h2>
            {(draft.profile_visibility.major !== false || draft.profile_visibility.grade !== false) && (
              <p className="mt-1 break-words text-sm text-ink-muted">
                {draft.profile_visibility.major !== false ? draft.major : ''}
                {draft.profile_visibility.major !== false && draft.profile_visibility.grade !== false ? ' · ' : ''}
                {draft.profile_visibility.grade !== false ? draft.grade : ''}
              </p>
            )}
            {draft.bio && <p className="mt-3 break-words text-sm leading-6 text-ink">{draft.bio}</p>}
            {draft.profile_visibility.interests !== false && draft.interests.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-1.5">
                {draft.interests.slice(0, 4).map((interest) => (
                  <span key={interest} className="rounded-card bg-primary-50 px-2 py-1 text-xs font-medium text-primary-800">
                    {interest}
                  </span>
                ))}
              </div>
            )}
            {draft.profile_visibility.skills !== false && draft.skills.length > 0 && (
              <p className="mt-4 break-words text-xs leading-5 text-ink-muted">技能：{draft.skills.slice(0, 3).join('、')}</p>
            )}
            {draft.profile_visibility.availability !== false && (
              <p className="mt-2 break-words text-xs leading-5 text-ink-muted">
                时间：{
                  [
                    ...AVAILABILITY_OPTIONS.filter((option) => draft.availability[option] === true),
                    typeof draft.availability.weekly_hours === 'string' ? draft.availability.weekly_hours : '',
                  ].filter(Boolean).join('、') || '暂未填写'
                }
              </p>
            )}
          </section>
        </div>
      )}
    </OnboardingShell>
  )
}
