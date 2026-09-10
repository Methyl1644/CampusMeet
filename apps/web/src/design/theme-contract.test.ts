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
