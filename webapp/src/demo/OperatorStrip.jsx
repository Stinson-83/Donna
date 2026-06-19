import { useEffect, useState } from 'react'
import { SCENES } from './scenes.js'
import { goScene } from './store.js'

// Operator control bar — pinned to the very top of the WINDOW, OUTSIDE the phone
// frame, so OBS (cropped to the phone) never sees it. Press `h` to hide entirely.
// `[` / `]` step scenes; the dropdown jumps anywhere.
export default function OperatorStrip({ current }) {
  const [hidden, setHidden] = useState(false)
  const idx = SCENES.findIndex((s) => s.id === current?.id)

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'h') setHidden((v) => !v)
      else if (e.key === ']' && idx < SCENES.length - 1) goScene(SCENES[idx + 1].id)
      else if (e.key === '[' && idx > 0) goScene(SCENES[idx - 1].id)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [idx])

  if (hidden) return null
  return (
    <div
      className="fixed inset-x-0 top-0 z-[999] flex items-center gap-2 px-3 py-1.5 font-mono text-[12px] text-white"
      style={{ background: 'rgba(20,16,11,0.92)' }}
    >
      <button onClick={() => idx > 0 && goScene(SCENES[idx - 1].id)} className="rounded px-2 py-0.5 hover:bg-white/15" disabled={idx <= 0}>◀</button>
      <button onClick={() => idx < SCENES.length - 1 && goScene(SCENES[idx + 1].id)} className="rounded px-2 py-0.5 hover:bg-white/15" disabled={idx >= SCENES.length - 1}>▶</button>
      <select
        value={current?.id || ''}
        onChange={(e) => goScene(e.target.value)}
        className="rounded bg-black/40 px-1.5 py-0.5 text-white outline-none"
      >
        {SCENES.map((s) => <option key={s.id} value={s.id}>{s.n}. {s.at ? `${s.at} · ` : ''}{s.beat}  ·  {s.id}</option>)}
      </select>
      <span className="ml-auto text-white/55">{idx + 1}/{SCENES.length} · [ ] step · h hide</span>
    </div>
  )
}
