import { CircleHelp, Github } from 'lucide-react'
import { SITE_LINKS } from '@shared/constants'

export default function SiteFooter() {
  return (
    <footer className="mt-12 bg-[#232326] text-white md:mt-16">
      <div className="mx-auto grid max-w-content gap-8 px-4 py-10 sm:px-6 md:grid-cols-[minmax(0,1fr)_auto] md:items-end lg:px-8">
        <div>
          <p className="text-xl font-bold">梧桐遇 <span className="text-sm font-semibold text-white/65">CampusMeet</span></p>
          <p className="mt-2 max-w-xl text-sm leading-6 text-white/65">连接南京大学校园里的活动、同伴与行动。</p>
        </div>
        <nav aria-label="页脚链接" className="flex flex-wrap gap-3">
          <a href={SITE_LINKS.contact} target="_blank" rel="noreferrer" className="inline-flex min-h-10 items-center gap-2 border border-white/20 px-4 text-sm font-semibold hover:border-white/50"><CircleHelp aria-hidden="true" className="size-4" />问题反馈</a>
          <a href={SITE_LINKS.repository} target="_blank" rel="noreferrer" className="inline-flex min-h-10 items-center gap-2 border border-white/20 px-4 text-sm font-semibold hover:border-white/50"><Github aria-hidden="true" className="size-4" />项目仓库</a>
        </nav>
      </div>
      <div className="border-t border-white/10"><p className="mx-auto max-w-content px-4 py-4 text-xs text-white/50 sm:px-6 lg:px-8">梧桐遇 CampusMeet · 南京大学校园团队</p></div>
    </footer>
  )
}
