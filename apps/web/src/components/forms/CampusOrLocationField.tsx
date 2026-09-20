import { useEffect, useState } from 'react'
import { isNjuCampus, NJU_CAMPUSES } from '@/features/location/campuses'

export default function CampusOrLocationField({
  id,
  label,
  value,
  onChange,
  required = false,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
}) {
  const [mode, setMode] = useState<'campus' | 'location'>(() => (!value || isNjuCampus(value) ? 'campus' : 'location'))

  useEffect(() => {
    if (value) setMode(isNjuCampus(value) ? 'campus' : 'location')
  }, [value])

  const chooseMode = (nextMode: 'campus' | 'location') => {
    setMode(nextMode)
    if (nextMode === 'campus' && !isNjuCampus(value)) onChange(NJU_CAMPUSES[0])
    if (nextMode === 'location' && isNjuCampus(value)) onChange('')
  }

  return (
    <div>
      <span className="publish-field-label">{label}{required && <span aria-hidden="true" className="text-rose-600"> *</span>}</span>
      <div className="mt-2 flex gap-2" role="group" aria-label={`${label}类型`}>
        <button type="button" className={mode === 'campus' ? 'btn-primary min-h-9' : 'btn-secondary min-h-9'} aria-pressed={mode === 'campus'} onClick={() => chooseMode('campus')}>校区</button>
        <button type="button" className={mode === 'location' ? 'btn-primary min-h-9' : 'btn-secondary min-h-9'} aria-pressed={mode === 'location'} onClick={() => chooseMode('location')}>地点</button>
      </div>
      {mode === 'campus' ? (
        <select id={id} aria-label="选择校区" required={required} className="input-base mt-2" value={isNjuCampus(value) ? value : NJU_CAMPUSES[0]} onChange={(event) => onChange(event.target.value)}>
          {NJU_CAMPUSES.map((campus) => <option key={campus} value={campus}>{campus}</option>)}
        </select>
      ) : (
        <input id={id} aria-label="填写具体地点" required={required} maxLength={80} className="input-base mt-2" value={value} onChange={(event) => onChange(event.target.value)} placeholder="填写拆分出的具体地点" />
      )}
    </div>
  )
}
