// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Publish from './Publish'
import { postDraft } from '@/api/agent'
import { createPost } from '@/api/posts'
import { getPublishContext } from '@/api/publish'
import { completeness, emptyDraft, missingFields } from '@/features/publish/publishState'
import type { PublishContext } from '@/features/publish/publishState'

vi.mock('@/api/agent', () => ({ postDraft: vi.fn() }))
vi.mock('@/api/posts', () => ({ createPost: vi.fn() }))
vi.mock('@/api/publish', () => ({ getPublishContext: vi.fn(), uploadPostCover: vi.fn() }))
vi.mock('@/store/authStore', () => ({ useAuthStore: Object.assign((selector: (s: unknown) => unknown) => selector({ user: { id: '1' } }), { subscribe: () => () => {} }) }))

const context: PublishContext = { kind: 'casual_invitation', topic_id: null, activity: null, allowed_purposes: ['team_recruitment', 'discussion'], default_purpose: 'team_recruitment', permission_explanations: {}, inherited_tags: [], defaults: {}, revision: 'r1', max_members: 100 }
const completeDraft = { activity_name: '周末羽毛球', target_members: 4, needed_roles: [], weekly_hours: '周六下午', school_scope: '仙林体育馆', deadline: '', description: '一起运动' }
const completeResponse = { draft: completeDraft, field_states: { needed_roles: { value: [], status: 'none' as const } }, is_complete: true, reply: '资料整理好了，请检查和修改。', candidate_tags: [], suggested_tag_ids: [] }

beforeEach(() => { vi.clearAllMocks(); sessionStorage.clear(); vi.mocked(getPublishContext).mockResolvedValue(context) })
afterEach(cleanup)
async function open() { render(<MemoryRouter><Publish /></MemoryRouter>); await screen.findByLabelText('描述你的想法') }
async function send() { fireEvent.change(screen.getByLabelText('描述你的想法'), { target: { value: '周末想打羽毛球' } }); fireEvent.click(screen.getByRole('button', { name: '发送' })) }

describe('conversational publishing', () => {
  it('keeps the form hidden until review and synchronizes growth', async () => {
    await open()
    expect(screen.queryByLabelText(/活动名称/)).toBeNull()
    expect(document.querySelector('.publish-plant-border')).toBeTruthy()
    expect(document.querySelector('.campus-growth')).toBeTruthy()
    vi.mocked(postDraft).mockResolvedValue(completeResponse)
    await send()
    expect(await screen.findByRole('heading', { name: '请检查和修改' })).toBeTruthy()
    expect((screen.getByLabelText(/活动名称/) as HTMLInputElement).value).toBe('周末羽毛球')
  })
  it('keeps whale waiting inside the conversation until the request resolves', async () => {
    let resolve!: (response: typeof completeResponse) => void
    vi.mocked(postDraft).mockReturnValue(new Promise((done) => { resolve = done }))
    await open(); await send()
    expect(document.querySelector('.whale-overlay')).toBeTruthy()
    expect((screen.getByRole('button', { name: '发送' }) as HTMLButtonElement).disabled).toBe(true)
    await act(async () => resolve(completeResponse))
    expect(document.querySelector('.whale-overlay')).toBeNull()
  })
  it('retains conversation on error and retries without duplicating the user message', async () => {
    vi.mocked(postDraft).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ ...completeResponse, is_complete: false })
    await open(); await send()
    fireEvent.click(await screen.findByRole('button', { name: '重试回复' }))
    await waitFor(() => expect(postDraft).toHaveBeenCalledTimes(2))
    expect(screen.getAllByText('周末想打羽毛球')).toHaveLength(1)
  })
  it('does not trust a complete flag when required data is missing', async () => {
    vi.mocked(postDraft).mockResolvedValue({ ...completeResponse, draft: { ...completeDraft, target_members: 0 } })
    await open(); await send()
    await waitFor(() => expect(postDraft).toHaveBeenCalled())
    expect(screen.queryByRole('heading', { name: '请检查和修改' })).toBeNull()
  })
  it('reuses the publish key after an uncertain result and never publishes before confirmation', async () => {
    vi.mocked(postDraft).mockResolvedValue(completeResponse)
    vi.mocked(createPost).mockRejectedValueOnce(new Error('timeout')).mockResolvedValueOnce({ id: '42' } as never)
    await open(); await send()
    const button = await screen.findByRole('button', { name: '确认发布' })
    expect(createPost).not.toHaveBeenCalled()
    fireEvent.click(button)
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: '确认发布' }))
    await screen.findByText('发布成功，等伙伴来相遇')
    expect(vi.mocked(createPost).mock.calls[0][0].client_request_id).toBe(vi.mocked(createPost).mock.calls[1][0].client_request_id)
    expect(sessionStorage.length).toBe(0)
  })
  it('supports discussion without requiring hidden recruitment fields', async () => {
    vi.mocked(createPost).mockResolvedValue({ id: '43' } as never)
    await open(); fireEvent.click(screen.getByRole('button', { name: '经验交流' }))
    fireEvent.click(screen.getByRole('button', { name: '手动完善资料' }))
    fireEvent.change(screen.getByLabelText(/活动名称/), { target: { value: '比赛经验' } })
    fireEvent.change(screen.getByLabelText(/介绍与参与说明/), { target: { value: '想请教准备方法' } })
    fireEvent.click(screen.getByRole('button', { name: '确认发布' }))
    await waitFor(() => expect(createPost).toHaveBeenCalled())
    expect(vi.mocked(createPost).mock.calls[0][0].target_members).toBe(1)
    expect(vi.mocked(createPost).mock.calls[0][0].purpose).toBe('discussion')
  })
  it('counts confirmed fields, not elapsed time or skipped answers', () => {
    expect(completeness(emptyDraft, {}, context, 'team_recruitment')).toBe(0)
    expect(missingFields(completeDraft, { needed_roles: { value: [], status: 'none' }, school_scope: { value: '仙林', status: 'unknown' } }, context, 'team_recruitment')).toEqual(['school_scope'])
    expect(completeness(completeDraft, { needed_roles: { value: [], status: 'none' } }, context, 'team_recruitment')).toBe(1)
  })
})
