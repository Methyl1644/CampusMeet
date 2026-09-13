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
  return <button type="button" onClick={() => navigate('/teams/team-2')}>打开另一个团队</button>
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
})
