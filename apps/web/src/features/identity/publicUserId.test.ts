import { describe, expect, it } from 'vitest'
import { parsePublicUserId, publicUserId } from './publicUserId'

describe('public user id', () => {
  it('formats and parses the short public form', () => {
    expect(publicUserId('104')).toBe('CM-104')
    expect(parsePublicUserId('cm-104')).toBe(104)
    expect(parsePublicUserId('104')).toBe(104)
    expect(parsePublicUserId('student')).toBeNull()
  })
})
