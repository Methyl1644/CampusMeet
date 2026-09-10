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
const loginSource = readFileSync(
  new URL('../pages/Login.tsx', import.meta.url),
  'utf8',
)
const publishSource = readFileSync(
  new URL('../pages/Publish.tsx', import.meta.url),
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

test('authentication keeps every stage inside the approved campus composition', () => {
  assert.match(
    loginSource,
    /import\s+CampusMark\s+from\s+['"]@\/components\/CampusMark['"]/,
    'Login must use the shared campus mark',
  )
  assert.match(loginSource, /<CampusMark\b/, 'Login must render CampusMark')
  assert.match(
    loginSource,
    /type\s+Step\s*=\s*['"]login['"]\s*\|\s*['"]register['"]\s*\|\s*['"]profile['"]\s*\|\s*['"]verify['"]/,
    'Login must preserve login, register, profile, and verify states',
  )
  assert.match(
    loginSource,
    /<AnimatePresence\b[\s\S]*?<motion\.(?:div|section|form)\b/,
    'Authentication stages must transition through Motion AnimatePresence',
  )
  assert.match(
    loginSource,
    /enter:\s*\(direction:\s*number\)\s*=>\s*\(\{[\s\S]*?x:\s*direction\s*\*\s*14[\s\S]*?custom=\{stageDirection\}/,
    'Authentication stage motion must use the transition direction',
  )
  assert.match(
    loginSource,
    /duration:\s*shouldReduceMotion\s*\?\s*0\s*:\s*0\.22/,
    'Authentication stage transitions must be direction-aware and 220ms',
  )
  assert.match(
    loginSource,
    /step\s*!==\s*['"]login['"][\s\S]*?aria-label=['"]注册进度['"]/,
    'Only registration stages may render the horizontal progress line',
  )
  assert.match(
    loginSource,
    /grid-cols-3[\s\S]*?h-(?:0\.5|1)\b/,
    'Registration progress must be a thin three-part horizontal line',
  )
})

test('publishing preserves AI fallback, controlled tags, and the publish boundary', () => {
  assert.match(
    publishSource,
    /const\s+\[useManualForm,\s*setUseManualForm\]\s*=\s*useState\(false\)/,
    'Publishing must retain the manual fallback state',
  )
  assert.match(
    publishSource,
    /const\s+activateManualForm\s*=\s*\(\)\s*=>\s*\{[\s\S]*?setUseManualForm\(true\)[\s\S]*?catch\s*\{[\s\S]*?activateManualForm\(\)/,
    'AI failure must continue to activate the manual fallback',
  )
  assert.match(
    publishSource,
    /const\s+\[fieldStates,\s*setFieldStates\][\s\S]*?field_states:\s*fieldStates/,
    'Publishing must retain structured field states across AI calls',
  )
  assert.match(
    publishSource,
    /candidateTags\s*\.filter\(\(tag\)\s*=>\s*selectedTagIds\.includes\(tag\.tag_id\)\)[\s\S]*?items\s*\.filter\(\(id\)\s*=>\s*id\s*!==\s*tag\.tag_id\)/,
    'Selected candidate tags must remain removable',
  )
  assert.match(
    publishSource,
    /candidateTags\.some\(\(tag\)\s*=>\s*!selectedTagIds\.includes\(tag\.tag_id\)\)[\s\S]*?setSelectedTagIds/,
    'Unselected candidate tags must remain selectable',
  )
  assert.match(
    publishSource,
    /const\s+handlePublish\s*=\s*async\s*\(\)\s*=>[\s\S]*?createPost\(/,
    'Publishing must retain handlePublish as the createPost boundary',
  )
  assert.match(
    publishSource,
    /<AnimatePresence\b|<Reveal\b/,
    'Publishing updates must use the shared Motion or Reveal language',
  )
})

test('publishing collapses the draft accessibly on mobile and keeps it visible on desktop', () => {
  assert.match(
    publishSource,
    /const\s+\[mobileDraftOpen,\s*setMobileDraftOpen\]\s*=\s*useState\(false\)/,
    'The mobile draft must start as an explicit collapsed disclosure',
  )
  assert.match(
    publishSource,
    /<button[\s\S]*?aria-expanded=\{mobileDraftOpen\}[\s\S]*?aria-controls=['"]mobile-publish-draft['"][\s\S]*?className=['"][^'"]*lg:hidden[^'"]*['"]/,
    'Mobile draft access must be an accessible disclosure button',
  )
  assert.match(
    publishSource,
    /id=['"]mobile-publish-draft['"][\s\S]*?mobileDraftOpen\s*\?\s*['"]block['"]\s*:\s*['"]hidden['"][\s\S]*?lg:block/,
    'The draft body must collapse below lg and remain visible on desktop',
  )
})

test('authentication clears purpose-specific OTP state when switching modes', () => {
  assert.match(
    loginSource,
    /const\s+switchingAuthPurpose\s*=\s*[\s\S]*?step\s*===\s*['"]login['"][\s\S]*?nextStep\s*===\s*['"]register['"][\s\S]*?step\s*===\s*['"]register['"][\s\S]*?nextStep\s*===\s*['"]login['"]/,
    'goToStep must detect login/register purpose changes in either direction',
  )
  assert.match(
    loginSource,
    /if\s*\(switchingAuthPurpose\)\s*\{[\s\S]*?setCode\(['"]['"]\)[\s\S]*?setCodeCooldown\(0\)[\s\S]*?\}/,
    'Purpose changes must clear the OTP value and resend cooldown together',
  )
})

test('manual draft edits synchronize confirmed field state for the next AI request', () => {
  assert.match(
    publishSource,
    /const\s+serializeFieldStateValue\s*=\s*\(value:[^)]*\)\s*=>[\s\S]*?Array\.isArray\(value\)[\s\S]*?value\.join\(['"]、['"]\)/,
    'Array draft fields must serialize to a readable field-state string',
  )
  assert.match(
    publishSource,
    /const\s+updateDraftField[\s\S]*?setDraft\([\s\S]*?setFieldStates\(\(current\)\s*=>\s*\(\{[\s\S]*?\[field\]:\s*\{[\s\S]*?value:\s*serializeFieldStateValue\(value\)[\s\S]*?status:\s*['"]confirmed['"]/,
    'Manual draft edits must update the corresponding field state as confirmed',
  )
})

test('primary auth code sends ignore stale completions after a purpose switch', () => {
  assert.match(
    loginSource,
    /const\s+primaryCodeRequestGeneration\s*=\s*useRef\(0\)/,
    'Primary auth code sends need a dedicated request generation ref',
  )
  assert.match(
    loginSource,
    /const\s+primaryAuthPurpose\s*=\s*useRef<['"]login['"]\s*\|\s*['"]register['"]>\(['"]login['"]\)/,
    'Primary auth code sends need the current auth purpose independent from stale closures',
  )
  assert.match(
    loginSource,
    /if\s*\(switchingAuthPurpose\)\s*\{[\s\S]*?primaryCodeRequestGeneration\.current\s*\+=\s*1[\s\S]*?setCode\(['"]['"]\)[\s\S]*?setCodeCooldown\(0\)[\s\S]*?setSendingCode\(false\)[\s\S]*?\}/,
    'A purpose switch must invalidate requests and clear all primary code-send UI state',
  )
  assert.match(
    loginSource,
    /const\s+requestPurpose\s*=\s*step\s*===\s*['"]login['"]\s*\?\s*['"]login['"]\s*:\s*['"]register['"][\s\S]*?const\s+requestGeneration\s*=\s*\+\+primaryCodeRequestGeneration\.current[\s\S]*?await\s+sendCode\(account,\s*requestPurpose\)/,
    'Each send must capture its purpose and generation before awaiting the API',
  )
  assert.match(
    loginSource,
    /const\s+requestIsCurrent\s*=\s*\(\)\s*=>[\s\S]*?primaryCodeRequestGeneration\.current\s*===\s*requestGeneration[\s\S]*?primaryAuthPurpose\.current\s*===\s*requestPurpose/,
    'Completion guards must check both generation and current auth purpose',
  )
  assert.equal(
    [...loginSource.matchAll(/if\s*\(!requestIsCurrent\(\)\)\s*return/g)].length,
    2,
    'Primary code success and error paths must both reject stale completion',
  )
  assert.match(
    loginSource,
    /finally\s*\{\s*if\s*\(requestIsCurrent\(\)\)\s*setSendingCode\(false\)\s*\}/,
    'A stale request must not finalize the current purpose sending state',
  )
  assert.match(
    loginSource,
    /sendCode\(verifyEmailAddr,\s*['"]campus_verify['"]\)/,
    'Campus verification code sending must remain on its independent flow',
  )
})
