// @vitest-environment jsdom

import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { ONBOARDING_INTERESTS } from '@shared/constants'
import ChoiceChips from './ChoiceChips'

const thirtyOneInterests = ONBOARDING_INTERESTS.slice(0, 31)

function SelectionHarness({ maxSelected }: { maxSelected?: number }) {
  const [selected, setSelected] = useState<string[]>([])

  return (
    <>
      <ChoiceChips
        label="兴趣方向"
        options={thirtyOneInterests}
        selected={selected}
        onChange={setSelected}
        maxSelected={maxSelected}
      />
      <div data-testid="interest-payload">
        {JSON.stringify({ interests: selected })}
      </div>
    </>
  )
}

function payloadInterests() {
  return JSON.parse(screen.getByTestId('interest-payload').textContent ?? '{}').interests as string[]
}

afterEach(cleanup)

describe('ChoiceChips selection limit', () => {
  it('does not put a thirty-first standard interest into the save payload', () => {
    render(<SelectionHarness maxSelected={30} />)

    thirtyOneInterests.forEach((interest) => {
      fireEvent.click(screen.getByRole('button', { name: interest }))
    })

    expect(payloadInterests()).toHaveLength(30)
    expect(payloadInterests()).not.toContain(thirtyOneInterests[30])
  })

  it('announces the limit, blocks new choices, and leaves selected choices removable', () => {
    render(<SelectionHarness maxSelected={30} />)

    thirtyOneInterests.slice(0, 30).forEach((interest) => {
      fireEvent.click(screen.getByRole('button', { name: interest }))
    })

    expect(screen.getByRole('status').textContent).toContain('最多选择 30 项')
    expect((screen.getByRole('button', { name: thirtyOneInterests[30] }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: thirtyOneInterests[0] }) as HTMLButtonElement).disabled).toBe(false)

    fireEvent.click(screen.getByRole('button', { name: thirtyOneInterests[0] }))

    expect(payloadInterests()).toHaveLength(29)
    expect((screen.getByRole('button', { name: thirtyOneInterests[30] }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('does not impose an interest limit when maxSelected is omitted', () => {
    render(<SelectionHarness />)

    thirtyOneInterests.forEach((interest) => {
      fireEvent.click(screen.getByRole('button', { name: interest }))
    })

    expect(payloadInterests()).toHaveLength(31)
    expect(screen.queryByRole('status')).toBeNull()
  })
})
