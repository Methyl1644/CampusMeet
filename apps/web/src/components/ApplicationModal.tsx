import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { Send, X } from 'lucide-react'
import { createApplication } from '@/api/applications'
import { getApiErrorMessage } from '@/api/auth-feedback'
import { useToast } from './Toast'

interface ApplicationTarget {
  id: string
  title: string
  needed_roles: string[]
}

interface ApplicationModalProps {
  post: ApplicationTarget
  onClose: () => void
  onSuccess: () => void
}

interface FormErrors {
  role?: string
  experience?: string
  reason?: string
}

const focusableSelector = [
  'button:not([disabled])',
  'input:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

const unrestrictedRole = '不限角色'

export default function ApplicationModal({ post, onClose, onSuccess }: ApplicationModalProps) {
  const roleOptions = post.needed_roles.length > 0 ? post.needed_roles : [unrestrictedRole]
  const [roleWanted, setRoleWanted] = useState(roleOptions[0])
  const [experience, setExperience] = useState('')
  const [availableTime, setAvailableTime] = useState('')
  const [reason, setReason] = useState('')
  const [questions, setQuestions] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)

  const modalRef = useRef<HTMLDivElement>(null)
  const { showToast } = useToast()
  const shouldReduceMotion = useReducedMotion()

  useEffect(() => {
    const previouslyFocusedElement = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null
    const previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const focusableElements = () => Array.from(
      modalRef.current?.querySelectorAll<HTMLElement>(focusableSelector) ?? [],
    )
    focusableElements()[0]?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== 'Tab') return

      const elements = focusableElements()
      if (elements.length === 0) {
        event.preventDefault()
        modalRef.current?.focus()
        return
      }

      const firstElement = elements[0]
      const lastElement = elements[elements.length - 1]
      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousBodyOverflow
      if (previouslyFocusedElement) previouslyFocusedElement.focus()
    }
  }, [onClose])

  const handleSubmit = async () => {
    const nextErrors: FormErrors = {}
    if (!roleWanted) nextErrors.role = '请选择你想担任的角色'
    if (!experience.trim()) nextErrors.experience = '请填写相关经验'
    if (!reason.trim()) nextErrors.reason = '请填写加入原因'
    setErrors(nextErrors)

    if (!roleWanted) {
      showToast('请选择你想担任的角色', 'error')
      return
    }
    if (!experience.trim()) {
      showToast('请填写相关经验', 'error')
      return
    }
    if (!reason.trim()) {
      showToast('请填写加入原因', 'error')
      return
    }

    setSubmitting(true)
    try {
      await createApplication({
        post_id: post.id,
        role_wanted: roleWanted,
        experience: experience.trim(),
        available_time: availableTime.trim(),
        reason: reason.trim(),
        questions: questions.trim() ? [questions.trim()] : undefined,
      })
      showToast('申请已提交，等待回复', 'success')
      onSuccess()
      onClose()
    } catch (error) {
      showToast(getApiErrorMessage(error, '申请提交失败，请稍后重试'), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/45 p-0 md:items-center md:p-4"
      onClick={onClose}
      role="presentation"
    >
      <motion.div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="application-modal-title"
        tabIndex={-1}
        initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.18 }}
        className="flex max-h-[calc(100dvh-1rem)] w-full max-w-lg flex-col overflow-hidden rounded-t-card border border-stone bg-paper shadow-lg md:max-h-[calc(100dvh-2rem)] md:rounded-card"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-stone px-4 py-4 sm:px-5">
          <div className="min-w-0">
            <p className="section-label">组队申请</p>
            <h2 id="application-modal-title" className="mt-2 font-serif text-xl font-semibold text-ink">
              申请加入
            </h2>
            <p className="mt-1 truncate text-xs text-ink-muted">{post.title}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="icon-button -mr-2 -mt-2"
            aria-label="关闭申请弹窗"
            title="关闭申请弹窗"
          >
            <X aria-hidden="true" size={20} />
          </button>
        </header>

        <form
          className="flex min-h-0 flex-1 flex-col"
          onSubmit={(event) => {
            event.preventDefault()
            handleSubmit()
          }}
        >
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-5 sm:px-5">
            <fieldset id="application-role" aria-describedby={errors.role ? 'application-role-error' : undefined}>
              <legend className="text-sm font-semibold text-ink">
                选择角色 <span className="text-red-600" aria-hidden="true">*</span>
                <span className="sr-only">必填</span>
              </legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {roleOptions.map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => {
                      setRoleWanted(role)
                      setErrors((current) => ({ ...current, role: undefined }))
                    }}
                    aria-pressed={roleWanted === role}
                    className={`min-h-9 rounded-card border px-3 py-1.5 text-sm font-medium transition-colors ${
                      roleWanted === role
                        ? 'border-primary-600 bg-primary-50 text-primary-700'
                        : 'border-stone text-ink-muted hover:border-primary-300 hover:text-primary-700'
                    }`}
                  >
                    {role}
                  </button>
                ))}
              </div>
              {errors.role && <FieldError id="application-role-error">{errors.role}</FieldError>}
            </fieldset>

            <Field label="相关经验" inputId="application-experience" required error={errors.experience}>
              <textarea
                id="application-experience"
                value={experience}
                onChange={(event) => {
                  setExperience(event.target.value)
                  setErrors((current) => ({ ...current, experience: undefined }))
                }}
                rows={3}
                aria-invalid={Boolean(errors.experience)}
                aria-describedby={errors.experience ? 'application-experience-error' : undefined}
                className="input-base resize-y"
              />
            </Field>

            <Field label="可投入时间" inputId="application-time">
              <input
                id="application-time"
                type="text"
                value={availableTime}
                onChange={(event) => setAvailableTime(event.target.value)}
                className="input-base"
              />
            </Field>

            <Field label="加入原因" inputId="application-reason" required error={errors.reason}>
              <textarea
                id="application-reason"
                value={reason}
                onChange={(event) => {
                  setReason(event.target.value)
                  setErrors((current) => ({ ...current, reason: undefined }))
                }}
                rows={3}
                aria-invalid={Boolean(errors.reason)}
                aria-describedby={errors.reason ? 'application-reason-error' : undefined}
                className="input-base resize-y"
              />
            </Field>

            <Field label="问题（选填）" inputId="application-questions">
              <textarea
                id="application-questions"
                value={questions}
                onChange={(event) => setQuestions(event.target.value)}
                rows={2}
                className="input-base resize-y"
              />
            </Field>
          </div>

          <footer className="shrink-0 border-t border-stone bg-paper px-4 py-3 sm:px-5">
            <div className="grid grid-cols-2 gap-3">
              <button type="button" onClick={onClose} className="btn-secondary min-h-11">
                取消
              </button>
              <button type="submit" disabled={submitting} className="btn-primary min-h-11">
                <Send aria-hidden="true" size={16} />
                {submitting ? '提交中...' : '提交申请'}
              </button>
            </div>
          </footer>
        </form>
      </motion.div>
    </div>
  )
}

function Field({
  children,
  error,
  inputId,
  label,
  required = false,
}: {
  children: ReactNode
  error?: string
  inputId: string
  label: string
  required?: boolean
}) {
  return (
    <div>
      <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ink">
        {label}{' '}
        {required && (
          <>
            <span className="text-red-600" aria-hidden="true">*</span>
            <span className="sr-only">必填</span>
          </>
        )}
      </label>
      {children}
      {error && <FieldError id={`${inputId}-error`}>{error}</FieldError>}
    </div>
  )
}

function FieldError({ children, id }: { children: string; id: string }) {
  return <p id={id} className="mt-1.5 text-xs font-medium text-red-700" role="alert">{children}</p>
}
