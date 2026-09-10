import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const sourcePath = fileURLToPath(new URL('../', import.meta.url))
const indexCss = readFileSync(new URL('../index.css', import.meta.url), 'utf8')
const tailwindConfig = readFileSync(
  new URL('../../tailwind.config.js', import.meta.url),
  'utf8',
)
const themeSources = `${indexCss}\n${tailwindConfig}`
const navbarSource = readFileSync(
  new URL('../components/Navbar.tsx', import.meta.url),
  'utf8',
)
const mainLayoutSource = readFileSync(
  new URL('../layouts/MainLayout.tsx', import.meta.url),
  'utf8',
)

test('theme sources define the approved campus identity tokens', () => {
  assert.match(themeSources, /#5B2A86/i, `${sourcePath} must define NJU purple`)
  assert.match(themeSources, /#175C4A/i, `${sourcePath} must define campus green`)
  assert.match(themeSources, /Noto Serif SC/, `${sourcePath} must define the title font`)
  assert.match(themeSources, /Noto Sans SC/, `${sourcePath} must define the UI font`)
  assert.match(
    tailwindConfig,
    /borderRadius\s*:\s*\{[\s\S]*?card\s*:\s*['"]8px['"]/,
    'Tailwind must expose an 8px card radius',
  )
})

test('global styles preserve keyboard focus and reduced-motion access', () => {
  assert.match(indexCss, /:focus-visible/, 'CSS must style keyboard focus')
  assert.match(
    indexCss,
    /@media\s*\(prefers-reduced-motion:\s*reduce\)/,
    'CSS must disable motion when reduced motion is requested',
  )
})

test('navbar preserves the five-route campus identity and accessible logout', () => {
  assert.match(
    navbarSource,
    /import\s+CampusMark\s+from\s+['"]@\/components\/CampusMark['"]/,
    'Navbar must use the shared campus mark',
  )
  assert.match(navbarSource, /<CampusMark\b/, 'Navbar must render CampusMark')

  for (const label of ['首页', '发现', '发布', '消息', '我的']) {
    assert.match(navbarSource, new RegExp(`label:\\s*['"]${label}['"]`))
  }

  assert.match(
    navbarSource,
    /<button[\s\S]*?aria-label=['"]退出登录['"][\s\S]*?onClick=\{handleLogout\}/,
    'Logout must remain an accessible button wired to the logout handler',
  )
})

test('desktop navbar has a medium-width fit strategy', () => {
  assert.match(
    navbarSource,
    /className=['"]lg:hidden['"][\s\S]*?<CampusMark\s+compact\s*\/>/,
    'Medium widths must keep a compact campus mark without the wordmark',
  )
  assert.match(
    navbarSource,
    /className=['"]hidden[^'"]*lg:inline-flex[^'"]*['"][\s\S]*?<CampusMark\s*\/>/,
    'Large widths may restore the full CampusMate wordmark',
  )
  assert.match(
    navbarSource,
    /<span\s+className=['"]hidden[^'"]*lg:block[^'"]*['"][^>]*>[\s\S]*?\{user\.nickname\}/,
    'Nickname text must stay hidden until large widths',
  )
  assert.match(
    navbarSource,
    /<nav[^>]*className=['"][^'"]*min-w-0[^'"]*gap-3[^'"]*lg:gap-6[^'"]*['"]/,
    'Desktop routes need a shrinkable nav region and responsive gaps',
  )
})

test('authenticated shell uses dynamic viewport height and mobile safe-area room', () => {
  assert.match(
    mainLayoutSource,
    /min-h-dvh/,
    'MainLayout must use the dynamic viewport-height shell',
  )
  assert.match(
    navbarSource,
    /env\(safe-area-inset-bottom\)/,
    'Mobile navigation must account for the bottom safe area',
  )
})
