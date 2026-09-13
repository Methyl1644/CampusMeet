// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { ToastProvider, useToast } from './Toast'

function DuplicateErrorTrigger() {
  const { showToast } = useToast()
  return (
    <button
      type="button"
      onClick={() => {
        showToast('提交失败', 'error')
        showToast('提交失败', 'error')
      }}
    >
      触发错误
    </button>
  )
}

afterEach(() => cleanup())

it('keeps only one identical error toast visible', () => {
  render(
    <ToastProvider>
      <DuplicateErrorTrigger />
    </ToastProvider>,
  )

  fireEvent.click(screen.getByRole('button', { name: '触发错误' }))

  expect(screen.getAllByRole('alert')).toHaveLength(1)
})
