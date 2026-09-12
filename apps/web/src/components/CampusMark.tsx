interface CampusMarkProps {
  compact?: boolean
}

export default function CampusMark({ compact = false }: CampusMarkProps) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2.5">
      <img
        src="/campus-clocktower-badge.jpg"
        alt={compact ? 'CampusMate 南京大学校园钟楼标志' : ''}
        className={`${compact ? 'size-9' : 'size-11'} shrink-0 rounded-full border border-campus-green/25 object-cover`}
      />
      {!compact && (
        <span className="min-w-0">
          <span className="block truncate font-serif text-lg font-semibold leading-5 text-ink">
            CampusMate
          </span>
          <span className="block truncate text-[11px] leading-4 text-ink-muted">
            南京大学校园组队
          </span>
        </span>
      )}
    </span>
  )
}
