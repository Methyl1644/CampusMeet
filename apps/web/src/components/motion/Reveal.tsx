import type { ReactNode } from 'react'
import { motion, useReducedMotion } from 'motion/react'

const revealElements = {
  article: motion.article,
  aside: motion.aside,
  div: motion.div,
  footer: motion.footer,
  header: motion.header,
  li: motion.li,
  main: motion.main,
  nav: motion.nav,
  section: motion.section,
  span: motion.span,
} as const

export interface RevealProps {
  children: ReactNode
  className?: string
  delay?: number
  as?: keyof typeof revealElements
}

const clampDelay = (delay: number) => Math.min(Math.max(delay, 0), 0.35)

export function Reveal({
  children,
  className,
  delay = 0,
  as = 'div',
}: RevealProps) {
  const shouldReduceMotion = useReducedMotion()
  const MotionElement = revealElements[as]

  return (
    <MotionElement
      className={className}
      initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        shouldReduceMotion
          ? { duration: 0 }
          : {
              delay: clampDelay(delay),
              duration: 0.26,
              ease: [0.22, 1, 0.36, 1],
            }
      }
    >
      {children}
    </MotionElement>
  )
}
