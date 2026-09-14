import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Circle,
  ListChecks,
  ArrowDown,
  ArrowUp,
  Archive,
  Edit3,
  LogOut,
  MessageCircle,
  Plus,
  Phone,
  RefreshCw,
  Sparkles,
  Trash2,
  UserMinus,
  Users,
} from 'lucide-react'
import { generateTeamPlan } from '@/api/agent'
import { archiveTeam, createTask, deleteTask, editTask, getTeamDetail, leaveTeam, removeMember, reorderTasks, transferTeamOwner, updateMemberRole, updateTask } from '@/api/teams'
import type { Team } from '@shared/types'
import Loading from '@/components/Loading'
import { useDetailResource, useRouteGeneration } from '@/components/details/useDetailResource'
import { Reveal } from '@/components/motion/Reveal'
import { useToast } from '@/components/Toast'
import { useAuthStore } from '@/store/authStore'
import { getApiErrorMessage } from '@/api/auth-feedback'

export default function TeamDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const user = useAuthStore((state) => state.user)

  const { data: team, setData: setTeam, loading, error, retry } = useDetailResource(id ?? '', getTeamDetail)
  const routeOwner = useRouteGeneration(id ?? '')
  const [generatingPlanFor, setGeneratingPlanFor] = useState<{
    teamId: string
    routeGeneration: number
  } | null>(null)
  const taskMutationOwners = useRef(new Map<string, symbol>())
  const [pendingTaskKeys, setPendingTaskKeys] = useState<Set<string>>(() => new Set())
  const [manageBusy, setManageBusy] = useState(false)
  const [manageError, setManageError] = useState('')
  const [taskForm, setTaskForm] = useState({ id: '', title: '', assignee_id: '', due_at: '' })
  const [memberRoles, setMemberRoles] = useState<Record<string, string>>({})

  const handleToggleTask = async (taskId: string, currentDone: boolean) => {
    if (!team) return
    const sourceTeamId = team.id
    const routeGeneration = routeOwner.current.generation
    const key = `${sourceTeamId}:${routeGeneration}:${taskId}`
    if (taskMutationOwners.current.has(key)) return
    const owner = Symbol(key)
    taskMutationOwners.current.set(key, owner)
    setPendingTaskKeys((current) => new Set(current).add(key))
    const ownsMutation = () => (
      taskMutationOwners.current.get(key) === owner
      && routeOwner.current.key === sourceTeamId
      && routeOwner.current.generation === routeGeneration
    )
    setTeam((current) => current?.id === sourceTeamId ? {
      ...current,
      task_list: current.task_list.map((task) =>
        task.id === taskId ? { ...task, done: !currentDone } : task,
      ),
    } : current)
    try {
      const updated = await updateTask(sourceTeamId, taskId, !currentDone)
      if (!ownsMutation()) return
      setTeam((current) => current?.id === sourceTeamId ? {
        ...current,
        task_list: current.task_list.map((task) =>
          task.id === taskId ? { ...task, ...updated } : task,
        ),
      } : current)
    } catch {
      if (ownsMutation()) {
        setTeam((current) => current?.id === sourceTeamId ? {
          ...current,
          task_list: current.task_list.map((task) =>
            task.id === taskId ? { ...task, done: currentDone } : task,
          ),
        } : current)
        showToast('更新失败', 'error')
      }
    } finally {
      if (taskMutationOwners.current.get(key) === owner) {
        taskMutationOwners.current.delete(key)
        setPendingTaskKeys((current) => {
          const next = new Set(current)
          next.delete(key)
          return next
        })
      }
    }
  }

  const handleToggleAgenda = (agendaId: string) => {
    if (!team) return
    setTeam((current) => current?.id === team.id ? {
      ...current,
      meeting_agenda: current.meeting_agenda.map((agenda) =>
        agenda.id === agendaId ? { ...agenda, done: !agenda.done } : agenda,
      ),
    } : current)
  }

  const hasTeamPlan = Boolean(
    team &&
      (team.division_of_labor.length > 0 ||
        team.meeting_agenda.length > 0 ||
        team.task_list.length > 0 ||
        team.risk_reminders.length > 0),
  )

  const handleGeneratePlan = async () => {
    if (!team) return
    const sourceTeamId = team.id
    const routeGeneration = routeOwner.current.generation
    if (
      generatingPlanFor?.teamId === sourceTeamId &&
      generatingPlanFor.routeGeneration === routeGeneration
    ) return
    const ownsRoute = () => (
      routeOwner.current.key === sourceTeamId && routeOwner.current.generation === routeGeneration
    )
    const isRegeneration = hasTeamPlan
    setGeneratingPlanFor({ teamId: sourceTeamId, routeGeneration })
    try {
      const plan = await generateTeamPlan(sourceTeamId)
      if (!ownsRoute()) return
      setTeam((current) =>
        current?.id === sourceTeamId
          ? {
              ...current,
              division_of_labor: plan.division_of_labor,
              meeting_agenda: plan.meeting_agenda,
              task_list: plan.task_list,
              risk_reminders: plan.risk_reminders,
            }
          : current,
      )
      showToast(isRegeneration ? '团队规划已重新生成' : '团队规划已生成', 'success')
    } catch {
      if (ownsRoute()) {
        showToast('规划生成失败，已保留当前内容，请稍后重试', 'error')
      }
    } finally {
      setGeneratingPlanFor((current) => (
        current?.teamId === sourceTeamId && current.routeGeneration === routeGeneration ? null : current
      ))
    }
  }

  const refreshTeam = async () => {
    if (!team) return
    setTeam(await getTeamDetail(team.id))
  }

  const runManagement = async (
    operation: () => Promise<unknown>,
    success: string,
    refresh = true,
    afterSuccess?: () => void,
  ) => {
    setManageBusy(true); setManageError('')
    try {
      await operation()
      if (refresh) await refreshTeam()
      showToast(success, 'success')
      afterSuccess?.()
    }
    catch (requestError) { setManageError(getApiErrorMessage(requestError, '团队操作失败')) }
    finally { setManageBusy(false) }
  }

  const saveTask = async () => {
    if (!team || !taskForm.title.trim()) return
    const body = { title: taskForm.title.trim(), assignee_id: taskForm.assignee_id ? Number(taskForm.assignee_id) : null, due_at: taskForm.due_at }
    await runManagement(() => taskForm.id ? editTask(team.id, taskForm.id, body) : createTask(team.id, body), taskForm.id ? '任务已更新' : '任务已添加')
    setTaskForm({ id: '', title: '', assignee_id: '', due_at: '' })
  }

  const moveTask = async (taskId: string, direction: -1 | 1) => {
    if (!team) return
    const ids = team.task_list.map((task) => task.id)
    const index = ids.indexOf(taskId); const target = index + direction
    if (index < 0 || target < 0 || target >= ids.length) return
    ;[ids[index], ids[target]] = [ids[target], ids[index]]
    await runManagement(() => reorderTasks(team.id, ids), '任务顺序已更新')
  }

  if (loading) return <Loading />
  if (error) {
    return (
      <div role="alert" className="mx-auto max-w-xl border-y border-stone bg-paper px-5 py-12 text-center">
        <p className="text-base font-semibold text-ink">团队加载失败</p>
        <p className="mt-2 text-sm text-ink-muted">网络可能暂时不可用，请重试。</p>
        <button type="button" onClick={retry} className="btn-primary mt-5 min-h-11">
          <RefreshCw aria-hidden="true" size={16} />重新加载
        </button>
      </div>
    )
  }
  if (!team) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-ink-muted">团队不存在</p>
        <button onClick={() => navigate('/profile')} className="btn-secondary mt-4">返回</button>
      </div>
    )
  }

  const generatingPlan = (
    generatingPlanFor?.teamId === team.id &&
    generatingPlanFor.routeGeneration === routeOwner.current.generation
  )
  const isOwner = Boolean(user && (team.owner_id === user.id || team.members.some((member) => member.user.id === user.id && member.member_role === 'owner')))

  return (
    <div data-testid="team-detail-page" className="mx-auto min-w-0 max-w-5xl overflow-x-clip pb-8">
      <button
        onClick={() => navigate(-1)}
        className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-ink-muted transition-colors hover:text-primary-700"
      >
        <ArrowLeft aria-hidden="true" size={16} />
        返回
      </button>

      <Reveal as="header" className="border-y border-stone bg-paper px-4 py-6 sm:px-7 lg:py-8">
        <p className="section-label">团队工作台</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="break-words text-2xl font-bold leading-9 text-ink sm:text-3xl">
              {team.activity_name}
            </h1>
            <p className="mt-2 text-sm text-ink-muted">建立于 {team.created_at || '暂无'}</p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <span className="text-sm font-semibold tabular-nums text-campus-green">
              {team.members.length} 位成员
            </span>
            <button
              type="button"
              onClick={handleGeneratePlan}
              disabled={generatingPlan}
              className="btn-secondary min-h-10 whitespace-nowrap px-3"
            >
              {generatingPlan ? (
                <RefreshCw aria-hidden="true" size={16} className="animate-spin" />
              ) : (
                <Sparkles aria-hidden="true" size={16} />
              )}
              {generatingPlan
                ? '正在生成...'
                : hasTeamPlan
                  ? '重新生成规划'
                  : '生成团队规划'}
            </button>
            {isOwner ? <button type="button" className="btn-secondary min-h-10" disabled={manageBusy} onClick={() => { if (window.confirm('确认归档该团队？')) void runManagement(() => archiveTeam(team.id), '团队已归档', false, () => navigate('/profile?view=teams')) }}><Archive aria-hidden="true" size={16} />归档团队</button> : <button type="button" className="btn-secondary min-h-10" disabled={manageBusy} onClick={() => { if (window.confirm('确认退出该团队？')) void runManagement(() => leaveTeam(team.id), '已退出团队', false, () => navigate('/profile?view=teams')) }}><LogOut aria-hidden="true" size={16} />退出团队</button>}
          </div>
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
                    {isOwner && member.member_role !== 'owner' ? <div className="flex flex-wrap items-center justify-end gap-2"><input aria-label={`调整 ${member.user.nickname} 的角色`} className="input-base min-h-9 w-28 px-2 py-1 text-xs" value={memberRoles[member.user.id] ?? member.suggested_role} onChange={(event) => setMemberRoles((current) => ({ ...current, [member.user.id]: event.target.value }))} /><button type="button" className="icon-button" title="保存成员角色" disabled={manageBusy} onClick={() => void runManagement(() => updateMemberRole(team.id, member.user.id, memberRoles[member.user.id] ?? member.suggested_role), '成员角色已更新')}><Edit3 aria-hidden="true" className="size-4" /><span className="sr-only">保存成员角色</span></button><button type="button" className="icon-button" title="转让负责人" disabled={manageBusy} onClick={() => { if (window.confirm(`确认将负责人转让给 ${member.user.nickname}？`)) void runManagement(() => transferTeamOwner(team.id, member.user.id), '负责人已转让') }}><Users aria-hidden="true" className="size-4" /><span className="sr-only">转让负责人</span></button><button type="button" className="icon-button text-red-700" title="移除成员" disabled={manageBusy} onClick={() => { if (window.confirm(`确认移除 ${member.user.nickname}？`)) void runManagement(() => removeMember(team.id, member.user.id), '成员已移除') }}><UserMinus aria-hidden="true" className="size-4" /><span className="sr-only">移除成员</span></button></div> : <span className="shrink-0 text-xs font-semibold text-primary-700">{member.suggested_role || '暂无'}</span>}
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
            {isOwner && <div className="mt-3 grid gap-2 border-y border-stone bg-paper p-3 sm:grid-cols-[minmax(0,1fr)_minmax(9rem,0.7fr)_minmax(8rem,0.6fr)_auto]"><input aria-label="任务标题" className="input-base" placeholder="任务标题" value={taskForm.title} onChange={(event) => setTaskForm({ ...taskForm, title: event.target.value })} /><select aria-label="任务负责人" className="input-base" value={taskForm.assignee_id} onChange={(event) => setTaskForm({ ...taskForm, assignee_id: event.target.value })}><option value="">暂不分配</option>{team.members.map((member) => <option key={member.user.id} value={member.user.id}>{member.user.nickname}</option>)}</select><input aria-label="任务截止时间" className="input-base" placeholder="截止时间" value={taskForm.due_at} onChange={(event) => setTaskForm({ ...taskForm, due_at: event.target.value })} /><button type="button" className="btn-primary" disabled={manageBusy || !taskForm.title.trim()} onClick={() => void saveTask()}><Plus aria-hidden="true" className="size-4" />{taskForm.id ? '保存' : '添加'}</button></div>}
            {team.task_list.length > 0 ? (
              <div className="mt-3 divide-y divide-stone border-y border-stone">
                {team.task_list.map((task) => (
                  <div
                    key={task.id}
                    className="flex min-h-16 w-full items-center gap-2 px-1 py-2"
                  >
                    <button onClick={() => handleToggleTask(task.id, task.done)} aria-pressed={task.done} disabled={pendingTaskKeys.has(`${team.id}:${routeOwner.current.generation}:${task.id}`)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
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
                        <span>截止：{task.due_at || task.deadline || '暂无'}</span>
                      </div>
                    </div></button>
                    {isOwner && <div className="flex shrink-0"><button type="button" className="icon-button" title="编辑任务" onClick={() => setTaskForm({ id: task.id, title: task.title, assignee_id: task.assignee_id || '', due_at: task.due_at || task.deadline || '' })}><Edit3 aria-hidden="true" className="size-4" /><span className="sr-only">编辑任务</span></button><button type="button" className="icon-button" title="上移任务" onClick={() => void moveTask(task.id, -1)}><ArrowUp aria-hidden="true" className="size-4" /><span className="sr-only">上移任务</span></button><button type="button" className="icon-button" title="下移任务" onClick={() => void moveTask(task.id, 1)}><ArrowDown aria-hidden="true" className="size-4" /><span className="sr-only">下移任务</span></button><button type="button" className="icon-button text-red-700" title="删除任务" onClick={() => { if (window.confirm('确认删除该任务？')) void runManagement(() => deleteTask(team.id, task.id), '任务已删除') }}><Trash2 aria-hidden="true" className="size-4" /><span className="sr-only">删除任务</span></button></div>}
                  </div>
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
              </div>
            )}
          </Reveal>
        </aside>
      </div>
      {manageError && <p role="alert" className="mt-5 rounded-card border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{manageError}</p>}
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
