import type { ReactNode } from 'react'
import { ArrowLeft, ArrowRight, LoaderCircle } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import CampusMark from '@/components/CampusMark'

interface OnboardingShellProps {
  step: number
  direction: number
  isSaving: boolean
  stageDisabled: boolean
  canGoBack: boolean
  continueDisabled: boolean
  continueLabel?: string
  tipTitle: string
  tip: ReactNode
  children: ReactNode
  onBack: () => void
  onContinue: () => void
}

const stageVariants = {
  enter: (direction: number) => ({ opacity: 0, x: direction * 16 }),
  center: { opacity: 1, x: 0 },
  exit: (direction: number) => ({ opacity: 0, x: direction * -10 }),
}

const reducedStageVariants = {
  enter: { opacity: 0, x: 0 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 0 },
}

export default function OnboardingShell({
  step,
  direction,
  isSaving,
  stageDisabled,
  canGoBack,
  continueDisabled,
  continueLabel = '继续',
  tipTitle,
  tip,
  children,
  onBack,
  onContinue,
}: OnboardingShellProps) {
  const shouldReduceMotion = useReducedMotion()
  const variants = shouldReduceMotion ? reducedStageVariants : stageVariants

  return (
    <main className="onboarding-page">
      <header className="border-b border-stone bg-paper">
        <div className="mx-auto flex w-full max-w-[1120px] items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <CampusMark />
          <button
            type="button"
            onClick={onBack}
            disabled={!canGoBack || isSaving}
            aria-hidden={!canGoBack}
            tabIndex={canGoBack ? 0 : -1}
            className={`icon-button ${canGoBack ? '' : 'invisible'}`}
            title="返回上一步"
          >
            <ArrowLeft aria-hidden="true" className="size-5" />
            <span className="sr-only">返回上一步</span>
          </button>
        </div>
        <div
          role="progressbar"
          aria-label="资料完善进度"
          aria-valuemin={1}
          aria-valuemax={6}
          aria-valuenow={step}
          className="mx-auto grid w-full max-w-[1120px] grid-cols-6 gap-2 px-5 pb-4 sm:px-8"
        >
          {Array.from({ length: 6 }, (_, index) => (
            <span
              key={index}
              aria-hidden="true"
              className={`h-1 rounded-sm transition-colors duration-feedback ${
                index < step ? 'bg-primary-600' : 'bg-stone'
              }`}
            />
          ))}
        </div>
      </header>

      <div className="mx-auto w-full max-w-[1120px] flex-1 px-5 py-8 sm:px-8 sm:py-12">
        <AnimatePresence mode="wait" initial={false} custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            variants={variants}
            initial={shouldReduceMotion ? false : 'enter'}
            animate="center"
            exit="exit"
            transition={{ duration: shouldReduceMotion ? 0.08 : 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="onboarding-stage-grid"
          >
            <section className="flex min-w-0 flex-col" aria-label={`资料完善第 ${step} 步`}>
              <fieldset
                disabled={stageDisabled}
                className="m-0 min-h-[430px] min-w-0 flex-1 border-0 p-0 sm:min-h-[470px]"
              >
                <legend className="sr-only">资料完善第 {step} 步字段</legend>
                {children}
              </fieldset>
              <div className="mt-8 flex min-h-11 items-center justify-end border-t border-stone pt-5">
                <button
                  type="button"
                  onClick={onContinue}
                  disabled={continueDisabled || isSaving}
                  className="btn-primary min-h-11 w-full px-5 sm:w-auto sm:min-w-32"
                >
                  {isSaving ? (
                    <>
                      <LoaderCircle aria-hidden="true" className="size-[18px] animate-spin" />
                      保存中
                    </>
                  ) : (
                    <>
                      {continueLabel}
                      <ArrowRight aria-hidden="true" className="size-[18px]" />
                    </>
                  )}
                </button>
              </div>
            </section>

            <aside className="onboarding-tip" aria-labelledby="onboarding-tip-title">
              <p className="text-xs font-semibold text-primary-700">第 {step} 步，共 6 步</p>
              <h2 id="onboarding-tip-title" className="mt-2 font-sans text-base font-semibold text-ink">
                {tipTitle}
              </h2>
              <div className="mt-2 text-sm leading-6 text-ink-muted">{tip}</div>
            </aside>
          </motion.div>
        </AnimatePresence>
      </div>
    </main>
  )
}
