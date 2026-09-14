// @vitest-environment jsdom

import { cleanup, render, screen } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import CampusMark from './CampusMark'

afterEach(cleanup)

describe('CampusMeet brand mark', () => {
  it('uses the shared mark and brand color in browser metadata', () => {
    const indexHtml = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')

    expect(indexHtml).toContain('href="/campusmeet-mark.svg"')
    expect(indexHtml).toContain('name="theme-color" content="#346f5d"')
  })

  it('renders the Wutongyu name and the shared three-whale leaf mark', () => {
    render(<CampusMark />)

    expect(screen.getByText('梧桐遇')).not.toBeNull()
    expect(screen.getByText('CampusMeet')).not.toBeNull()
    expect(screen.getByRole('img', { name: '梧桐遇三鲸鱼梧桐叶标志' })).not.toBeNull()
  })

  it('keeps the compact mark accessible without rendering the wordmark', () => {
    render(<CampusMark compact />)

    expect(screen.getByRole('img', { name: '梧桐遇三鲸鱼梧桐叶标志' })).not.toBeNull()
    expect(screen.queryByText('CampusMeet')).toBeNull()
  })
})
