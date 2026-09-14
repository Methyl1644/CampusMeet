interface CampusMarkProps {
  compact?: boolean
}

export default function CampusMark({ compact = false }: CampusMarkProps) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2.5">
      <img
        src="/campusmeet-mark.svg"
        alt="梧桐遇三鲸鱼梧桐叶标志"
        className={`${compact ? 'size-9' : 'size-11'} shrink-0`}
      />
      {!compact && (
        <span className="min-w-0 leading-none">
          <span className="block truncate text-lg font-bold leading-5 text-ink">
            梧桐遇
          </span>
          <span className="mt-0.5 block truncate text-[11px] font-semibold leading-4 text-campus-green">
            CampusMeet
          </span>
        </span>
      )}
    </span>
  )
}
