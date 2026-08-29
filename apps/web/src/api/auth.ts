import { post, get, patch } from './client'
import { API_PATHS } from '@shared/constants'
import type { AuthResponse, LoginRequest, RegisterRequest, User } from '@shared/types'

/** 发送验证码 */
export function sendCode(account: string) {
  return post<{ sent: boolean }>(API_PATHS.auth.sendCode, { account })
}

/** 注册 */
export function register(data: RegisterRequest) {
  return post<AuthResponse>(API_PATHS.auth.register, data)
}

/** 登录 */
export function login(data: LoginRequest) {
  return post<AuthResponse>(API_PATHS.auth.login, data)
}

/** 校园邮箱认证 */
export function verifyEmail(email: string, code: string) {
  return post<{ verified: boolean }>(API_PATHS.auth.verifyEmail, { email, code })
}

/** 获取当前用户信息 */
export function getProfile() {
  return get<User>(API_PATHS.auth.profile)
}

/** 更新用户资料 */
export function updateProfile(data: Partial<Pick<User, 'nickname' | 'major' | 'grade' | 'skills'>>) {
  return patch<User>(API_PATHS.auth.profile, data)
}
