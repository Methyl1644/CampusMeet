// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { login, register, resetPassword, sendCode } from '@/api/auth'
import { ToastProvider } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import type { User } from '@shared/types'
import Login from './Login'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  resetPassword: vi.fn(),
  sendCode: vi.fn(),
}))

const user = {
  id: '1',
  email: 'student@smail.nju.edu.cn',
  nickname: 'student',
  auth_status: 'unverified',
  skills: [],
  onboarding_step: 6,
  onboarding_completed: true,
  interests: [],
  looking_for: [],
  availability: {},
  profile_visibility: {
    major: true,
    grade: true,
    interests: true,
    skills: true,
    availability: false,
    contact: false,
  },
} as User

function renderLogin() {
  render(
    <MemoryRouter initialEntries={['/login']}>
      <ToastProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/home" element={<h1>Home destination</h1>} />
          <Route path="/onboarding" element={<h1>Onboarding destination</h1>} />
        </Routes>
      </ToastProvider>
    </MemoryRouter>,
  )
}

function submitFrom(input: HTMLElement) {
  const form = (input as HTMLInputElement).form
  expect(form).not.toBeNull()
  form!.requestSubmit()
}

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState({ token: null, user: null, isAuthenticated: false })
  vi.mocked(login).mockResolvedValue({ token: 'token', user })
  vi.mocked(register).mockResolvedValue({
    token: 'token',
    user: { ...user, onboarding_completed: false, onboarding_step: 1 },
  })
  vi.mocked(resetPassword).mockResolvedValue(null)
  vi.mocked(sendCode).mockResolvedValue({ sent: true, retry_after_seconds: 60 })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  vi.unstubAllGlobals()
})

describe('Login keyboard submission', () => {
  it('submits login from the password field form', async () => {
    renderLogin()
    fireEvent.change(screen.getByLabelText('南京大学邮箱'), {
      target: { value: 'student@smail.nju.edu.cn' },
    })
    const password = screen.getByLabelText('密码')
    fireEvent.change(password, { target: { value: 'Password2026' } })

    submitFrom(password)

    expect(await screen.findByRole('heading', { name: 'Home destination' })).toBeTruthy()
    expect(login).toHaveBeenCalledWith({
      account: 'student@smail.nju.edu.cn',
      password: 'Password2026',
    })
  })

  it('submits registration from the password field form', async () => {
    renderLogin()
    fireEvent.click(screen.getByRole('button', { name: '注册' }))
    fireEvent.change(screen.getByLabelText('南京大学邮箱'), {
      target: { value: 'student@smail.nju.edu.cn' },
    })
    fireEvent.change(await screen.findByLabelText('验证码'), { target: { value: '123456' } })
    const password = await screen.findByLabelText('设置密码')
    fireEvent.change(password, { target: { value: 'Password2026' } })

    submitFrom(password)

    expect(await screen.findByRole('heading', { name: 'Onboarding destination' })).toBeTruthy()
    expect(register).toHaveBeenCalledWith({
      account: 'student@smail.nju.edu.cn',
      code: '123456',
      password: 'Password2026',
    })
  })

  it('submits password reset from the confirmation field form', async () => {
    renderLogin()
    fireEvent.click(screen.getByRole('button', { name: '忘记密码？' }))
    fireEvent.change(screen.getByLabelText('南京大学邮箱'), {
      target: { value: 'student@smail.nju.edu.cn' },
    })
    fireEvent.change(await screen.findByLabelText('邮箱验证码'), { target: { value: '123456' } })
    fireEvent.change(await screen.findByLabelText('新密码'), { target: { value: 'NewPassword2026' } })
    const confirmation = await screen.findByLabelText('再次输入新密码')
    fireEvent.change(confirmation, { target: { value: 'NewPassword2026' } })

    submitFrom(confirmation)

    await waitFor(() => expect(screen.getByRole('heading', { name: '欢迎回来' })).toBeTruthy())
    expect(resetPassword).toHaveBeenCalledWith({
      account: 'student@smail.nju.edu.cn',
      code: '123456',
      new_password: 'NewPassword2026',
    })
  })

  it('uses ordinary buttons for mode selection without incomplete tab semantics', () => {
    renderLogin()

    expect(screen.queryByRole('tablist')).toBeNull()
    expect(screen.queryAllByRole('tab')).toEqual([])
    expect(screen.getAllByRole('button', { name: '登录' })).toHaveLength(2)
    expect(screen.getByRole('button', { name: '注册' })).toBeTruthy()
  })
})
