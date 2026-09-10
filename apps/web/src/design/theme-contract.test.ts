import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
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
const discoveryHubSource = readFileSync(
  new URL('../components/DiscoveryHub.tsx', import.meta.url),
  'utf8',
)
const topicCardUrl = new URL('../components/TopicCard.tsx', import.meta.url)
const topicCardSource = existsSync(topicCardUrl)
  ? readFileSync(topicCardUrl, 'utf8')
  : ''

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

test('discovery preserves the approved channel and search hierarchy', () => {
  const channelTitles = [
    ...discoveryHubSource.matchAll(
      /\{\s*key:\s*['"](?:official|organization|casual)['"],\s*title:\s*['"]([^'"]+)['"]/g,
    ),
  ].map((match) => match[1])

  assert.deepEqual(channelTitles, [
    '官方赛事与项目',
    '认证组织活动',
    '同学自主组队',
  ])
  assert.equal(
    [...discoveryHubSource.matchAll(/<input\b/g)].length,
    1,
    'DiscoveryHub must render a single search input',
  )
  const directTopicPosition = discoveryHubSource.search(/>\s*话题直达\s*</)
  const standardTagPosition = discoveryHubSource.search(/>\s*标准标签\s*</)
  assert.ok(
    directTopicPosition >= 0 &&
      standardTagPosition >= 0 &&
      directTopicPosition < standardTagPosition,
    'Direct topic results must render before standard tags',
  )
  assert.match(
    discoveryHubSource,
    /aria-label=['"]已选择标签['"][\s\S]*?setSelectedTags\([\s\S]*?filter\([\s\S]*?aria-label=\{`移除\$\{tag\.canonical_name\}`\}/,
    'Selected standard tags must expose an X removal control',
  )
  assert.match(
    discoveryHubSource,
    /import\s+TopicCard\s+from\s+['"]@\/components\/TopicCard['"]/,
    'DiscoveryHub must import TopicCard',
  )
})

test('topic cards exist and link to topic detail routes', () => {
  assert.ok(existsSync(topicCardUrl), 'TopicCard.tsx must exist')
  assert.match(
    topicCardSource,
    /to=\{`\/topics\/\$\{topic\.id\}`\}/,
    'TopicCard must link to /topics/:id',
  )
})

test('discovery list loading commits only the latest request', () => {
  assert.match(
    discoveryHubSource,
    /const\s+loadRequestId\s*=\s*useRef\(0\)/,
    'List loading needs a request guard independent from suggestions',
  )
  assert.match(
    discoveryHubSource,
    /const\s+load\s*=\s*useCallback\(async\s*\(currentLoad:\s*number\)\s*=>/,
    'The delayed list load must receive the dependency generation',
  )
  assert.match(
    discoveryHubSource,
    /useEffect\(\(\)\s*=>\s*\{\s*const\s+currentLoad\s*=\s*\+\+loadRequestId\.current\s*const\s+timer\s*=\s*window\.setTimeout\(\(\)\s*=>\s*load\(currentLoad\),\s*250\)/,
    'Dependency changes must invalidate prior list requests before the debounce timer',
  )
  assert.match(
    discoveryHubSource,
    /getPosts\([\s\S]*?if\s*\(currentLoad\s*===\s*loadRequestId\.current\)\s*\{[\s\S]*?setPosts\(response\.list\)[\s\S]*?setTopics\(\[\]\)[\s\S]*?\}/,
    'Casual list success must be latest-request guarded',
  )
  assert.match(
    discoveryHubSource,
    /getTopics\([\s\S]*?if\s*\(currentLoad\s*===\s*loadRequestId\.current\)\s*\{[\s\S]*?setTopics\(response\.list\)[\s\S]*?setPosts\(\[\]\)[\s\S]*?\}/,
    'Topic list success must be latest-request guarded',
  )
  assert.match(
    discoveryHubSource,
    /catch\s*\{\s*if\s*\(currentLoad\s*===\s*loadRequestId\.current\)\s*\{[\s\S]*?setTopics\(\[\]\)[\s\S]*?setPosts\(\[\]\)[\s\S]*?showToast\(/,
    'List errors must be latest-request guarded',
  )
  assert.match(
    discoveryHubSource,
    /finally\s*\{\s*if\s*\(currentLoad\s*===\s*loadRequestId\.current\)\s+setLoading\(false\)/,
    'Only the latest list request may clear loading',
  )
})
