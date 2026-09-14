export function publicUserId(id: string | number): string {
  const value = String(id).trim()
  return /^\d+$/.test(value) ? `CM-${value}` : value
}

export function parsePublicUserId(value: string): number | null {
  const normalized = value.trim().toUpperCase().replace(/^CM[-\s]?/, '')
  if (!/^\d+$/.test(normalized)) return null
  const id = Number(normalized)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}
