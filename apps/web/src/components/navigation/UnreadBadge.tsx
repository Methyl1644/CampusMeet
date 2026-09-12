export function unreadLabel(label: string, count: number) {
  return `${label}，${count} 条未读`
}

export default function UnreadBadge({ count }: { count: number }) {
  if (count <= 0) return null

  return (
    <span
      aria-hidden="true"
      className="absolute -right-1 -top-1 flex min-w-[18px] items-center justify-center rounded-full bg-primary-600 px-1 text-[10px] font-semibold leading-[18px] text-white"
    >
      {count > 99 ? '99+' : count}
    </span>
  )
}
