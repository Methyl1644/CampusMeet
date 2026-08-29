import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Users, ListChecks, Calendar, AlertTriangle, Phone, MessageCircle, CheckCircle2, Circle } from 'lucide-react'
import { getTeamDetail, updateTask } from '@/api/teams'
import type { Team } from '@shared/types'
import Loading from '@/components/Loading'
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
    // 乐观更新
    setTeam({
      ...team,
      task_list: team.task_list.map((t) =>
        t.id === taskId ? { ...t, done: !currentDone } : t,
      ),
    })
    try {
      await updateTask(team.id, taskId, !currentDone)
    } catch {
      // 回滚
      setTeam({
        ...team,
        task_list: team.task_list.map((t) =>
          t.id === taskId ? { ...t, done: currentDone } : t,
        ),
      })
      showToast('更新失败', 'error')
    }
  }

  const handleToggleAgenda = (agendaId: string) => {
    if (!team) return
    setTeam({
      ...team,
      meeting_agenda: team.meeting_agenda.map((a) =>
        a.id === agendaId ? { ...a, done: !a.done } : a,
      ),
    })
  }

  if (loading) return <Loading />
  if (!team) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-gray-500">团队不存在</p>
        <button onClick={() => navigate('/profile')} className="btn-secondary mt-4">返回</button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <button
        onClick={() => navigate(-1)}
        className="mb-3 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft size={16} />
        返回
      </button>

      {/* 团队头部 */}
      <div className="card mb-3">
        <h1 className="mb-3 text-lg font-bold text-gray-900">{team.activity_name}</h1>
        <div className="flex flex-wrap gap-2">
          {team.members.map((member) => (
            <div key={member.user.id} className="flex items-center gap-2 rounded-lg bg-gray-50 px-3 py-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-xs font-medium text-primary-600">
                {member.user.nickname.charAt(0)}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">{member.user.nickname}</p>
                <p className="text-xs text-primary-600">{member.suggested_role}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI 分工建议 */}
      <div className="card mb-3">
        <div className="mb-3 flex items-center gap-2">
          <Users size={18} className="text-primary-600" />
          <h2 className="text-sm font-semibold text-gray-900">AI 分工建议</h2>
        </div>
        <div className="space-y-2">
          {team.division_of_labor.map((item, idx) => (
            <div key={idx} className="rounded-lg bg-gray-50 p-3">
              <p className="text-sm font-medium text-gray-900">{item.role}</p>
              <p className="mt-0.5 text-xs text-gray-600">{item.responsibilities}</p>
              {item.member_id && (
                <p className="mt-1 text-xs text-primary-600">
                  → {team.members.find((m) => m.user.id === item.member_id)?.user.nickname || '待分配'}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 首次会议议程 */}
      <div className="card mb-3">
        <div className="mb-3 flex items-center gap-2">
          <ListChecks size={18} className="text-primary-600" />
          <h2 className="text-sm font-semibold text-gray-900">首次会议议程</h2>
        </div>
        <div className="space-y-2">
          {team.meeting_agenda.map((item) => (
            <button
              key={item.id}
              onClick={() => handleToggleAgenda(item.id)}
              className="flex w-full items-start gap-2 rounded-lg p-2 text-left hover:bg-gray-50"
            >
              {item.done ? (
                <CheckCircle2 size={18} className="mt-0.5 text-green-500" />
              ) : (
                <Circle size={18} className="mt-0.5 text-gray-300" />
              )}
              <span className={`text-sm ${item.done ? 'text-gray-400 line-through' : 'text-gray-700'}`}>
                {item.content}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* 任务清单 */}
      <div className="card mb-3">
        <div className="mb-3 flex items-center gap-2">
          <Calendar size={18} className="text-primary-600" />
          <h2 className="text-sm font-semibold text-gray-900">任务清单</h2>
        </div>
        <div className="space-y-2">
          {team.task_list.map((task) => (
            <button
              key={task.id}
              onClick={() => handleToggleTask(task.id, task.done)}
              className="flex w-full items-start gap-2 rounded-lg p-2 text-left hover:bg-gray-50"
            >
              {task.done ? (
                <CheckCircle2 size={18} className="mt-0.5 text-green-500" />
              ) : (
                <Circle size={18} className="mt-0.5 text-gray-300" />
              )}
              <div className="flex-1">
                <span className={`text-sm ${task.done ? 'text-gray-400 line-through' : 'text-gray-700'}`}>
                  {task.title}
                </span>
                <div className="mt-0.5 flex gap-3 text-xs text-gray-400">
                  {task.assignee_name && <span>负责人：{task.assignee_name}</span>}
                  {task.deadline && <span>截止：{task.deadline}</span>}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 风险提醒 */}
      {team.risk_reminders.length > 0 && (
        <div className="card mb-3 border-orange-200 bg-orange-50">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle size={18} className="text-orange-500" />
            <h2 className="text-sm font-semibold text-gray-900">风险提醒</h2>
          </div>
          <ul className="space-y-1">
            {team.risk_reminders.map((reminder, idx) => (
              <li key={idx} className="flex items-start gap-2 text-xs text-orange-700">
                <span className="mt-0.5">•</span>
                {reminder}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 联系方式 */}
      <div className="card">
        <div className="mb-3 flex items-center gap-2">
          <Phone size={18} className="text-primary-600" />
          <h2 className="text-sm font-semibold text-gray-900">联系方式</h2>
        </div>
        {team.contact_info.length > 0 ? (
          <div className="space-y-2">
            {team.contact_info.map((contact) => (
              <div key={contact.user_id} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                <span className="text-sm font-medium text-gray-900">{contact.nickname}</span>
                <div className="flex gap-3 text-xs text-gray-600">
                  {contact.phone && (
                    <span className="flex items-center gap-1">
                      <Phone size={12} />
                      {contact.phone}
                    </span>
                  )}
                  {contact.wechat && (
                    <span className="flex items-center gap-1">
                      <MessageCircle size={12} />
                      {contact.wechat}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-gray-400">
            双方确认组队后将解锁联系方式
          </p>
        )}
      </div>
    </div>
  )
}
