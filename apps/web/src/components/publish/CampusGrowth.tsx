import { useId } from 'react'
import './publish.css'

const crown = 'M-30 0 Q-43-16-30-25 Q-34-42-17-42 Q-15-61 0-53 Q16-65 20-46 Q39-43 30-25 Q45-9 30 0Z'

export function PlantBorder({ progress }: { progress: number }) {
  return <svg viewBox="0 0 800 62" preserveAspectRatio="xMidYMax slice" className="publish-plant-border" aria-hidden="true">
    <path d="M0 58 Q160 42 310 56 T800 52" fill="none" stroke="#cfdfd2" strokeWidth="2" />
    {Array.from({ length: 25 }, (_, i) => {
      const visible = Math.max(0, Math.min(1, progress * 1.8 - (i % 6) * .13))
      return <g key={i} className="growth-part" style={{ opacity: visible, transform: `translate(${i * 34}px, 62px) scale(${.4 + visible * .4})`, transformOrigin: '0 0' }}>
        <path d="M0 0 Q-9-20 0-46 M-2-16 Q-20-30-24-22 Q-23-11-2-16 M-3-29 Q12-44 17-35 Q16-25-3-29" fill={i % 2 ? '#80ad6a' : '#44785d'} stroke="#44785d" strokeWidth="1.5" />
      </g>
    })}
  </svg>
}

export default function CampusGrowth({ progress, published }: { progress: number; published: boolean }) {
  const id = useId().replace(/:/g, '')
  const growth = Math.max(0, Math.min(1, progress))
  return <div className="campus-growth" aria-label="发布资料完善进度">
    <svg viewBox="0 0 620 268" role="img" aria-label="北大楼与绿植随资料完善逐步绘制" className="w-full overflow-visible">
      <defs><clipPath id={id}><rect x="0" y={225 - growth * 205} width="620" height={growth * 205} className="growth-part" /></clipPath></defs>
      <g fill="none" stroke="#ccd2d0" strokeWidth="1.5" strokeLinejoin="round">
        <path d="M46 213V145H263V62H360V145H573V213ZM42 145L63 111H263M360 111H553L578 145M251 61L242 38L275 43L311 16L348 43L382 38L371 61Z" />
      </g>
      <g className="growth-part" opacity={Math.min(1, growth * 3)} stroke="#555e63" strokeWidth="2" strokeLinejoin="round">
        <path d="M46 145H263V212H46ZM360 145H573V212H360Z" fill="#f5f5f1" />
        <path d="M42 145Q51 135 63 111H263V148ZM360 111H553Q561 135 578 145L360 148Z" fill="#bdc3c7" />
        {Array.from({ length: 14 }, (_, i) => <path key={i} d={`M${72 + i * 13} 116l-12 25 M${371 + i * 13} 116l12 25`} strokeWidth="1" />)}
        <path d="M263 61H360V212H263Z" fill="#f4f4ef" />
        <path d="M251 61L242 38Q267 50 280 38L311 16L344 38Q359 48 382 38L371 61Z" fill="#aab2b9" />
        <path d="M276 43L311 17L349 43M253 53H370" fill="none" />
        <path d="M311 26L315 36L326 37L317 44L320 54L311 48L302 54L305 44L296 37L307 36Z" fill="#b76765" stroke="#865652" strokeWidth="1" />
        <path d="M295 76H327V95H295Z M311 76V95M295 85H327" fill="#d8e2e2" />
        <path d="M292 181H331V216H292Z" fill="#cec7be" />
        <path d="M300 185H323V216H300Z" fill="#805e56" />
        <path d="M289 217H334L338 223H285ZM285 223H338L341 229H282" fill="#bdc3c7" />
      </g>
      <g clipPath={`url(#${id})`}>
        <path d="M267 67H356V181Q341 190 327 179L297 179Q274 185 267 173Z" fill="#77a368" />
        {Array.from({ length: 42 }, (_, i) => <path key={i} d={crown} fill={i % 3 ? '#5c8d5d' : '#477458'} transform={`translate(${278 + (i % 5) * 17} ${81 + Math.floor(i / 5) * 13}) scale(.34)`} />)}
        <rect x="295" y="76" width="32" height="19" fill="#d8e2e2" stroke="#555e63" strokeWidth="2" /><path d="M311 76V95M295 85H327" stroke="#555e63" />
      </g>
      <g className="growth-part" opacity={Math.max(0, Math.min(1, (growth - .25) * 2))}>
        <path d="M25 228Q111 216 281 231L260 257H18ZM341 231Q476 215 600 229L608 257H362Z" fill="#d4e5c7" />
        <path d="M282 229L260 257H362L341 229" fill="#ebeded" stroke="#acb6b1" strokeWidth="1.5" />
        {[45, 86, 122, 158, 205, 252, 374, 529, 570].map((x, i) => <g key={x} transform={`translate(${x} ${223 - (i % 3) * 5}) scale(${i === 5 ? 1.15 : .8})`}><path d="M0 0V-32" stroke="#737d69" strokeWidth="5"/><path d={crown} fill={i % 2 ? '#518064' : '#386651'} stroke="#386651" strokeWidth="1.2" /></g>)}
        <g transform="translate(442 223)"><path d="M0 0V-116" stroke="#72745c" strokeWidth="8" />
          {[-104, -78, -49, -20].map((y, i) => <path key={y} d="M0-27Q-11-32-16-14Q-33-22-33-1Q-53 0-46 22Q-29 19-28 31Q-12 19-3 34Q12 23 22 31Q22 14 39 22Q52 3 32-4Q35-21 17-15Q14-33 0-27Z" fill={i % 2 ? '#83aa62' : '#90b86b'} stroke="#769c5d" strokeWidth="1" transform={`translate(0 ${y}) scale(${.7 + i * .24})`} />)}
        </g>
        {[61, 108, 174, 222, 370, 533, 575].map((x, i) => <path key={x} d={crown} fill={i % 2 ? '#95b875' : '#669562'} transform={`translate(${x} 231) scale(.55 .4)`} />)}
      </g>
      {published && <g transform="translate(535 59)"><circle r="13" fill="#4b9067"/><path d="M-6 0l4 4 8-8" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" /></g>}
    </svg>
    <p className="mt-1 text-center text-xs text-ink-muted" aria-live="polite">{published ? '想法已启程' : growth === 1 ? '绿意成景，等待你确认' : growth > .5 ? '条件逐渐清晰，绿意正在生长' : growth > 0 ? '已了解你的想法，继续补齐细节' : '从一个想法开始'}</p>
  </div>
}
