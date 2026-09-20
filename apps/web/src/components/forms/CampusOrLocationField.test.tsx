// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CampusOrLocationField from './CampusOrLocationField'

describe('CampusOrLocationField', () => {
  it('limits campus choices to the four Nanjing University campuses and allows a concrete location', () => {
    const onChange = vi.fn()
    const { rerender } = render(<CampusOrLocationField id="scope" label="校区或地点" value="" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: '校区' }))
    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual(['鼓楼校区', '仙林校区', '苏州校区', '浦口校区'])
    fireEvent.change(screen.getByLabelText('选择校区'), { target: { value: '苏州校区' } })
    expect(onChange).toHaveBeenCalledWith('苏州校区')

    rerender(<CampusOrLocationField id="scope" label="校区或地点" value="玄武湖" onChange={onChange} />)
    expect((screen.getByLabelText('填写具体地点') as HTMLInputElement).value).toBe('玄武湖')
  })
})
