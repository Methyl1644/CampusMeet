import { useEffect, useState } from 'react'
import './publish.css'

export function Whale({ animated = false }: { animated?: boolean }) {
  return <svg viewBox="0 0 180 152" className={animated ? 'whale whale-animated' : 'whale'} aria-hidden="true">
    <g className="whale-body">
      <path d="M142 83Q156 86 159 72Q167 78 173 67Q180 88 160 97Q155 125 112 135Q43 149 22 110Q7 78 36 61Q66 39 103 57Q131 66 142 83Z" fill="#72b7ed" stroke="#4e97cf" strokeWidth="2" />
      <path d="M29 111Q65 101 82 120Q101 137 125 130Q63 152 29 111" fill="#f4fafc" />
      <path d="M39 109Q24 122 22 112" fill="#4e97cf" /><path d="M113 113Q127 131 133 113" fill="#589fda" />
      <ellipse cx="53" cy="87" rx="3.5" ry="5" fill="#263c4f"/><ellipse cx="91" cy="87" rx="3.5" ry="5" fill="#263c4f"/>
      <path d="M66 97Q72 105 79 97" fill="none" stroke="#263c4f" strokeWidth="2.5" strokeLinecap="round" />
    </g>
    <g fill="#78d2ed" className="whale-spout"><path d="M73 52Q43 39 52 25Q66 16 73 52ZM76 47Q72 10 85 11Q102 19 76 47Z" /><circle className="whale-drop" cx="104" cy="33" r="4"/><circle className="whale-drop" cx="42" cy="13" r="3" /></g>
  </svg>
}

export default function WhaleWaiting() {
  const [visible, setVisible] = useState(false)
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const show = setTimeout(() => setVisible(true), 250)
    const late = setTimeout(() => setSlow(true), 12000)
    return () => { clearTimeout(show); clearTimeout(late) }
  }, [])
  return <div className={`whale-overlay ${visible ? 'is-visible' : ''}`} role="status" aria-live="polite">
    <div className="w-32"><Whale animated /></div>
    <p className="font-medium text-ink">{slow ? '这次整理稍久，你的内容已保留' : '正在整理你的想法…'}</p>
  </div>
}
