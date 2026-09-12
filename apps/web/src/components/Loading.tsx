import { Clock3, Sparkles } from 'lucide-react'

export default function Loading({ text = '加载中...' }: { text?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="animate-slide-up flex min-h-24 items-center justify-center gap-2 py-8 text-ink-muted"
    >
      <Clock3
        aria-hidden="true"
        className="size-[18px] shrink-0 text-primary-600"
      />
      <span className="text-sm">{text}</span>
    </div>
  )
}

export function AIThinking() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="animate-slide-up flex min-h-9 items-center gap-2 py-2 text-ink-muted"
    >
      <Sparkles
        aria-hidden="true"
        className="size-4 shrink-0 text-primary-600"
      />
      <span className="text-sm">AI 正在思考</span>
    </div>
  )
}
