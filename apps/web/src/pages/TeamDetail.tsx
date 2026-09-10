import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Circle,
  ListChecks,
  MessageCircle,
  Phone,
  Users,
} from 'lucide-react'
import { getTeamDetail, updateTask } from '@/api/teams'
import type { Team } from '@shared/types'
import Loading from '@/components/Loading'
import { Reveal } from '@/components/motion/Reveal'
import { useToast } from '@/components/Toast'

export default function TeamDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [team, setTeam] = useState<Team | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    const fetchTeam = async () => {
      setLoading(true)
      try {
        const data = await getTeamDetail(id)
        if (!cancelled) setTeam(data)
      } catch {
        if (!cancelled) showToast('加载失败', 'error')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchTeam()
    return () => { cancelled = true }
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleToggleTask = async (taskId: string, currentDone: boolean) => {
    if (!team) return
    setTeam({
      ...team,
      task_list: team.task_list.map((task) =>
        task.id === taskId ? { ...task, done: !currentDone } : task,
      ),
    })
    try {
      await updateTask(team.id, taskId, !currentDone)
    } catch {
      setTeam({
        ...team,
        task_list: team.task_list.map((task) =>
          task.id === taskId ? { ...task, done: currentDone } : task,
        ),
      })
      showToast('更新失败', 'error')
    }
  }

  const handleToggleAgenda = (agendaId: string) => {
    if (!team) return
    setTeam({
      ...team,
      meeting_agenda: team.meeting_agenda.map((agenda) =>
        agenda.id === agendaId ? { ...agenda, done: !agenda.done } : agenda,
      ),
    })
  }

  if (loading) return <Loading />
  if (!team) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-ink-muted">团队不存在</p>
        <button onClick={() => navigate('/profile')} className="btn-secondary mt-4">返回</button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl">
      <button
        onClick={() => navigate(-1)}
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-ink-muted transition-colors hover:text-primary-700"
      >
        <ArrowLeft aria-hidden="true" size={16} />
        返回
      </button>

      <Reveal as="header" className="border-y border-stone bg-paper px-4 py-6 sm:px-7">
        <p className="section-label">团队工作台</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-serif text-2xl font-semibold leading-9 text-ink sm:text-3xl">
              {team.activity_name}
            </h1>
            <p className="mt-2 text-sm text-ink-muted">建立于 {team.created_at || '暂无'}</p>
          </div>
          <span className="text-sm font-semibold tabular-nums text-campus-green">
            {team.members.length} 位成员
          </span>
        </div>
      </Reveal>

      <div className="mt-7 grid gap-8 lg:grid-cols-[minmax(0,1.25fr)_minmax(17rem,0.75fr)] lg:gap-10">
        <main className="min-w-0 space-y-8">
          <Reveal as="section">
            <SectionHeading icon={Users} id="members-title">成员与角色</SectionHeading>
            {team.members.length > 0 ? (
              <div className="mt-3 divide-y divide-stone border-y border-stone">
                {team.members.map((member) => (
                  <div key={member.user.id} className="flex min-h-16 items-center gap-3 py-3">
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-700">
                      {member.user.nickname.charAt(0)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-ink">{member.user.nickname}</p>
                      <p className="mt-0.5 text-xs text-ink-muted">
                        {member.user.major || '暂无'} · {member.user.grade || '暂无'}
                      </p>
                    </div>
                    <span className="shrink-0 text-xs font-semibold text-primary-700">
                      {member.suggested_role || '暂无'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-ink-muted">暂无</p>
            )}
          </Reveal>

          <Reveal as="section" delay={0.04}>
            <SectionHeading icon={Users} id="division-title">分工建议</SectionHeading>
            {team.division_of_labor.length > 0 ? (
              <dl className="mt-3 divide-y divide-stone border-y border-stone">
                {team.division_of_labor.map((item, index) => (
                  <div key={`${item.role}-${index}`} className="grid gap-1 py-4 sm:grid-cols-[9rem_minmax(0,1fr)] sm:gap-5">
                    <dt className="text-sm font-semibold text-ink">{item.role}</dt>
                    <dd className="min-w-0 text-sm leading-6 text-ink-muted">
                      <p>{item.responsibilities}</p>
                      {item.member_id && (
                        <p className="mt-1 text-xs font-medium text-primary-700">
                          负责人：{team.members.find((member) => member.user.id === item.member_id)?.user.nickname || '待分配'}
                        </p>
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="mt-3 text-sm text-ink-muted">暂无</p>
            )}
          </Reveal>

          <Reveal as="section" delay={0.06}>
            <SectionHeading icon={ListChecks} id="agenda-title">首次会议议程</SectionHeading>
            {team.meeting_agenda.length > 0 ? (
              <div className="mt-3 divide-y divide-stone border-y border-stone">
                {team.meeting_agenda.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleToggleAgenda(item.id)}
                    aria-pressed={item.done}
                    className="flex min-h-12 w-full items-center gap-3 px-1 py-2 text-left transition-colors hover:bg-paper focus-visible:bg-paper"
                  >
                    {item.done ? (
                      <CheckCircle2 aria-hidden="true" size={18} className="shrink-0 text-campus-green" />
                    ) : (
                      <Circle aria-hidden="true" size={18} className="shrink-0 text-ink-muted" />
                    )}
                    <span className={`min-w-0 text-sm leading-6 ${item.done ? 'text-ink-muted line-through' : 'text-ink'}`}>
                      {item.content}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-ink-muted">暂无</p>
            )}
          </Reveal>

          <Reveal as="section" delay={0.08}>
            <SectionHeading icon={Calendar} id="tasks-title">任务清单</SectionHeading>
            {team.task_list.length > 0 ? (
              <div className="mt-3 divide-y divide-stone border-y border-stone">
                {team.task_list.map((task) => (
                  <button
                    key={task.id}
                    onClick={() => handleToggleTask(task.id, task.done)}
                    aria-pressed={task.done}
                    className="flex min-h-16 w-full items-center gap-3 px-1 py-2 text-left transition-colors hover:bg-paper focus-visible:bg-paper"
                  >
                    {task.done ? (
                      <CheckCircle2 aria-hidden="true" size={18} className="shrink-0 text-campus-green" />
                    ) : (
                      <Circle aria-hidden="true" size={18} className="shrink-0 text-ink-muted" />
                    )}
                    <div className="min-w-0 flex-1">
                      <span className={`block text-sm leading-6 ${task.done ? 'text-ink-muted line-through' : 'text-ink'}`}>
                        {task.title}
                      </span>
                      <div className="mt-0.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-muted">
                        <span>负责人：{task.assignee_name || '暂无'}</span>
                        <span>截止：{task.deadline || '暂无'}</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-ink-muted">暂无</p>
            )}
          </Reveal>
        </main>

        <aside className="min-w-0 space-y-8 lg:border-l lg:border-stone lg:pl-8">
          {team.risk_reminders.length > 0 && (
            <Reveal as="section">
              <SectionHeading icon={AlertTriangle} id="risks-title" tone="gold">风险提醒</SectionHeading>
              <ul className="mt-3 divide-y divide-campus-gold/20 border-y border-campus-gold/25 bg-amber-50 px-3">
                {team.risk_reminders.map((reminder, index) => (
                  <li key={index} className="flex items-start gap-2 py-3 text-xs leading-5 text-amber-900">
                    <AlertTriangle aria-hidden="true" size={14} className="mt-0.5 shrink-0 text-campus-gold" />
                    <span>{reminder}</span>
                  </li>
                ))}
              </ul>
            </Reveal>
          )}

          <Reveal as="section" delay={0.04}>
            <SectionHeading icon={Phone} id="contacts-title">联系方式</SectionHeading>
            {team.contact_info.length > 0 ? (
              <div className="mt-3 divide-y divide-stone border-y border-stone">
                {team.contact_info.map((contact) => (
                  <div key={contact.user_id} className="py-3">
                    <p className="text-sm font-semibold text-ink">{contact.nickname}</p>
                    <div className="mt-2 grid gap-2 text-xs text-ink-muted">
                      {contact.phone && (
                        <span className="flex min-w-0 items-center gap-2">
                          <Phone aria-hidden="true" size={13} className="shrink-0 text-campus-green" />
                          <span className="break-all">{contact.phone}</span>
                        </span>
                      )}
                      {contact.wechat && (
                        <span className="flex min-w-0 items-center gap-2">
                          <MessageCircle aria-hidden="true" size={13} className="shrink-0 text-campus-green" />
                          <span className="break-all">{contact.wechat}</span>
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 border-y border-stone py-6 text-center">
                <p className="text-sm font-medium text-ink">联系方式暂未解锁</p>
                <p className="mt-1 text-xs leading-5 text-ink-muted">
                  双方确认组队后将解锁联系方式
                </p>
              </div>
            )}
          </Reveal>
        </aside>
      </div>
    </div>
  )
}

function SectionHeading({
  children,
  icon: Icon,
  id,
  tone = 'green',
}: {
  children: string
  icon: typeof Users
  id: string
  tone?: 'green' | 'gold'
}) {
  return (
    <div className="flex items-center gap-2 border-b border-stone pb-3">
      <Icon aria-hidden="true" size={17} className={tone === 'gold' ? 'text-campus-gold' : 'text-campus-green'} />
      <h2 id={id} className="font-serif text-lg font-semibold text-ink">{children}</h2>
    </div>
  )
}
