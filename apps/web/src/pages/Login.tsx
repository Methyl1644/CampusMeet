import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, Mail, Phone, Shield } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import { sendCode, register, login, verifyEmail } from '@/api/auth'
import { getApiErrorMessage, getCodeSentMessage } from '@/api/auth-feedback'
import CampusMark from '@/components/CampusMark'
import { useToast } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import { COMMON_SKILLS } from '@shared/constants'
import type { User } from '@shared/types'

type Step = 'login' | 'register' | 'profile' | 'verify'

const STEP_INDEX: Record<Step, number> = {
  login: 0,
  register: 0,
  profile: 1,
  verify: 2,
}

const REGISTRATION_STEPS = ['创建账号', '完善资料', '校园认证']

const DEMO_USER: User = {
  id: 'local-demo-user',
  nickname: '前端演示用户',
  email: 'demo@nju.edu.cn',
  auth_status: 'verified',
  verified_email: 'demo@nju.edu.cn',
  major: '计算机科学与技术',
  grade: '大三',
  skills: ['产品设计', 'React', 'Python'],
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
  const { setAuth, user, updateUser } = useAuthStore()
  const { showToast } = useToast()

  const [step, setStep] = useState<Step>('login')
  const [stageDirection, setStageDirection] = useState(1)
  const [account, setAccount] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [codeCooldown, setCodeCooldown] = useState(0)
  const [sendingCode, setSendingCode] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const primaryCodeRequestGeneration = useRef(0)
  const primaryAuthPurpose = useRef<'login' | 'register'>('login')

  const [nickname, setNickname] = useState('')
  const [major, setMajor] = useState('')
  const [grade, setGrade] = useState('')
  const [skills, setSkills] = useState<string[]>([])

  const [verifyEmailAddr, setVerifyEmailAddr] = useState('')
  const [verifyCode, setVerifyCode] = useState('')
  const [verifyCodeCooldown, setVerifyCodeCooldown] = useState(0)

  const isPhone = /^1\d{10}$/.test(account)
  const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account)

  useEffect(() => {
    if (codeCooldown <= 0) return
    const timer = window.setTimeout(() => {
      setCodeCooldown((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [codeCooldown])

  useEffect(() => {
    if (verifyCodeCooldown <= 0) return
    const timer = window.setTimeout(() => {
      setVerifyCodeCooldown((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [verifyCodeCooldown])

  const goToStep = (nextStep: Step) => {
    const nextIndex = STEP_INDEX[nextStep]
    const currentIndex = STEP_INDEX[step]
    const switchingAuthPurpose =
      (step === 'login' && nextStep === 'register') ||
      (step === 'register' && nextStep === 'login')

    if (nextStep === 'login' || nextStep === 'register') {
      primaryAuthPurpose.current = nextStep
    }

    if (switchingAuthPurpose) {
      primaryCodeRequestGeneration.current += 1
      setCode('')
      setCodeCooldown(0)
      setSendingCode(false)
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
    if (!account || !code || !password) {
      showToast('请填写账号、验证码和密码', 'error')
      return false
    }
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      showToast('密码至少 8 位，并同时包含字母和数字', 'error')
      return false
    }
    return true
  }

  const handleSendCode = async () => {
    if (!isPhone && !isEmail) {
      showToast('请输入正确的手机号或邮箱', 'error')
      return
    }
    const requestPurpose = step === 'login' ? 'login' : 'register'
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
    if (!account) {
      showToast('请输入手机号或邮箱', 'error')
      return
    }
    setSubmitting(true)
    try {
      const res = await login({ account, code: code || undefined, password: password || undefined })
      setAuth(res.token, res.user)
      showToast('登录成功', 'success')
      navigate('/home')
    } catch (error) {
      showToast(getApiErrorMessage(error, '登录失败，请检查账号和验证码'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRegister = async () => {
    if (!validateRegistrationAccount()) return
    setSubmitting(true)
    try {
      const res = await register({ account, code, password, nickname, major, grade, skills })
      setAuth(res.token, res.user)
      showToast('注册成功', 'success')
      goToStep('verify')
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

  const handleVerifyEmail = async () => {
    if (!verifyEmailAddr || !verifyCode) {
      showToast('请填写邮箱和验证码', 'error')
      return
    }
    setSubmitting(true)
    try {
      await verifyEmail(verifyEmailAddr, verifyCode)
      updateUser({ auth_status: 'verified', verified_email: verifyEmailAddr })
      showToast('校园邮箱认证成功', 'success')
      navigate('/home')
    } catch (error) {
      showToast(getApiErrorMessage(error, '认证失败，请检查邮箱和验证码'), 'error')
    } finally {
      setSubmitting(false)
    }
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
          <p className="mb-4 text-xs font-semibold text-primary-100">CAMPUS PUBLICATION · NJU</p>
          <h1 className="font-serif text-4xl font-semibold leading-tight xl:text-5xl">
            在校园里，找到一起把事情做成的人
          </h1>
          <p className="mt-5 max-w-md text-sm leading-7 text-primary-100">
            从赛事组队到同学邀约，清楚地说明目标、角色与时间，让每一次协作都有可靠的开始。
          </p>
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
              {step === 'login' ? '校园账户' : `注册进度 ${registrationStage + 1} / 3`}
            </p>
            <h2 className="text-2xl font-semibold text-ink sm:text-3xl">
              {step === 'login' && '欢迎回来'}
              {step === 'register' && '创建账号'}
              {step === 'profile' && '完善个人资料'}
              {step === 'verify' && '完成校园邮箱认证'}
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              {step === 'login' && '登录后直接进入校园组队信息页面。'}
              {step === 'register' && '手机号或常用邮箱用于登录，验证码与密码均需填写。'}
              {step === 'profile' && '昵称用于站内展示，其他资料可以稍后继续补充。'}
              {step === 'verify' && '认证后即可发帖和申请加入队伍。'}
            </p>
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
                      手机号 / 邮箱
                    </label>
                    <div className="relative">
                      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted">
                        {isEmail ? <Mail size={16} /> : <Phone size={16} />}
                      </span>
                      <input
                        id="auth-account"
                        type="text"
                        value={account}
                        onChange={(event) => setAccount(event.target.value)}
                        placeholder="输入手机号或邮箱"
                        autoComplete="username"
                        className="input-base min-w-0 pl-9"
                      />
                    </div>
                  </div>

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
                        placeholder="输入验证码"
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

                  <div>
                    <label htmlFor="auth-password" className="mb-1.5 block text-sm font-medium text-ink">
                      {step === 'login' ? '密码' : '设置密码'}
                      <span className="ml-1 font-normal text-ink-muted">
                        {step === 'login' ? '（验证码登录可留空）' : '（至少 8 位，含字母和数字）'}
                      </span>
                    </label>
                    <input
                      id="auth-password"
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder={step === 'login' ? '输入密码（可选）' : '设置登录密码'}
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
                      <p className="mt-2 text-center text-xs text-ink-muted">
                        仅用于本地界面预览，不连接真实账户
                      </p>
                    </div>
                  )}
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
                      placeholder="给自己取个昵称"
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
                        placeholder="如：计算机"
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

              {step === 'verify' && (
                <div className="space-y-4">
                  <div className="flex items-start gap-3 border-l-2 border-campus-green bg-green-50 px-4 py-3 text-sm text-campus-green">
                    <Shield size={18} className="mt-0.5 shrink-0" />
                    <p className="leading-6">
                      欢迎，{user?.nickname}！完成校园邮箱认证后即可发帖和申请加入队伍。
                    </p>
                  </div>
                  <div>
                    <label htmlFor="verify-email" className="mb-1.5 block text-sm font-medium text-ink">
                      校园邮箱
                    </label>
                    <input
                      id="verify-email"
                      type="email"
                      value={verifyEmailAddr}
                      onChange={(event) => setVerifyEmailAddr(event.target.value)}
                      placeholder="如：xxx@nju.edu.cn"
                      autoComplete="email"
                      className="input-base"
                    />
                  </div>
                  <div>
                    <label htmlFor="verify-code" className="mb-1.5 block text-sm font-medium text-ink">
                      验证码
                    </label>
                    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                      <input
                        id="verify-code"
                        type="text"
                        inputMode="numeric"
                        value={verifyCode}
                        onChange={(event) => setVerifyCode(event.target.value)}
                        placeholder="输入邮箱验证码"
                        autoComplete="one-time-code"
                        className="input-base min-w-0"
                      />
                      <button
                        type="button"
                        onClick={async () => {
                          if (!verifyEmailAddr) return showToast('请先填写邮箱', 'error')
                          try {
                            const result = await sendCode(verifyEmailAddr, 'campus_verify')
                            setVerifyCodeCooldown(result.retry_after_seconds ?? 60)
                            showToast(getCodeSentMessage(result), 'success')
                          } catch (error) {
                            showToast(getApiErrorMessage(error, '发送失败'), 'error')
                          }
                        }}
                        disabled={verifyCodeCooldown > 0}
                        className="btn-secondary min-w-[5rem] whitespace-nowrap px-3"
                      >
                        {verifyCodeCooldown > 0 ? `${verifyCodeCooldown}s` : '获取'}
                      </button>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleVerifyEmail}
                    disabled={submitting}
                    className="btn-primary min-h-11 w-full"
                  >
                    {submitting ? '认证中...' : '完成认证'}
                  </button>
                  <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => goToStep('profile')}
                      className="btn-secondary"
                    >
                      <ArrowLeft size={16} />
                      上一步
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate('/home')}
                      className="min-h-10 text-center text-ink-muted transition-colors hover:text-primary-700"
                    >
                      稍后再认证，先逛逛
                    </button>
                  </div>
                </div>
              )}

              {step !== 'login' && (
                <nav className="mt-8 border-t border-stone pt-5" aria-label="注册进度">
                  <ol className="grid grid-cols-3">
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

          <p className="mt-6 text-center text-xs leading-5 text-ink-muted">
            首期限南京大学校内使用 · 认证后可发帖和申请
          </p>
        </div>
      </section>
    </main>
  )
}
