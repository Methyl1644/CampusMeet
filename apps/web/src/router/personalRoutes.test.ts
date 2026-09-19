import { describe, expect, it } from 'vitest'
import { personalRedirectTarget } from '@/pages/ProfileRedirect'
import { readFileSync } from 'node:fs'

describe('legacy profile route compatibility', () => {
  it.each([
    ['?tab=events', '/my/activities'],
    ['?tab=groups', '/my/groups'],
    ['?view=notifications', '/notifications'],
    ['?view=settings', '/settings'],
    ['?view=public', '/users/me'],
    ['', '/users/me'],
    ['?view=unknown', '/users/me'],
  ])('maps %s to %s', (search, expected) => {
    expect(personalRedirectTarget(new URLSearchParams(search))).toBe(expected)
  })
})

describe('route recovery and personal management', () => {
  it('ships crawler and security-contact metadata as real static files', () => {
    const robots = readFileSync(new URL('../../public/robots.txt', import.meta.url), 'utf8')
    const security = readFileSync(new URL('../../public/.well-known/security.txt', import.meta.url), 'utf8')

    expect(robots).toContain('User-agent: *')
    expect(security).toContain('https://github.com/Methyl1644/EL_CampusMate/issues')
  })

  it('loads non-entry pages lazily to keep the first screen responsive', () => {
    const router = readFileSync(new URL('./index.tsx', import.meta.url), 'utf8')

    expect(router).toContain("const Discover = lazy(() => import('@/pages/Discover'))")
    expect(router).toContain('<Suspense fallback={<RouteLoading />}>' )
  })

  it('provides a branded error boundary and a catch-all route', () => {
    const router = readFileSync(new URL('./index.tsx', import.meta.url), 'utf8')

    expect(router).toContain('errorElement: <RouteError />')
    expect(router).toContain("path: '*'")
  })

  it('names the personal group entry as a publishing and team-management destination', () => {
    const menu = readFileSync(new URL('../components/navigation/UserMenu.tsx', import.meta.url), 'utf8')

    expect(menu).toContain('我的组队与发布')
  })
})
