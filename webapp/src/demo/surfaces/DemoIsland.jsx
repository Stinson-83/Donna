// M5 — the Dynamic Island over Instagram. The one deliberately-faked surface:
// an Instagram-ish dark feed behind an iOS-style island that listens, recalls,
// then collapses to a booking. Three states, driven by the scene fixture.

function Feed() {
  const rows = Array.from({ length: 7 })
  return (
    <div className="absolute inset-0 bg-black pt-[120px]">
      {rows.map((_, i) => (
        <div key={i} className="mb-1 h-[128px]" style={{ background: i % 2 ? '#161616' : '#1c1c1c' }}>
          <div className="flex items-center gap-2 px-3 py-2">
            <span className="h-7 w-7 rounded-full" style={{ background: '#2a2a2a' }} />
            <span className="h-2 w-24 rounded" style={{ background: '#2a2a2a' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function Wave() {
  const bars = [7, 13, 9, 17, 8, 14, 7, 12, 9]
  return (
    <div className="flex h-5 items-center justify-center gap-[3px]">
      {bars.map((h, i) => (
        <span key={i} className="w-[3px] rounded" style={{ height: h, background: '#C99A7E' }} />
      ))}
    </div>
  )
}

export default function DemoIsland({ state = 'listening', query, title, body, text }) {
  const wide = state !== 'listening'
  return (
    <div className="relative h-full w-full overflow-hidden">
      <Feed />
      <div
        className="absolute left-1/2 top-3.5 -translate-x-1/2 rounded-[26px] bg-black text-white shadow-[0_12px_34px_rgba(0,0,0,0.55)]"
        style={{ width: wide ? '90%' : 188, padding: wide ? '15px 18px' : '13px 18px', transition: 'all .35s cubic-bezier(.22,1,.36,1)' }}
      >
        {state === 'listening' && <Wave />}

        {state === 'recall' && (
          <>
            {query && <div className="mb-2.5 text-center text-[12.5px] leading-snug text-white/80">{query}</div>}
            <div className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: '#C99A7E' }}>{title}</div>
            <div className="mt-1.5 text-[13.5px] leading-[1.5] text-white/90">{body}</div>
          </>
        )}

        {state === 'booked' && (
          <div className="flex items-center justify-center gap-2 py-0.5 text-[13.5px] font-semibold" style={{ color: '#9fd9a8' }}>
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 6" /></svg>
            {text}
          </div>
        )}
      </div>
    </div>
  )
}
