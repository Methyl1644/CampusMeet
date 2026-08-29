import { Loader2 } from 'lucide-react'

export default function Loading({ text = '加载中...' }: { text?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-8 text-gray-500">
      <Loader2 size={18} className="animate-spin" />
      <span className="text-sm">{text}</span>
    </div>
  )
}

export function AIThinking() {
  return (
    <div className="flex items-center gap-2 py-2 text-gray-500">
      <span className="text-sm">AI 正在思考</span>
      <span className="flex gap-1">
        <span className="thinking-dot text-primary-500">●</span>
        <span className="thinking-dot text-primary-500">●</span>
        <span className="thinking-dot text-primary-500">●</span>
      </span>
    </div>
  )
}
