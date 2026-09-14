export interface VerificationCodeResponse {
  sent: boolean
  code?: string
  test_mode?: boolean
  reused?: boolean
  retry_after_seconds?: number
}

type ApiLikeError = {
  code?: string
  message?: string
  response?: {
    data?: {
      detail?: string | { message?: string; error_message?: string }
      message?: string
    }
  }
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const apiError = error as ApiLikeError | null
  const detail = apiError?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail && typeof detail === 'object') {
    if (detail.message?.trim()) return detail.message
    if (detail.error_message?.trim()) return detail.error_message
  }
  const responseMessage = apiError?.response?.data?.message
  if (responseMessage?.trim()) return responseMessage
  if (apiError?.code === 'ERR_NETWORK' || !apiError?.response) {
    return import.meta.env.DEV
      ? '无法连接本地后端服务，请确认后端已启动'
      : '服务暂时不可达，请检查网络后重试；填写内容已经保留'
  }
  return fallback
}

export function getCodeSentMessage(result: VerificationCodeResponse): string {
  if (result.test_mode && result.code) {
    return `验证码已生成：${result.code}（本地测试模式）`
  }
  return '验证码已发送'
}
