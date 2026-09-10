import {
  BadgeCheck,
  BookOpen,
  CheckCircle2,
  MessageCircle,
  Search,
  ShieldCheck,
  Sparkles,
  Tags,
} from 'lucide-react'

import { Reveal } from '@/components/motion/Reveal'

const sections = [
  {
    id: 'account',
    number: '01',
    title: '注册与校园认证',
    icon: BadgeCheck,
    paragraphs: [
      '使用手机号或常用邮箱完成注册。填写昵称、专业、年级和技能后，可继续绑定南京大学校园邮箱。',
      '校园认证用于区分校内成员。完成认证后，账号才能发布组队帖或申请加入队伍。',
    ],
  },
  {
    id: 'topics',
    number: '02',
    title: '查找话题与活动',
    icon: Search,
    paragraphs: [
      '官方赛事与认证组织活动以“话题”为入口。先打开话题，可查看活动资料、来源和相关组队帖。',
      '同学自主组队用于运动、约饭和出游等日常邀约，不需要先创建正式话题。',
    ],
  },
  {
    id: 'tags',
    number: '03',
    title: '标准标签与搜索',
    icon: Tags,
    paragraphs: [
      '搜索同时匹配话题名称、活动简称和标准标签。话题直达结果优先显示，点击即可进入活动页面。',
      '系统不会把非标准写法直接加入标签库。例如输入“羽球”时，会推荐已收录的标准标签“羽毛球”。',
    ],
  },
  {
    id: 'publish',
    number: '04',
    title: 'AI 辅助发布组队帖',
    icon: Sparkles,
    paragraphs: [
      '描述想参加的活动和需要的队友，AI 会整理活动名称、人数、角色、投入时间、范围和截止日期。',
      '不知道或没有要求的字段可以跳过。发布前仍可手动修改草稿，并决定保留哪些标准标签。',
    ],
  },
  {
    id: 'team',
    number: '05',
    title: '申请、消息与确认组队',
    icon: MessageCircle,
    paragraphs: [
      '在组队帖中提交角色、经历、可用时间和申请理由。发布者接受申请后，双方可进入消息页面继续沟通。',
      '确认合作意愿后，团队页面会集中展示成员分工、首次会议议程、任务清单和风险提醒。',
    ],
  },
  {
    id: 'safety',
    number: '06',
    title: '联系方式与安全',
    icon: ShieldCheck,
    paragraphs: [
      '不要在公开帖子或未确认的聊天中发布手机号、微信号、身份证号或精确住址。',
      '联系方式只在双方确认组队后解锁。发现违规、诱导转账或高风险活动时，应停止沟通并联系平台运营人员。',
    ],
  },
]

export default function Tutorial() {
  return (
    <div className="mx-auto max-w-5xl">
      <Reveal as="header" className="border-b border-stone pb-7">
        <p className="section-label">CampusMate 使用手册</p>
        <div className="mt-4 flex items-center gap-3">
          <BookOpen aria-hidden="true" className="size-6 text-primary-600" />
          <h1 className="text-3xl font-semibold text-ink">教程</h1>
        </div>
      </Reveal>

      <div className="grid gap-10 py-8 lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-14">
        <Reveal as="aside" className="hidden lg:block" delay={0.04}>
          <nav className="sticky top-28 border-l border-stone" aria-label="教程目录">
            {sections.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                className="flex min-h-10 items-center gap-3 border-l-2 border-transparent px-4 text-sm text-ink-muted transition-colors hover:border-primary-500 hover:text-primary-700"
              >
                <span className="text-xs tabular-nums text-primary-500">{section.number}</span>
                {section.title}
              </a>
            ))}
          </nav>
        </Reveal>

        <main className="min-w-0 divide-y divide-stone">
          {sections.map((section, index) => {
            const Icon = section.icon
            return (
              <section key={section.id} id={section.id} className="scroll-mt-28 py-8 first:pt-0">
                <Reveal
                  as="div"
                  className="grid gap-5 sm:grid-cols-[3rem_minmax(0,1fr)]"
                  delay={Math.min(index * 0.04, 0.2)}
                >
                  <div className="flex size-11 items-center justify-center rounded-card border border-primary-200 bg-primary-50 text-primary-700">
                    <Icon aria-hidden="true" className="size-5" />
                  </div>
                  <div>
                    <p className="text-xs font-semibold tabular-nums text-campus-green">{section.number}</p>
                    <h2 className="mt-1 text-xl font-semibold text-ink">{section.title}</h2>
                    <div className="mt-4 space-y-3 text-sm leading-7 text-ink-muted">
                      {section.paragraphs.map((paragraph) => (
                        <p key={paragraph} className="flex items-start gap-2">
                          <CheckCircle2 aria-hidden="true" className="mt-1.5 size-4 shrink-0 text-campus-green" />
                          <span>{paragraph}</span>
                        </p>
                      ))}
                    </div>
                  </div>
                </Reveal>
              </section>
            )
          })}
        </main>
      </div>
    </div>
  )
}
