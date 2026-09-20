// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { matchPosts } from '@/api/agent'
import PostMatchPanel from './PostMatchPanel'

vi.mock('@/api/agent', () => ({ matchPosts: vi.fn() }))

function renderPanel() {
  return render(<MemoryRouter><PostMatchPanel postId="3" /></MemoryRouter>)
}

describe('PostMatchPanel', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('recommends teammates with score, reason and public profile detail', async () => {
    vi.mocked(matchPosts).mockResolvedValue({
      matches: [{
        user_id: '2', nickname: '林晓', score: 88, reason: '技能覆盖所需的前端开发角色',
        major: '计算机科学与技术', grade: '大二', skills: ['React', 'TypeScript'],
      }],
    })

    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: /推荐队友/ }))

    expect(await screen.findByText('林晓')).toBeTruthy()
    expect(screen.getByText(/技能覆盖所需的前端开发角色/)).toBeTruthy()
    expect(screen.getByText('88% 匹配')).toBeTruthy()
    expect(screen.getByText('React')).toBeTruthy()
    expect(screen.getByRole('link', { name: '查看主页' }).getAttribute('href')).toBe('/users/2')
  })

  it('never renders contact details from the public profile', async () => {
    vi.mocked(matchPosts).mockResolvedValue({
      matches: [{
        user_id: '2', nickname: '林晓', score: 75, reason: '专业相关', skills: [],
        contact: { wechat: 'linxiao_wx' },
      } as never],
    })

    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: /推荐队友/ }))

    expect(await screen.findByText('林晓')).toBeTruthy()
    expect(screen.queryByText(/linxiao_wx/)).toBeNull()
  })

  it('reports when the candidate pool is empty', async () => {
    vi.mocked(matchPosts).mockResolvedValue({ matches: [] })

    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: /推荐队友/ }))

    expect(await screen.findByText(/暂无可推荐的候选人/)).toBeTruthy()
  })
})
