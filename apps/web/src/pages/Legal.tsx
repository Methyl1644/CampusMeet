import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

const documents = {
  terms: {
    title: '用户协议',
    sections: [
      ['账号与使用', '梧桐遇面向南京大学校园用户。请使用本人校园邮箱注册，妥善保管账号，不得冒用他人身份或利用平台骚扰、诈骗。'],
      ['内容与协作', '发布活动、组队与交流内容时，应保证信息真实、合法并尊重他人。平台可对违规内容采取限制展示、暂停互动或账号处置。'],
      ['服务说明', '平台会尽力保障服务稳定，但网络、第三方 AI 与存储服务可能短时不可用。重要安排请由团队成员再次确认。'],
    ],
  },
  privacy: {
    title: '隐私政策',
    sections: [
      ['收集范围', '为完成注册、匹配与组队协作，我们会处理校园邮箱、昵称、专业年级、兴趣技能、可参与时间、用户主动填写的联系方式及站内操作记录。'],
      ['使用目的', '信息用于身份验证、内容发布、活动报名、队友推荐、消息沟通、安全风控和服务改进。队友推荐只使用你选择公开并明确授权参与匹配的资料，不向 AI 服务发送联系方式。'],
      ['第三方与保存', '图片由 Cloudinary 等对象存储服务托管，AI 整理由 Coze 工作流处理必要的帖子信息。我们按实现服务与安全审计所需的期限保存数据。'],
      ['你的权利', '你可以在“设置”中调整资料可见性、关闭队友推荐、申请导出数据、停用账号或申请永久删除账号。'],
    ],
  },
} as const

export default function Legal({ kind }: { kind: keyof typeof documents }) {
  const document = documents[kind]
  return (
    <main className="min-h-dvh bg-paper-warm px-4 py-8 sm:px-8">
      <article className="mx-auto max-w-3xl bg-paper px-5 py-8 sm:px-10 sm:py-12">
        <Link to="/login" className="inline-flex min-h-10 items-center gap-2 text-sm font-semibold text-primary-700"><ArrowLeft aria-hidden="true" className="size-4" />返回登录</Link>
        <p className="section-label mt-8">梧桐遇 CampusMeet</p>
        <h1 className="mt-3 text-3xl font-semibold text-ink">{document.title}</h1>
        <p className="mt-2 text-sm text-ink-muted">更新日期：2026 年 9 月 20 日</p>
        <div className="mt-8 space-y-8">
          {document.sections.map(([title, content]) => <section key={title}><h2 className="text-lg font-semibold text-ink">{title}</h2><p className="mt-2 text-sm leading-7 text-ink-muted">{content}</p></section>)}
        </div>
      </article>
    </main>
  )
}
