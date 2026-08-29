import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, Phone, Shield, ArrowRight } from 'lucide-react'
import { sendCode, register, login, verifyEmail } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import { useToast } from '@/components/Toast'
import { COMMON_SKILLS } from '@shared/constants'

type Step = 'login' | 'register' | 'profile' | 'verify'

export default function Login() {
  const navigate = useNavigate()
  const { setAuth, user, updateUser } = useAuthStore()
  const { showToast } = useToast()

  const [step, setStep] = useState<Step>('login')
  const [account, setAccount] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [sendingCode, setSendingCode] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // 注册资料
  const [nickname, setNickname] = useState('')
  const [major, setMajor] = useState('')
  const [grade, setGrade] = useState('')
  const [skills, setSkills] = useState<string[]>([])

  // 邮箱认证
  const [verifyEmailAddr, setVerifyEmailAddr] = useState('')
  const [verifyCode, setVerifyCode] = useState('')
  const [verifyCodeSent, setVerifyCodeSent] = useState(false)

  const isPhone = /^1\d{10}$/.test(account)
  const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account)

  const handleSendCode = async () => {
    if (!isPhone && !isEmail) {
      showToast('请输入正确的手机号或邮箱', 'error')
      return
    }
    setSendingCode(true)
    try {
      await sendCode(account)
      setCodeSent(true)
      showToast('验证码已发送', 'success')
    } catch {
      showToast('验证码发送失败，请稍后重试', 'error')
    } finally {
      setSendingCode(false)
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
    } catch {
      showToast('登录失败，请检查账号和验证码', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRegister = async () => {
    if (!account || !code) {
      showToast('请填写账号和验证码', 'error')
      return
    }
    setSubmitting(true)
    try {
      const res = await register({ account, code, nickname, major, grade, skills })
      setAuth(res.token, res.user)
      showToast('注册成功', 'success')
      setStep('verify')
    } catch {
      showToast('注册失败，请稍后重试', 'error')
    } finally {
      setSubmitting(false)
    }
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
    } catch {
      showToast('认证失败，请检查邮箱和验证码', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  const toggleSkill = (skill: string) => {
    setSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill],
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-50 to-blue-100 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-600 text-2xl font-bold text-white">
            C
          </div>
          <h1 className="text-2xl font-bold text-gray-900">CampusMate AI</h1>
          <p className="mt-1 text-sm text-gray-500">AI 赋能校园组队</p>
        </div>

        <div className="card">
          {/* 步骤指示器 */}
          {step === 'verify' && (
            <div className="mb-4 flex items-center gap-2 text-sm text-primary-600">
              <Shield size={18} />
              <span>校园邮箱认证</span>
            </div>
          )}

          {/* 登录/注册切换 */}
          {(step === 'login' || step === 'register') && (
            <div className="mb-5 flex rounded-lg bg-gray-100 p-1">
              <button
                onClick={() => setStep('login')}
                className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-colors ${
                  step === 'login' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-500'
                }`}
              >
                登录
              </button>
              <button
                onClick={() => setStep('register')}
                className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-colors ${
                  step === 'register' ? 'bg-white text-primary-600 shadow-sm' : 'text-gray-500'
                }`}
              >
                注册
              </button>
            </div>
          )}

          {/* 账号输入（登录/注册共用） */}
          {(step === 'login' || step === 'register') && (
            <>
              <div className="mb-4">
                <label className="mb-1.5 block text-sm font-medium text-gray-700">手机号 / 邮箱</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                    {isEmail ? <Mail size={16} /> : <Phone size={16} />}
                  </span>
                  <input
                    type="text"
                    value={account}
                    onChange={(e) => setAccount(e.target.value)}
                    placeholder="输入手机号或邮箱"
                    className="input-base pl-9"
                  />
                </div>
              </div>

              {/* 验证码 */}
              <div className="mb-4">
                <label className="mb-1.5 block text-sm font-medium text-gray-700">验证码</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="输入验证码"
                    className="input-base flex-1"
                  />
                  <button
                    onClick={handleSendCode}
                    disabled={sendingCode || codeSent}
                    className="btn-secondary whitespace-nowrap"
                  >
                    {sendingCode ? '发送中...' : codeSent ? '已发送' : '获取验证码'}
                  </button>
                </div>
              </div>

              {/* 登录模式：密码（可选） */}
              {step === 'login' && (
                <div className="mb-5">
                  <label className="mb-1.5 block text-sm font-medium text-gray-700">
                    密码 <span className="text-gray-400">（验证码登录可留空）</span>
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="输入密码（可选）"
                    className="input-base"
                  />
                </div>
              )}

              {/* 注册模式：基础资料 */}
              {step === 'register' && (
                <>
                  <div className="mb-4">
                    <label className="mb-1.5 block text-sm font-medium text-gray-700">昵称</label>
                    <input
                      type="text"
                      value={nickname}
                      onChange={(e) => setNickname(e.target.value)}
                      placeholder="给自己取个昵称"
                      className="input-base"
                    />
                  </div>
                  <div className="mb-4 grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-gray-700">专业</label>
                      <input
                        type="text"
                        value={major}
                        onChange={(e) => setMajor(e.target.value)}
                        placeholder="如：计算机"
                        className="input-base"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-gray-700">年级</label>
                      <select
                        value={grade}
                        onChange={(e) => setGrade(e.target.value)}
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
                  <div className="mb-5">
                    <label className="mb-1.5 block text-sm font-medium text-gray-700">技能标签</label>
                    <div className="flex flex-wrap gap-2">
                      {COMMON_SKILLS.map((skill) => (
                        <button
                          key={skill}
                          onClick={() => toggleSkill(skill)}
                          className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                            skills.includes(skill)
                              ? 'border-primary-500 bg-primary-50 text-primary-600'
                              : 'border-gray-300 text-gray-600'
                          }`}
                        >
                          {skill}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* 提交按钮 */}
              <button
                onClick={step === 'login' ? handleLogin : handleRegister}
                disabled={submitting}
                className="btn-primary w-full"
              >
                {submitting ? '处理中...' : step === 'login' ? '登录' : '注册'}
                <ArrowRight size={16} />
              </button>
            </>
          )}

          {/* 邮箱认证步骤 */}
          {step === 'verify' && (
            <>
              <p className="mb-4 text-sm text-gray-500">
                欢迎，{user?.nickname}！完成校园邮箱认证后即可发帖和申请加入队伍。
              </p>
              <div className="mb-4">
                <label className="mb-1.5 block text-sm font-medium text-gray-700">校园邮箱</label>
                <input
                  type="email"
                  value={verifyEmailAddr}
                  onChange={(e) => setVerifyEmailAddr(e.target.value)}
                  placeholder="如：xxx@nju.edu.cn"
                  className="input-base"
                />
              </div>
              <div className="mb-5">
                <label className="mb-1.5 block text-sm font-medium text-gray-700">验证码</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={verifyCode}
                    onChange={(e) => setVerifyCode(e.target.value)}
                    placeholder="输入邮箱验证码"
                    className="input-base flex-1"
                  />
                  <button
                    onClick={async () => {
                      if (!verifyEmailAddr) return showToast('请先填写邮箱', 'error')
                      try {
                        await sendCode(verifyEmailAddr)
                        setVerifyCodeSent(true)
                        showToast('验证码已发送', 'success')
                      } catch {
                        showToast('发送失败', 'error')
                      }
                    }}
                    disabled={verifyCodeSent}
                    className="btn-secondary whitespace-nowrap"
                  >
                    {verifyCodeSent ? '已发送' : '获取'}
                  </button>
                </div>
              </div>
              <button onClick={handleVerifyEmail} disabled={submitting} className="btn-primary w-full">
                {submitting ? '认证中...' : '完成认证'}
              </button>
              <button
                onClick={() => navigate('/home')}
                className="mt-3 w-full text-center text-sm text-gray-400 hover:text-gray-600"
              >
                稍后再认证，先逛逛
              </button>
            </>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-gray-400">
          首期限南京大学校内使用 · 认证后可发帖和申请
        </p>
      </div>
    </div>
  )
}
