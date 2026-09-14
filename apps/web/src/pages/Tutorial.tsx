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
    id: 'activity-vs-group',
    number: '01',
    title: '活动与小组的区别',
    icon: BadgeCheck,
    paragraphs: [
      '“活动”用于正式、安排明确的赛事、讲座、项目和组织活动。',
      '“小组”用于同学发起的临时组队、练习、讨论和轻量邀约。',
      '在探索页切换两者时，搜索和筛选状态会分别保留。',
    ],
  },
  {
    id: 'find-teammates',
    number: '02',
    title: '为正式活动寻找队友',
    icon: Search,
    paragraphs: [
      '打开活动详情后，可查看与该活动关联的组队帖。',
      '选择现有小组申请加入，或从活动页进入发布流程；新帖会自动带上活动标签。',
    ],
  },
  {
    id: 'official-signup',
    number: '03',
    title: '官方报名与人数上限',
    icon: Tags,
    paragraphs: [
      '讲座、个人赛等不需自行组队的活动，只显示由官方负责人发布的高容量报名组。',
      '到达人数上限或截止时间后，报名入口会关闭，已报名状态仍可在“我的活动”查看。',
    ],
  },
  {
    id: 'discussion',
    number: '04',
    title: '讨论与经验交流',
    icon: Sparkles,
    paragraphs: [
      '即使活动不需组队，仍可在“小组”中发布相关讨论，用于请教经验、资料交流或约同行者。',
      '讨论帖不会被视为活动官方报名。',
    ],
  },
  {
    id: 'applications-and-contact',
    number: '05',
    title: '申请、消息与确认组队',
    icon: MessageCircle,
    paragraphs: [
      '在组队帖中提交角色、经历、可用时间和申请理由。发布者接受申请后，双方可进入消息页面继续沟通。',
      '确认合作意愿后，团队页面会集中展示成员分工、首次会议议程、任务清单和风险提醒。',
      '接受申请后系统会自动创建会话；未选择会话时，从左侧会话列表打开对应队伍。',
    ],
  },
  {
    id: 'reporting-and-privacy',
    number: '06',
    title: '举报、隐私与安全',
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
        <p className="section-label">梧桐遇 CampusMeet 使用手册</p>
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
