import { useState } from 'react'

// Not a "+ create" button. A quiet invitation to leave a thought with Donna.
const ACTIONS = [
  { key: 'chat', label: 'a thought' },
  { key: 'voice', label: 'a voice note' },
  { key: 'capture', label: 'something quick' },
  { key: 'journal', label: 'a journal entry' },
]

export default function Fab({ onAction }) {
  const [open, setOpen] = useState(false)

  function handle(key) {
    setOpen(false)
    onAction?.(key)
  }

  return (
    <div className="pointer-events-none absolute bottom-4 right-5 z-30 flex flex-col items-end gap-2">
      {open &&
        ACTIONS.map((a, i) => (
          <button
            key={a.key}
            onClick={() => handle(a.key)}
            className="reveal pointer-events-auto rounded-full border border-line bg-surface/90 px-4 py-2 text-[13px] lowercase text-ink backdrop-blur"
            style={{ animationDelay: `${i * 45}ms` }}
          >
            {a.label}
          </button>
        ))}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="tell donna"
        className="pointer-events-auto flex items-center gap-2 rounded-full border bg-surface/80 px-4 py-2.5 backdrop-blur transition"
        style={{ borderColor: 'rgb(var(--rust) / 0.5)' }}
      >
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: 'rgb(var(--rust))' }} />
        <span className="text-[13px] lowercase tracking-wide text-ink">tell donna</span>
      </button>
    </div>
  )
}
