import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, Mail } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import { sendCode, register, login, resetPassword } from '@/api/auth'
import { getApiErrorMessage, getCodeSentMessage } from '@/api/auth-feedback'
import CampusMark from '@/components/CampusMark'
import { useToast } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import {
  createAuthRequestTracker,
  passwordForMode,
  successfulAuthNavigation,
  type AuthMode,
} from './authFlow'

type Step = AuthMode

const isNjuCampusEmail = (value: string) =>
  /^[^\s@]+@(?:smail\.)?nju\.edu\.cn$/i.test(value.trim())

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
  const [loginPassword, setLoginPassword] = useState('')
  const [registrationPassword, setRegistrationPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [codeCooldown, setCodeCooldown] = useState(0)
  const [sendingCode, setSendingCode] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const registrationCodeRequestGeneration = useRef(0)
  const resetCodeRequestGeneration = useRef(0)
  const [authRequestTracker] = useState(() => createAuthRequestTracker('login'))

  useEffect(() => {
    if (codeCooldown <= 0) return
    const timer = window.setTimeout(() => {
      setCodeCooldown((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearTimeout(timer)
  }, [codeCooldown])

  const goToStep = (nextStep: Step) => {
    const switchingMode = step !== nextStep
    const leavingRegistration = step === 'register' && nextStep !== 'register'
    const leavingReset = step === 'reset' && nextStep !== 'reset'

    if (switchingMode) {
      authRequestTracker.switchMode(nextStep)
      setSubmitting(false)
      setLoginPassword((current) => passwordForMode(current, 'login', nextStep))
      setRegistrationPassword((current) => passwordForMode(current, 'register', nextStep))
      setNewPassword((current) => passwordForMode(current, 'reset', nextStep))
      setConfirmPassword((current) => passwordForMode(current, 'reset', nextStep))
    }

    if (leavingRegistration) {
      registrationCodeRequestGeneration.current += 1
      setCode('')
      setCodeCooldown(0)
      setSendingCode(false)
    }

    if (leavingReset) {
      resetCodeRequestGeneration.current += 1
      setCode('')
      setCodeCooldown(0)
      setSendingCode(false)
    }

    setStageDirection(nextStep === 'login' ? -1 : 1)
    setStep(nextStep)
  }

  const validateRegistrationAccount = () => {
    if (!isNjuCampusEmail(account)) {
      showToast('仅支持南京大学学生或教职工邮箱注册', 'error')
      return false
    }
    if (!account || !code || !registrationPassword) {
      showToast('请填写校园邮箱、验证码和密码', 'error')
      return false
    }
    if (
      registrationPassword.length < 8 ||
      !/[A-Za-z]/.test(registrationPassword) ||
      !/\d/.test(registrationPassword)
    ) {
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
    const requestGeneration = ++registrationCodeRequestGeneration.current
    const requestIsCurrent = () =>
      registrationCodeRequestGeneration.current === requestGeneration

    setSendingCode(true)
    try {
      const result = await sendCode(account, 'register')
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
    if (!loginPassword) {
      showToast('请输入密码', 'error')
      return
    }
    const request = authRequestTracker.begin()
    setSubmitting(true)
    try {
      const res = await login({ account, password: loginPassword })
      authRequestTracker.commit(request, () => {
        setAuth(res.token, res.user)
        showToast('登录成功', 'success')
        const navigation = successfulAuthNavigation(res.user)
        navigate(navigation.to, { replace: navigation.replace })
      })
    } catch (error) {
      authRequestTracker.commit(request, () => {
        showToast(getApiErrorMessage(error, '登录失败，请检查账号和密码'), 'error')
      })
    } finally {
      authRequestTracker.commit(request, () => setSubmitting(false))
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

    const request = authRequestTracker.begin()
    setSubmitting(true)
    try {
      await resetPassword({ account, code, new_password: newPassword })
      authRequestTracker.commit(request, () => {
        showToast('密码已重置，请使用新密码登录', 'success')
        setLoginPassword('')
        goToStep('login')
      })
    } catch (error) {
      authRequestTracker.commit(request, () => {
        showToast(getApiErrorMessage(error, '密码重置失败，请检查验证码'), 'error')
      })
    } finally {
      authRequestTracker.commit(request, () => setSubmitting(false))
    }
  }

  const handleRegister = async () => {
    if (!validateRegistrationAccount()) return
    const request = authRequestTracker.begin()
    setSubmitting(true)
    try {
      const res = await register({ account, code, password: registrationPassword })
      authRequestTracker.commit(request, () => {
        setAuth(res.token, res.user)
        showToast('注册成功', 'success')
        const navigation = successfulAuthNavigation(res.user)
        navigate(navigation.to, { replace: navigation.replace })
      })
    } catch (error) {
      authRequestTracker.commit(request, () => {
        showToast(getApiErrorMessage(error, '注册失败，请稍后重试'), 'error')
      })
    } finally {
      authRequestTracker.commit(request, () => setSubmitting(false))
    }
  }

  return (
    <main className="min-h-dvh bg-paper-warm lg:grid lg:grid-cols-[minmax(20rem,0.9fr)_minmax(32rem,1.1fr)]">
      <section className="relative hidden min-h-dvh overflow-hidden border-r border-primary-950/20 bg-primary-800 p-10 text-white lg:flex lg:flex-col lg:justify-between xl:p-14">
        <div className="w-fit rounded-card bg-paper px-4 py-3 shadow-panel">
          <CampusMark />
        </div>
        <div className="max-w-lg border-l-2 border-campus-gold pl-7">
          <p className="mb-4 text-xs font-semibold text-primary-100">NANJING UNIVERSITY</p>
          <h1 className="font-serif text-5xl font-semibold leading-tight xl:text-6xl">梧桐遇</h1>
          <p className="mt-2 text-xl font-semibold text-primary-100">CampusMeet</p>
        </div>
        <div className="flex items-center justify-between border-t border-white/20 pt-5 text-xs text-primary-100">
          <span>在校园，遇见同行的人</span>
          <span className="text-campus-gold">诚朴雄伟 · 励学敦行</span>
        </div>
      </section>

      <section className="flex min-h-dvh items-center justify-center px-4 py-8 sm:px-8 lg:px-12">
        <div className="w-full max-w-lg">
          <div className="mb-7 flex items-center gap-3 lg:hidden">
            <CampusMark compact />
            <div className="min-w-0">
              <p className="truncate font-serif text-lg font-semibold text-ink">梧桐遇</p>
              <p className="truncate text-xs font-semibold text-campus-green">CampusMeet</p>
            </div>
          </div>

          <div className="mb-7 border-b border-stone pb-5">
            <p className="section-label mb-3">
              {step === 'reset' ? '找回账号' : '校园账户'}
            </p>
            <h2 className="text-2xl font-semibold text-ink sm:text-3xl">
              {step === 'login' && '欢迎回来'}
              {step === 'register' && '创建账号'}
              {step === 'reset' && '重置密码'}
            </h2>
          </div>

          {(step === 'login' || step === 'register') && (
            <div
              className="mb-6 grid grid-cols-2 rounded-card border border-stone bg-primary-50 p-1"
            >
              <button
                type="button"
                aria-pressed={step === 'login'}
                onClick={() => goToStep('login')}
                className={`min-h-10 rounded-md px-3 text-sm font-semibold transition-colors ${
                  step === 'login' ? 'bg-paper text-primary-700 shadow-panel' : 'text-ink-muted'
                }`}
              >
                登录
              </button>
              <button
                type="button"
                aria-pressed={step === 'register'}
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
                <form
                  className="space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault()
                    void (step === 'login' ? handleLogin() : handleRegister())
                  }}
                >
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
                      <p className="mt-1.5 text-xs text-ink-muted">长时间未收到邮箱验证码请翻阅邮件垃圾箱</p>
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
                      value={step === 'login' ? loginPassword : registrationPassword}
                      onChange={(event) => {
                        if (step === 'login') setLoginPassword(event.target.value)
                        else setRegistrationPassword(event.target.value)
                      }}
                      autoComplete={step === 'login' ? 'current-password' : 'new-password'}
                      className="input-base"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={submitting}
                    className="btn-primary min-h-11 w-full"
                  >
                    {submitting ? '处理中...' : step === 'login' ? '登录' : '注册并继续'}
                    <ArrowRight size={16} />
                  </button>
                </form>
              )}

              {step === 'reset' && (
                <form
                  className="space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault()
                    void handleResetPassword()
                  }}
                >
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
                      type="submit"
                      disabled={submitting}
                      className="btn-primary min-h-11"
                    >
                      {submitting ? '处理中...' : '重置密码'}
                      <ArrowRight aria-hidden="true" size={16} />
                    </button>
                  </div>
                </form>
              )}

            </motion.section>
          </AnimatePresence>

        </div>
      </section>
    </main>
  )
}
