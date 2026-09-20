export const NJU_CAMPUSES = ['鼓楼校区', '仙林校区', '苏州校区', '浦口校区'] as const

export function isNjuCampus(value: string): value is (typeof NJU_CAMPUSES)[number] {
  return NJU_CAMPUSES.includes(value as (typeof NJU_CAMPUSES)[number])
}
