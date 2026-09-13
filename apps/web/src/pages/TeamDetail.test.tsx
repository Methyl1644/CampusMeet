// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { generateTeamPlan } from '@/api/agent'
import { getTeamDetail, updateTask } from '@/api/teams'
import { ToastProvider } from '@/components/Toast'
import TeamDetail from './TeamDetail'
import { teamFixture } from './detailTestFixtures'

vi.mock('@/api/agent', () => ({ generateTeamPlan: vi.fn() }))
vi.mock('@/api/teams', () => ({ getTeamDetail: vi.fn(), updateTask: vi.fn() }))

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolvePromise) => { resolve = resolvePromise })
  return { promise, resolve }
}

function RouteChange() {
  const navigate = useNavigate()
  return (
    <>
      <button type="button" onClick={() => navigate('/teams/team-2')}>打开另一个团队</button>
      <button type="button" onClick={() => navigate('/teams/team-1')}>返回原团队</button>
    </>
  )
}

function renderTeam() {
  return render(
    <MemoryRouter initialEntries={['/teams/team-1']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <RouteChange />
        <Routes><Route path="/teams/:id" element={<TeamDetail />} /></Routes>
      </ToastProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getTeamDetail).mockResolvedValue(teamFixture)
  vi.mocked(updateTask).mockResolvedValue({ ...teamFixture.task_list[0], done: true })
  vi.mocked(generateTeamPlan).mockResolvedValue({
    division_of_labor: teamFixture.division_of_labor,
    meeting_agenda: teamFixture.meeting_agenda,
    task_list: teamFixture.task_list,
    risk_reminders: teamFixture.risk_reminders,
  })
})

afterEach(() => cleanup())

describe('TeamDetail consistency', () => {
  it('keeps the collaboration controls keyboard-operable inside the restrained detail hierarchy', async () => {
    renderTeam()
    expect(await screen.findByRole('heading', { level: 1, name: teamFixture.activity_name })).toBeTruthy()
    expect(screen.getByRole('button', { name: '重新生成规划' })).toBeTruthy()
    const task = screen.getByRole('button', { name: /完成原型/ })
    task.focus()
    fireEvent.keyDown(task, { key: 'Enter' })
    fireEvent.click(task)
    expect(updateTask).toHaveBeenCalledWith('team-1', 'task-1', true)
  })

  it('shows a retryable in-page error and ignores stale route responses', async () => {
    vi.mocked(getTeamDetail).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(teamFixture)
    renderTeam()
    expect((await screen.findByRole('alert')).textContent).toContain('团队加载失败')
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    expect(await screen.findByRole('heading', { name: teamFixture.activity_name })).toBeTruthy()

    cleanup()
    const stale = deferred<typeof teamFixture>()
    const current = { ...teamFixture, id: 'team-2', activity_name: '当前团队工作台' }
    vi.mocked(getTeamDetail).mockReturnValueOnce(stale.promise).mockResolvedValueOnce(current)
    renderTeam()
    fireEvent.click(screen.getByRole('button', { name: '打开另一个团队' }))
    expect(await screen.findByRole('heading', { name: current.activity_name })).toBeTruthy()
    await act(async () => { stale.resolve(teamFixture); await stale.promise })
    expect(screen.queryByText(teamFixture.activity_name)).toBeNull()
  })

  it('keeps an older plan mutation from owning the next team state or feedback', async () => {
    const oldPlan = deferred<Awaited<ReturnType<typeof generateTeamPlan>>>()
    const current = {
      ...teamFixture,
      id: 'team-2',
      activity_name: '当前团队工作台',
      division_of_labor: [{ role: '当前团队策划', responsibilities: '保留当前团队规划' }],
    }
    vi.mocked(getTeamDetail).mockResolvedValueOnce(teamFixture).mockResolvedValueOnce(current)
    vi.mocked(generateTeamPlan).mockReturnValueOnce(oldPlan.promise)
    renderTeam()

    fireEvent.click(await screen.findByRole('button', { name: '重新生成规划' }))
    fireEvent.click(screen.getByRole('button', { name: '打开另一个团队' }))
    expect(await screen.findByRole('heading', { name: current.activity_name })).toBeTruthy()
    expect(screen.getByRole('button', { name: '重新生成规划' }).hasAttribute('disabled')).toBe(false)

    await act(async () => {
      oldPlan.resolve({
        division_of_labor: [{ role: '旧团队规划', responsibilities: '不应写入新团队' }],
        meeting_agenda: [],
        task_list: [],
        risk_reminders: [],
      })
      await oldPlan.promise
    })

    expect(screen.getByText('当前团队策划')).toBeTruthy()
    expect(screen.queryByText('旧团队规划')).toBeNull()
    expect(screen.queryByText('团队规划已重新生成')).toBeNull()
  })

  it('does not let an old A plan commit or clear a fresh A plan after A to B to A navigation', async () => {
    const oldPlan = deferred<Awaited<ReturnType<typeof generateTeamPlan>>>()
    const freshPlan = deferred<Awaited<ReturnType<typeof generateTeamPlan>>>()
    const teamB = { ...teamFixture, id: 'team-2', activity_name: '中间团队' }
    const freshA = {
      ...teamFixture,
      activity_name: '重新进入的原团队',
      division_of_labor: [{ role: '重访基线', responsibilities: '保留重访状态' }],
    }
    vi.mocked(getTeamDetail)
      .mockResolvedValueOnce(teamFixture)
      .mockResolvedValueOnce(teamB)
      .mockResolvedValueOnce(freshA)
    vi.mocked(generateTeamPlan).mockReturnValueOnce(oldPlan.promise).mockReturnValueOnce(freshPlan.promise)
    renderTeam()

    fireEvent.click(await screen.findByRole('button', { name: '重新生成规划' }))
    fireEvent.click(screen.getByRole('button', { name: '打开另一个团队' }))
    expect(await screen.findByRole('heading', { name: teamB.activity_name })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '返回原团队' }))
    expect(await screen.findByRole('heading', { name: freshA.activity_name })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '重新生成规划' }))
    expect(screen.getByRole('button', { name: '正在生成...' }).hasAttribute('disabled')).toBe(true)

    await act(async () => {
      oldPlan.resolve({
        division_of_labor: [{ role: '旧访问规划', responsibilities: '不得写入重访页面' }],
        meeting_agenda: [],
        task_list: [],
        risk_reminders: [],
      })
      await oldPlan.promise
    })

    expect(screen.getByText('重访基线')).toBeTruthy()
    expect(screen.queryByText('旧访问规划')).toBeNull()
    expect(screen.getByRole('button', { name: '正在生成...' }).hasAttribute('disabled')).toBe(true)
    expect(screen.queryByText('团队规划已重新生成')).toBeNull()

    await act(async () => {
      freshPlan.resolve({
        division_of_labor: [{ role: '新一轮团队规划', responsibilities: '只写入当前访问' }],
        meeting_agenda: [],
        task_list: [],
        risk_reminders: [],
      })
      await freshPlan.promise
    })
    expect(await screen.findByText('新一轮团队规划')).toBeTruthy()
  })
})
