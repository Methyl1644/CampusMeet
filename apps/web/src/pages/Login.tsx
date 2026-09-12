import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, Mail } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import { sendCode, register, login, resetPassword } from '@/api/auth'
import { getApiErrorMessage, getCodeSentMessage } from '@/api/auth-feedback'
import CampusMark from '@/components/CampusMark'
import { useToast } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import { COMMON_SKILLS } from '@shared/constants'
import type { User } from '@shared/types'

type Step = 'login' | 'register' | 'profile' | 'reset'

const STEP_INDEX: Record<Step, number> = {
  login: 0,
  register: 0,
  profile: 1,
  reset: 0,
}

const REGISTRATION_STEPS = ['校园账户', '完善资料']

const isNjuCampusEmail = (value: string) =>
  /^[^\s@]+@(?:smail\.)?nju\.edu\.cn$/i.test(value.trim())

const DEMO_USER: User = {
  id: 'local-demo-user',
  nickname: '前端演示用户',
  email: 'demo@nju.edu.cn',
  auth_status: 'verified',
  verified_email: 'demo@nju.edu.cn',
  major: '计算机科学与技术',
  grade: '大三',
  skills: ['产品设计', 'React', 'Python'],
  onboarding_step: 1,
  onboarding_completed: true,
  interests: [],
  looking_for: [],
  availability: {},
  profile_visibility: {},
  post_count: 0,
  team_count: 0,
}

const stageVariants = {
  enter: (direction: number) => ({ opacity: 0, x: direction * 14 }),
  center: { opacity: 1, x: 0 },
  exit: (direction: number) => ({ opacity: 0, x: direction * -10 }),
}

export default function Login() {
  const navigate = useNavigate()
  const shouldReduceMotion = useReducedMotion()
  const { setAuth } = useAuthStore()
  const { showToast } = useToast()

  const [step, setStep] = useState<Step>('login')
  const [stageDirection, setStageDirection] = useState(1)
  const [account, setAccount] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [codeCooldown, setCodeCooldown] = useState(0)
  const [sendingCode, setSendingCode] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const primaryCodeRequestGeneration = useRef(0)
  const primaryAuthPurpose = useRef<'login' | 'register'>('login')
  const resetCodeRequestGeneration = useRef(0)

  const [nickname, setNickname] = useState('')
  const [major, setMajor] = useState('')
  const [grade, setGrade] = useState('')
  const [skills, setSkills] = useState<string[]>([])

  useEffect(() => {
    if (codeCooldown <= 0) return
    const timer = window.setTimeout(() => {
      setCodeCooldown((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [codeCooldown])

  const goToStep = (nextStep: Step) => {
    const nextIndex = STEP_INDEX[nextStep]
    const currentIndex = STEP_INDEX[step]
    const switchingAuthPurpose =
      (step === 'login' && nextStep === 'register') ||
      (step === 'register' && nextStep === 'login')
    const leavingPrimaryAuth =
      (step === 'login' || step === 'register') && nextStep === 'reset'
    const leavingReset = step === 'reset' && nextStep !== 'reset'

    if (nextStep === 'login' || nextStep === 'register') {
      primaryAuthPurpose.current = nextStep
    }

    if (switchingAuthPurpose || leavingPrimaryAuth) {
      primaryCodeRequestGeneration.current += 1
      setCode('')
      setCodeCooldown(0)
      setSendingCode(false)
    }

    if (leavingReset) {
      resetCodeRequestGeneration.current += 1
      setCode('')
      setCodeCooldown(0)
      setSendingCode(false)
      setNewPassword('')
      setConfirmPassword('')
    }

    setStageDirection(
      nextIndex === currentIndex
        ? nextStep === 'login'
          ? -1
          : 1
        : nextIndex > currentIndex
          ? 1
          : -1,
    )
    setStep(nextStep)
  }

  const validateRegistrationAccount = () => {
    if (!isNjuCampusEmail(account)) {
      showToast('仅支持南京大学学生或教职工邮箱注册', 'error')
      return false
    }
    if (!account || !code || !password) {
      showToast('请填写校园邮箱、验证码和密码', 'error')
      return false
    }
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      showToast('密码至少 8 位，并同时包含字母和数字', 'error')
      return false
    }
    return true
  }

  const handleSendCode = async () => {
    if (!isNjuCampusEmail(account)) {
      showToast('请输入南京大学学生或教职工邮箱', 'error')
      return
    }
    const requestPurpose = 'register'
    const requestGeneration = ++primaryCodeRequestGeneration.current
    primaryAuthPurpose.current = requestPurpose
    const requestIsCurrent = () =>
      primaryCodeRequestGeneration.current === requestGeneration &&
      primaryAuthPurpose.current === requestPurpose

    setSendingCode(true)
    try {
      const result = await sendCode(account, requestPurpose)
      if (!requestIsCurrent()) return
      setCodeCooldown(result.retry_after_seconds ?? 60)
      showToast(getCodeSentMessage(result), 'success')
    } catch (error) {
      if (!requestIsCurrent()) return
      showToast(getApiErrorMessage(error, '验证码发送失败，请稍后重试'), 'error')
    } finally {
      if (requestIsCurrent()) setSendingCode(false)
    }
  }

  const handleLogin = async () => {
    if (!isNjuCampusEmail(account)) {
      showToast('请输入南京大学学生或教职工邮箱', 'error')
      return
    }
    if (!password) {
      showToast('请输入密码', 'error')
      return
    }
    setSubmitting(true)
    try {
      const res = await login({ account, password })
      setAuth(res.token, res.user)
      showToast('登录成功', 'success')
      navigate('/home')
    } catch (error) {
      showToast(getApiErrorMessage(error, '登录失败，请检查账号和密码'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSendResetCode = async () => {
    if (!isNjuCampusEmail(account)) {
      showToast('请输入注册时使用的南京大学邮箱', 'error')
      return
    }
    const requestGeneration = ++resetCodeRequestGeneration.current
    setSendingCode(true)
    try {
      const result = await sendCode(account, 'reset_password')
      if (resetCodeRequestGeneration.current !== requestGeneration) return
      setCodeCooldown(result.retry_after_seconds ?? 60)
      showToast(getCodeSentMessage(result), 'success')
    } catch (error) {
      if (resetCodeRequestGeneration.current !== requestGeneration) return
      showToast(getApiErrorMessage(error, '重置验证码发送失败，请稍后重试'), 'error')
    } finally {
      if (resetCodeRequestGeneration.current === requestGeneration) setSendingCode(false)
    }
  }

  const handleResetPassword = async () => {
    if (!isNjuCampusEmail(account)) {
      showToast('请输入注册时使用的南京大学邮箱', 'error')
      return
    }
    if (!code || !newPassword || !confirmPassword) {
      showToast('请填写验证码和两次新密码', 'error')
      return
    }
    if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
      showToast('密码至少 8 位，并同时包含字母和数字', 'error')
      return
    }
    if (newPassword !== confirmPassword) {
      showToast('两次输入的新密码不一致', 'error')
      return
    }

    setSubmitting(true)
    try {
      await resetPassword({ account, code, new_password: newPassword })
      showToast('密码已重置，请使用新密码登录', 'success')
      setPassword('')
      goToStep('login')
    } catch (error) {
      showToast(getApiErrorMessage(error, '密码重置失败，请检查验证码'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRegister = async () => {
    if (!validateRegistrationAccount()) return
    setSubmitting(true)
    try {
      const res = await register({ account, code, password })
      setAuth(res.token, res.user)
      showToast('注册成功', 'success')
      navigate('/home')
    } catch (error) {
      showToast(getApiErrorMessage(error, '注册失败，请稍后重试'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDemoEnter = () => {
    setAuth('local-demo-token', DEMO_USER)
    navigate('/home')
  }

  const toggleSkill = (skill: string) => {
    setSkills((prev) =>
      prev.includes(skill) ? prev.filter((item) => item !== skill) : [...prev, skill],
    )
  }

  const registrationStage = STEP_INDEX[step]

  return (
    <main className="min-h-dvh bg-paper-warm lg:grid lg:grid-cols-[minmax(20rem,0.9fr)_minmax(32rem,1.1fr)]">
      <section className="relative hidden min-h-dvh overflow-hidden border-r border-primary-950/20 bg-primary-800 p-10 text-white lg:flex lg:flex-col lg:justify-between xl:p-14">
        <div className="w-fit rounded-card bg-paper px-4 py-3 shadow-panel">
          <CampusMark />
        </div>
        <div className="max-w-lg border-l-2 border-campus-gold pl-7">
          <p className="mb-4 text-xs font-semibold text-primary-100">NANJING UNIVERSITY</p>
          <h1 className="font-serif text-5xl font-semibold leading-tight xl:text-6xl">CampusMate</h1>
        </div>
        <div className="flex items-center justify-between border-t border-white/20 pt-5 text-xs text-primary-100">
          <span>南京大学校园组队</span>
          <span className="text-campus-gold">诚朴雄伟 · 励学敦行</span>
        </div>
      </section>

      <section className="flex min-h-dvh items-center justify-center px-4 py-8 sm:px-8 lg:px-12">
        <div className="w-full max-w-lg">
          <div className="mb-7 flex items-center gap-3 lg:hidden">
            <CampusMark compact />
            <div className="min-w-0">
              <p className="truncate font-serif text-lg font-semibold text-ink">CampusMate</p>
              <p className="truncate text-xs text-ink-muted">南京大学校园组队</p>
            </div>
          </div>

          <div className="mb-7 border-b border-stone pb-5">
            <p className="section-label mb-3">
              {step === 'reset'
                ? '找回账号'
                : step === 'login'
                  ? '校园账户'
                  : `注册进度 ${registrationStage + 1} / ${REGISTRATION_STEPS.length}`}
            </p>
            <h2 className="text-2xl font-semibold text-ink sm:text-3xl">
              {step === 'login' && '欢迎回来'}
              {step === 'register' && '创建账号'}
              {step === 'profile' && '完善个人资料'}
              {step === 'reset' && '重置密码'}
            </h2>
          </div>

          {(step === 'login' || step === 'register') && (
            <div
              className="mb-6 grid grid-cols-2 rounded-card border border-stone bg-primary-50 p-1"
              role="tablist"
              aria-label="登录或注册"
            >
              <button
                type="button"
                role="tab"
                aria-selected={step === 'login'}
                onClick={() => goToStep('login')}
                className={`min-h-10 rounded-md px-3 text-sm font-semibold transition-colors ${
                  step === 'login' ? 'bg-paper text-primary-700 shadow-panel' : 'text-ink-muted'
                }`}
              >
                登录
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={step === 'register'}
                onClick={() => goToStep('register')}
                className={`min-h-10 rounded-md px-3 text-sm font-semibold transition-colors ${
                  step === 'register' ? 'bg-paper text-primary-700 shadow-panel' : 'text-ink-muted'
                }`}
              >
                注册
              </button>
            </div>
          )}

          <AnimatePresence mode="wait" initial={false} custom={stageDirection}>
            <motion.section
              key={step}
              custom={stageDirection}
              variants={stageVariants}
              initial={shouldReduceMotion ? false : 'enter'}
              animate="center"
              exit={shouldReduceMotion ? undefined : 'exit'}
              transition={{
                duration: shouldReduceMotion ? 0 : 0.22,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {(step === 'login' || step === 'register') && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="auth-account" className="mb-1.5 block text-sm font-medium text-ink">
                      南京大学邮箱
                    </label>
                    <div className="relative">
                      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted">
                        <Mail size={16} />
                      </span>
                      <input
                        id="auth-account"
                        type="email"
                        value={account}
                        onChange={(event) => setAccount(event.target.value)}
                        autoComplete="email"
                        placeholder="学号@smail.nju.edu.cn"
                        className="input-base min-w-0 pl-9"
                      />
                    </div>
                  </div>

                  {step === 'register' && (
                    <div>
                      <label htmlFor="auth-code" className="mb-1.5 block text-sm font-medium text-ink">
                        验证码
                      </label>
                      <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                        <input
                          id="auth-code"
                          type="text"
                          inputMode="numeric"
                          value={code}
                          onChange={(event) => setCode(event.target.value)}
                          autoComplete="one-time-code"
                          className="input-base min-w-0"
                        />
                        <button
                          type="button"
                          onClick={handleSendCode}
                          disabled={sendingCode || codeCooldown > 0}
                          className="btn-secondary min-w-[6.5rem] whitespace-nowrap px-3"
                        >
                          {sendingCode
                            ? '发送中...'
                            : codeCooldown > 0
                              ? `${codeCooldown}s 后重发`
                              : '获取验证码'}
                        </button>
                      </div>
                    </div>
                  )}

                  <div>
                    <div className="mb-1.5 flex items-center justify-between gap-3">
                      <label htmlFor="auth-password" className="block text-sm font-medium text-ink">
                        {step === 'login' ? '密码' : '设置密码'}
                      </label>
                      {step === 'login' && (
                        <button
                          type="button"
                          onClick={() => goToStep('reset')}
                          className="text-xs font-semibold text-primary-700 transition-colors hover:text-primary-900"
                        >
                          忘记密码？
                        </button>
                      )}
                    </div>
                    <input
                      id="auth-password"
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      autoComplete={step === 'login' ? 'current-password' : 'new-password'}
                      className="input-base"
                    />
                  </div>

                  <button
                    type="button"
                    onClick={
                      step === 'login'
                        ? handleLogin
                        : () => validateRegistrationAccount() && goToStep('profile')
                    }
                    disabled={submitting}
                    className="btn-primary min-h-11 w-full"
                  >
                    {submitting ? '处理中...' : step === 'login' ? '登录' : '继续完善资料'}
                    <ArrowRight size={16} />
                  </button>

                  {import.meta.env.DEV && step === 'login' && (
                    <div className="border-t border-stone pt-4">
                      <button type="button" onClick={handleDemoEnter} className="btn-secondary w-full">
                        进入前端演示
                      </button>
                    </div>
                  )}
                </div>
              )}

              {step === 'reset' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="reset-account" className="mb-1.5 block text-sm font-medium text-ink">
                      南京大学邮箱
                    </label>
                    <div className="relative">
                      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted">
                        <Mail aria-hidden="true" size={16} />
                      </span>
                      <input
                        id="reset-account"
                        type="email"
                        value={account}
                        onChange={(event) => setAccount(event.target.value)}
                        autoComplete="email"
                        placeholder="学号@smail.nju.edu.cn"
                        className="input-base min-w-0 pl-9"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="reset-code" className="mb-1.5 block text-sm font-medium text-ink">
                      邮箱验证码
                    </label>
                    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                      <input
                        id="reset-code"
                        type="text"
                        inputMode="numeric"
                        value={code}
                        onChange={(event) => setCode(event.target.value)}
                        autoComplete="one-time-code"
                        className="input-base min-w-0"
                      />
                      <button
                        type="button"
                        onClick={handleSendResetCode}
                        disabled={sendingCode || codeCooldown > 0}
                        className="btn-secondary min-w-[6.5rem] whitespace-nowrap px-3"
                      >
                        {sendingCode
                          ? '发送中...'
                          : codeCooldown > 0
                            ? `${codeCooldown}s 后重发`
                            : '获取验证码'}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="reset-password" className="mb-1.5 block text-sm font-medium text-ink">
                      新密码
                    </label>
                    <input
                      id="reset-password"
                      type="password"
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                      autoComplete="new-password"
                      className="input-base"
                    />
                    <p className="mt-1.5 text-xs text-ink-muted">至少 8 位，同时包含字母和数字</p>
                  </div>

                  <div>
                    <label htmlFor="reset-password-confirm" className="mb-1.5 block text-sm font-medium text-ink">
                      再次输入新密码
                    </label>
                    <input
                      id="reset-password-confirm"
                      type="password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      autoComplete="new-password"
                      className="input-base"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <button
                      type="button"
                      onClick={() => goToStep('login')}
                      className="btn-secondary min-h-11"
                    >
                      <ArrowLeft aria-hidden="true" size={16} />
                      返回登录
                    </button>
                    <button
                      type="button"
                      onClick={handleResetPassword}
                      disabled={submitting}
                      className="btn-primary min-h-11"
                    >
                      {submitting ? '处理中...' : '重置密码'}
                      <ArrowRight aria-hidden="true" size={16} />
                    </button>
                  </div>
                </div>
              )}

              {step === 'profile' && (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="nickname" className="mb-1.5 block text-sm font-medium text-ink">
                      昵称
                    </label>
                    <input
                      id="nickname"
                      type="text"
                      value={nickname}
                      onChange={(event) => setNickname(event.target.value)}
                      autoComplete="nickname"
                      className="input-base"
                    />
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                      <label htmlFor="major" className="mb-1.5 block text-sm font-medium text-ink">
                        专业
                      </label>
                      <input
                        id="major"
                        type="text"
                        value={major}
                        onChange={(event) => setMajor(event.target.value)}
                        autoComplete="off"
                        className="input-base"
                      />
                    </div>
                    <div>
                      <label htmlFor="grade" className="mb-1.5 block text-sm font-medium text-ink">
                        年级
                      </label>
                      <select
                        id="grade"
                        value={grade}
                        onChange={(event) => setGrade(event.target.value)}
                        className="input-base"
                      >
                        <option value="">选择年级</option>
                        <option value="大一">大一</option>
                        <option value="大二">大二</option>
                        <option value="大三">大三</option>
                        <option value="大四">大四</option>
                        <option value="研一">研一</option>
                        <option value="研二">研二</option>
                        <option value="博士">博士</option>
                      </select>
                    </div>
                  </div>
                  <fieldset>
                    <legend className="mb-2 text-sm font-medium text-ink">技能标签</legend>
                    <div className="flex flex-wrap gap-2">
                      {COMMON_SKILLS.map((skill) => (
                        <button
                          key={skill}
                          type="button"
                          aria-pressed={skills.includes(skill)}
                          onClick={() => toggleSkill(skill)}
                          className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                            skills.includes(skill)
                              ? 'border-primary-500 bg-primary-50 text-primary-700'
                              : 'border-stone bg-paper text-ink-muted'
                          }`}
                        >
                          {skill}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <button
                      type="button"
                      onClick={() => goToStep('register')}
                      className="btn-secondary min-h-11"
                    >
                      <ArrowLeft size={16} />
                      上一步
                    </button>
                    <button
                      type="button"
                      onClick={handleRegister}
                      disabled={submitting}
                      className="btn-primary min-h-11"
                    >
                      {submitting ? '处理中...' : '注册'}
                      <ArrowRight size={16} />
                    </button>
                  </div>
                </div>
              )}

              {(step === 'register' || step === 'profile') && (
                <nav className="mt-8 border-t border-stone pt-5" aria-label="注册进度">
                  <ol className="grid grid-cols-2">
                    {REGISTRATION_STEPS.map((label, index) => {
                      const reached = index <= registrationStage
                      return (
                        <li key={label} className="relative min-w-0 pt-4 text-center">
                          <span
                            className={`absolute left-0 right-0 top-1.5 h-0.5 ${
                              index <= registrationStage ? 'bg-primary-600' : 'bg-stone'
                            } ${index === 0 ? 'left-1/2' : ''} ${
                              index === REGISTRATION_STEPS.length - 1 ? 'right-1/2' : ''
                            }`}
                          />
                          <span
                            className={`absolute left-1/2 top-0 size-3 -translate-x-1/2 rounded-full border-2 ${
                              reached ? 'border-primary-600 bg-primary-600' : 'border-stone bg-paper'
                            }`}
                          />
                          <span
                            className={`block truncate px-1 text-[11px] ${
                              reached ? 'font-semibold text-primary-700' : 'text-ink-muted'
                            }`}
                          >
                            {label}
                          </span>
                        </li>
                      )
                    })}
                  </ol>
                </nav>
              )}
            </motion.section>
          </AnimatePresence>

        </div>
      </section>
    </main>
  )
}
