import assert from 'node:assert/strict'
import test from 'node:test'

import { getApiErrorMessage, getCodeSentMessage } from './auth-feedback.ts'

test('uses the backend detail instead of replacing it with a generic error', () => {
  const error = { response: { data: { detail: '后端服务未启动' } } }

  assert.equal(getApiErrorMessage(error, '验证码发送失败'), '后端服务未启动')
})

test('shows a returned verification code only in backend test mode', () => {
  assert.equal(
    getCodeSentMessage({ sent: true, test_mode: true, code: '246810' }),
    '验证码已生成：246810（本地测试模式）',
  )
  assert.equal(getCodeSentMessage({ sent: true }), '验证码已发送')
})
