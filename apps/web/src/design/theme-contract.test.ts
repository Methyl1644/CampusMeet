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
const apiClientSource = readFileSync(
  new URL('../api/client.ts', import.meta.url),
  'utf8',
)
const postDetailSource = readFileSync(
  new URL('../pages/PostDetail.tsx', import.meta.url),
  'utf8',
)
const applicationModalSource = readFileSync(
  new URL('../components/ApplicationModal.tsx', import.meta.url),
  'utf8',
)
const messagesSource = readFileSync(
  new URL('../pages/Messages.tsx', import.meta.url),
  'utf8',
)
const teamDetailSource = readFileSync(
  new URL('../pages/TeamDetail.tsx', import.meta.url),
  'utf8',
)
const profileSource = readFileSync(
  new URL('../pages/Profile.tsx', import.meta.url),
  'utf8',
)
const homeSource = readFileSync(new URL('../pages/Home.tsx', import.meta.url), 'utf8')
const discoverSource = readFileSync(new URL('../pages/Discover.tsx', import.meta.url), 'utf8')
const routerSource = readFileSync(new URL('../router/index.tsx', import.meta.url), 'utf8')
const clientSource = readFileSync(new URL('../api/client.ts', import.meta.url), 'utf8')
const tutorialUrl = new URL('../pages/Tutorial.tsx', import.meta.url)
const tutorialSource = existsSync(tutorialUrl) ? readFileSync(tutorialUrl, 'utf8') : ''
const topicDetailSource = readFileSync(new URL('../pages/TopicDetail.tsx', import.meta.url), 'utf8')

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
  assert.match(
    indexCss,
    /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*?\.group:hover[\s\S]*?transform:\s*none\s*!important/,
    'Reduced-motion mode must disable card hover transforms',
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

test('tutorial is available on desktop without changing the mobile five-item navigation', () => {
  assert.ok(existsSync(tutorialUrl), 'Tutorial.tsx must exist')
  assert.match(navbarSource, /BookOpen/)
  assert.match(
    navbarSource,
    /to:\s*['"]\/tutorial['"][\s\S]*?label:\s*['"]教程['"][\s\S]*?desktopOnly:\s*true/,
  )
  assert.match(navbarSource, /navItems\.filter\(\(item\)\s*=>\s*!item\.desktopOnly\)/)
  assert.match(navbarSource, /grid-cols-5/)
  assert.match(routerSource, /import\s+Tutorial\s+from\s+['"]@\/pages\/Tutorial['"]/)
  assert.match(routerSource, /path:\s*['"]tutorial['"][\s\S]*?element:\s*<Tutorial\s*\/>/)

  for (const heading of [
    '注册与校园认证',
    '查找话题与活动',
    '标准标签与搜索',
    'AI 辅助发布组队帖',
    '申请、消息与确认组队',
    '联系方式与安全',
  ]) {
    assert.match(tutorialSource, new RegExp(heading))
  }
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

test('business pages move explanatory copy into the tutorial module', () => {
  assert.doesNotMatch(discoveryHubSource, /正式赛事先查看话题资料/)
  assert.doesNotMatch(discoveryHubSource, /调整关键词|试试活动简称/)
  assert.doesNotMatch(loginSource, /在校园里，找到一起把事情做成的人/)
  assert.doesNotMatch(loginSource, /仅用于本地界面预览|验证码登录可留空|首期限南京大学校内使用/)
  assert.doesNotMatch(publishSource, /例如：|例如：「|AI 只整理发帖草稿|开始对话后/)
  assert.doesNotMatch(messagesSource, /请勿在聊天中交换联系方式/)
  assert.doesNotMatch(teamDetailSource, /双方确认组队后将解锁联系方式/)
  assert.doesNotMatch(topicDetailSource, /先了解活动，再选择合适的队伍|成为第一个发起招募的人/)
  assert.doesNotMatch(postDetailSource, /该活动被标记为高风险|该活动涉及线下\/夜间/)

  for (const concept of ['校园认证', '话题直达', '标准标签', 'AI 辅助', '确认组队', '联系方式只在双方确认组队后解锁']) {
    assert.match(tutorialSource, new RegExp(concept))
  }
})

test('topic cards exist and link to topic detail routes', () => {
  assert.ok(existsSync(topicCardUrl), 'TopicCard.tsx must exist')
  assert.match(
    topicCardSource,
    /to=\{`\/topics\/\$\{topic\.id\}`\}/,
    'TopicCard must link to /topics/:id',
  )
})

test('discovery and topic detail are connected to application routes', () => {
  assert.match(homeSource, /import\s+DiscoveryHub\s+from\s+['"]@\/components\/DiscoveryHub['"]/)
  assert.match(homeSource, /return\s+<DiscoveryHub\s*\/>/)
  assert.match(discoverSource, /import\s+DiscoveryHub\s+from\s+['"]@\/components\/DiscoveryHub['"]/)
  assert.match(discoverSource, /return\s+<DiscoveryHub\s*\/>/)
  assert.match(routerSource, /import\s+TopicDetail\s+from\s+['"]@\/pages\/TopicDetail['"]/)
  assert.match(routerSource, /path:\s*['"]topics\/:id['"][\s\S]*?element:\s*<TopicDetail\s*\/>/)
})

test('development preview stays in the frontend when protected APIs return 401', () => {
  assert.match(clientSource, /import\.meta\.env\.DEV/)
  assert.match(clientSource, /token\s*===\s*['"]local-demo-token['"]/)
  assert.match(
    clientSource,
    /status\s*===\s*401[\s\S]*?!isLocalDemo[\s\S]*?logout\(\)/,
    'A preview-only token must not trigger the real-account logout redirect',
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
    /type\s+Step\s*=\s*['"]login['"]\s*\|\s*['"]register['"]\s*\|\s*['"]profile['"]/,
    'Login must keep the campus account and profile registration stages',
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
    /grid-cols-2[\s\S]*?h-(?:0\.5|1)\b/,
    'Registration progress must be a thin two-part horizontal line',
  )
  assert.match(
    loginSource,
    /const\s+isNjuCampusEmail[\s\S]*?smail[\s\S]*?nju[\s\S]*?edu[\s\S]*?cn/,
    'Authentication must validate the two approved NJU mail domains',
  )
  assert.doesNotMatch(loginSource, /\bPhone\b|campus_verify|verifyEmailAddr/)
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
  assert.doesNotMatch(
    publishSource,
    /editingDraft|setEditingDraft/,
    'Structured draft fields must remain directly editable without a hidden edit mode',
  )
  assert.match(
    publishSource,
    /draft\.target_members\s*>\s*0\s*\?\s*String\(draft\.target_members\)\s*:\s*''/,
    'An unknown target size must render as an empty editable value instead of a fake person count',
  )
  assert.match(
    apiClientSource,
    /timeout:\s*65000/,
    'The browser timeout must leave enough room for Coze timeout and local fallback handling',
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

test('manual draft edits synchronize meaningful field state for the next AI request', () => {
  assert.match(
    publishSource,
    /const\s+serializeFieldStateValue\s*=\s*\(value:[^)]*\)\s*=>[\s\S]*?Array\.isArray\(value\)[\s\S]*?value\.join\(['"]、['"]\)/,
    'Array draft fields must serialize to a readable field-state string',
  )
  assert.match(
    publishSource,
    /const\s+updateDraftField[\s\S]*?const\s+isEmpty[\s\S]*?setDraft\([\s\S]*?setFieldStates\(\(current\)[\s\S]*?value:\s*isEmpty\s*\?\s*null\s*:\s*serializeFieldStateValue\(value\)[\s\S]*?status:\s*emptyIsTerminal\s*\?\s*['"]none['"]\s*:\s*isEmpty\s*\?\s*['"]pending['"]\s*:\s*['"]confirmed['"]/,
    'Manual draft edits must confirm entered values and distinguish optional empty values from missing required values',
  )
  assert.match(
    publishSource,
    /const\s+fieldStatesComplete[\s\S]*?requiredDraftFields\.every[\s\S]*?status\s*!==\s*['"]pending['"][\s\S]*?const\s+canPublish\s*=\s*draftIsValid\s*&&\s*\(useManualForm\s*\|\|\s*fieldStatesComplete\)/,
    'Direct edits must immediately recalculate whether the structured draft can be published',
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
})

test('remaining workflow surfaces use the shared campus visual and motion language', () => {
  for (const [name, source] of [
    ['PostDetail', postDetailSource],
    ['ApplicationModal', applicationModalSource],
    ['Messages', messagesSource],
    ['TeamDetail', teamDetailSource],
    ['Profile', profileSource],
  ]) {
    assert.match(
      source,
      /(?:<Reveal\b|<motion\.|text-ink|border-stone|bg-paper)/,
      `${name} must use shared campus styling or motion`,
    )
    assert.doesNotMatch(source, /[\u2013\u2014]/, `${name} must not render dash fallbacks`)
  }
})

test('post detail reads as a recruitment brief while preserving apply permissions and status', () => {
  assert.match(
    postDetailSource,
    /import\s+\{\s*Reveal\s*\}\s+from\s+['"]@\/components\/motion\/Reveal['"]/,
    'PostDetail must use the shared page reveal',
  )
  for (const label of ['招募条件', '所需角色', 'AI 匹配说明', '发起人']) {
    assert.match(postDetailSource, new RegExp(label), `PostDetail must include ${label}`)
  }
  assert.match(
    postDetailSource,
    /const\s+isAuthor\s*=\s*user\?\.id\s*===\s*post\.author\.id[\s\S]*?const\s+canApply\s*=\s*!isAuthor\s*&&\s*post\.status\s*===\s*['"]recruiting['"]\s*&&\s*!applied/,
    'Author, recruiting status, and prior application must continue to gate applying',
  )
  assert.match(
    postDetailSource,
    /if\s*\(isUnverified\)[\s\S]*?showToast\(['"]请先完成校园邮箱认证['"],\s*['"]error['"]\)[\s\S]*?setShowApplyModal\(true\)/,
    'Campus verification must continue to gate the application modal',
  )
  assert.match(
    postDetailSource,
    /isAuthor\s*\?[\s\S]*?applied\s*\?[\s\S]*?canApply\s*\?[\s\S]*?post\.status\s*===\s*['"]full['"][\s\S]*?post\.status\s*===\s*['"]expired['"]/,
    'The stable apply action must preserve every status branch',
  )
})

test('application modal protects focus and preserves required application submission fields', () => {
  assert.match(
    applicationModalSource,
    /role=['"]dialog['"][\s\S]*?aria-modal=['"]true['"][\s\S]*?aria-labelledby=['"]application-modal-title['"]/,
    'ApplicationModal must expose modal dialog semantics',
  )
  assert.match(
    applicationModalSource,
    /previouslyFocusedElement[\s\S]*?event\.key\s*===\s*['"]Escape['"][\s\S]*?event\.key\s*!==\s*['"]Tab['"][\s\S]*?previouslyFocusedElement\.focus\(\)/,
    'ApplicationModal must close on Escape, contain Tab focus, and restore focus',
  )
  for (const fieldId of ['application-role', 'application-experience', 'application-time', 'application-reason', 'application-questions']) {
    assert.match(
      applicationModalSource,
      new RegExp(`(?:htmlFor|id)=['"]${fieldId}['"]`),
      `ApplicationModal must explicitly label ${fieldId}`,
    )
  }
  assert.match(
    applicationModalSource,
    /!roleWanted[\s\S]*?!experience\.trim\(\)[\s\S]*?!reason\.trim\(\)[\s\S]*?createApplication\(\{[\s\S]*?post_id:\s*post\.id[\s\S]*?role_wanted:\s*roleWanted[\s\S]*?experience:\s*experience\.trim\(\)[\s\S]*?available_time:\s*availableTime\.trim\(\)[\s\S]*?reason:\s*reason\.trim\(\)[\s\S]*?questions:/,
    'Required checks and the createApplication payload must remain intact',
  )
  assert.match(
    applicationModalSource,
    /max-h-\[calc\(100dvh-[^\]]+\)\][\s\S]*?overflow-y-auto/,
    'The modal body must remain scrollable within the mobile viewport',
  )
})

test('messages keeps safe bilateral confirmation in a responsive two-pane workspace', () => {
  assert.match(messagesSource, /100dvh/, 'Messages must use dynamic viewport height')
  assert.match(
    messagesSource,
    /md:grid-cols-\[[^\]]+\]/,
    'Messages must expose stable desktop conversation and chat columns',
  )
  assert.match(
    messagesSource,
    /aria-current=\{activeConv\?\.id\s*===\s*conv\.id\s*\?\s*['"]true['"]\s*:\s*undefined\}/,
    'The active conversation row must be announced',
  )
  assert.match(
    messagesSource,
    /sendMessage\(activeConv\.id,\s*content\)[\s\S]*?confirmTeam\(activeConv\.id\)[\s\S]*?closeConversation\(activeConv\.id\)/,
    'Message send, bilateral confirmation, and close API boundaries must remain',
  )
  assert.match(
    messagesSource,
    /activeConv\.status\s*===\s*['"]active['"][\s\S]*?activeConv\.status\s*===\s*['"]closed['"][\s\S]*?activeConv\.status\s*===\s*['"]team_confirmed['"]/,
    'Conversation controls must preserve active, closed, and confirmation states',
  )
})

test('team detail keeps planning controls and locked contact disclosure stable', () => {
  assert.match(
    teamDetailSource,
    /import\s+\{\s*Reveal\s*\}\s+from\s+['"]@\/components\/motion\/Reveal['"]/,
    'TeamDetail must use shared record reveals',
  )
  for (const label of ['成员与角色', '分工建议', '首次会议议程', '任务清单', '风险提醒', '联系方式']) {
    assert.match(teamDetailSource, new RegExp(label), `TeamDetail must include ${label}`)
  }
  assert.match(
    teamDetailSource,
    new RegExp(
      String.raw`handleToggleAgenda\(item\.id\)[\s\S]*?min-h-` +
        String.raw`[\w\[\]-]+[\s\S]*?handleToggleTask\(task\.id,\s*task\.done\)[\s\S]*?min-h-` +
        String.raw`[\w\[\]-]+`,
    ),
    'Agenda and task controls need stable checked and unchecked row heights',
  )
  assert.match(
    teamDetailSource,
    /updateTask\(team\.id,\s*taskId,\s*!currentDone\)[\s\S]*?showToast\(['"]更新失败['"],\s*['"]error['"]\)/,
    'Task updates must keep their API and rollback error boundary',
  )
  assert.match(teamDetailSource, /team\.contact_info\.length\s*>\s*0/)
})

test('team detail exposes the deployed AI team-plan workflow with resilient feedback', () => {
  assert.match(
    teamDetailSource,
    /import\s+\{\s*generateTeamPlan\s*\}\s+from\s+['"]@\/api\/agent['"]/,
    'TeamDetail must use the shared team-plan API client',
  )
  assert.match(
    teamDetailSource,
    /const\s+handleGeneratePlan\s*=\s*async[\s\S]*?await\s+generateTeamPlan\(team\.id\)/,
    'TeamDetail must call the deployed team-plan endpoint for the current team',
  )
  assert.match(
    teamDetailSource,
    /setTeam\(\(current\)[\s\S]*?division_of_labor:\s*plan\.division_of_labor[\s\S]*?meeting_agenda:\s*plan\.meeting_agenda[\s\S]*?task_list:\s*plan\.task_list[\s\S]*?risk_reminders:\s*plan\.risk_reminders/,
    'A generated plan must refresh every planning section together',
  )
  assert.match(teamDetailSource, /生成团队规划/)
  assert.match(teamDetailSource, /重新生成规划/)
  assert.match(teamDetailSource, /disabled=\{generatingPlan\}/, 'Duplicate requests must be disabled')
  assert.match(teamDetailSource, /规划生成失败/, 'The workflow call needs an error boundary')
  assert.match(
    teamDetailSource,
    /task\.due_at\s*\|\|\s*task\.deadline/,
    'Generated due_at values must remain visible alongside legacy deadline values',
  )
})

test('profile preserves editing, underline tabs, records, stats, and logout', () => {
  assert.match(
    profileSource,
    /import\s+\{\s*Reveal\s*\}\s+from\s+['"]@\/components\/motion\/Reveal['"]/,
    'Profile must use shared page and record reveals',
  )
  assert.match(profileSource, /role=['"]tablist['"]/, 'Profile tabs need tablist semantics')
  assert.match(
    profileSource,
    /role=['"]tab['"][\s\S]*?aria-selected=\{active\}[\s\S]*?border-b-2/,
    'Profile must keep underline tabs with selected-state semantics',
  )
  assert.match(
    profileSource,
    /updateProfile\(\{[\s\S]*?nickname:\s*editNickname[\s\S]*?major:\s*editMajor[\s\S]*?grade:\s*editGrade[\s\S]*?skills:\s*editSkills/,
    'Profile editing must preserve its existing payload',
  )
  for (const label of ['我的帖子', '我的申请', '我的团队']) {
    assert.match(profileSource, new RegExp(label), `Profile must preserve ${label}`)
  }
  assert.match(
    profileSource,
    /const\s+handleLogout[\s\S]*?logout\(\)[\s\S]*?navigate\(['"]\/login['"]\)/,
    'Profile logout must continue to clear auth and route to login',
  )
})
