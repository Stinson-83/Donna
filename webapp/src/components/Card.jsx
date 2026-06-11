// DonnaCard renderer — the design-spec block vocabulary, rendered with the
// webapp's tokens. The backend emits a payload; this maps blocks -> components.
// A card's theme is intrinsic (dark = she needs you), independent of app
// morning/night, so dark/settled use explicit colors.

function themeColors(theme) {
  if (theme === 'dark')
    return { bg: '#241a12', fg: '#f3ebe1', sub: 'rgba(243,235,225,0.6)', line: 'rgba(243,235,225,0.14)', accent: '#c99a7e' }
  if (theme === 'settled')
    return { bg: 'rgba(120,110,100,0.07)', fg: 'rgb(var(--ink))', sub: 'rgb(var(--soft))', line: 'rgb(var(--line))', accent: 'rgb(var(--soft))' }
  return { bg: 'rgb(var(--surface))', fg: 'rgb(var(--ink))', sub: 'rgb(var(--soft))', line: 'rgb(var(--line))', accent: 'rgb(var(--rust))' }
}

// **bold** -> <strong>
function richText(text) {
  return String(text || '').split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i} style={{ fontWeight: 600 }}>{p.slice(2, -2)}</strong>
      : <span key={i}>{p}</span>,
  )
}

function Header({ b, c }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]" style={{ color: c.sub }}>{b.label}</span>
      {b.ref && <span className="text-[11px]" style={{ color: c.sub }}>{b.ref}</span>}
    </div>
  )
}

function Body({ b, c }) {
  return <p className="mt-2.5 text-[14.5px] leading-[1.5] lowercase" style={{ color: c.fg }}>{richText(b.text)}</p>
}

function Delta({ b, c }) {
  return (
    <div className="mt-3 flex items-end gap-3">
      {b.from && (
        <div>
          {b.from_caption && <div className="text-[10px] uppercase tracking-wide" style={{ color: c.sub }}>{b.from_caption}</div>}
          <div className="font-serif text-[22px] line-through" style={{ color: c.sub }}>{b.from}</div>
        </div>
      )}
      <div>
        {b.to_caption && <div className="text-[10px] uppercase tracking-wide" style={{ color: c.sub }}>{b.to_caption}</div>}
        <div className="font-serif text-[30px] leading-none" style={{ color: c.fg }}>{b.to}</div>
      </div>
    </div>
  )
}

function KeyValues({ b, c }) {
  return (
    <div className="mt-3 space-y-1.5">
      {(b.rows || []).map((r, i) => (
        <div key={i} className="flex items-baseline justify-between text-[13px]">
          <span style={{ color: c.sub }}>{r.k}</span>
          <span style={{ color: c.fg }}>{r.strike && <span className="mr-1.5 line-through" style={{ color: c.sub }}>{r.strike}</span>}{r.v}</span>
        </div>
      ))}
    </div>
  )
}

function Steps({ b, c }) {
  const dot = (st) => st === 'done' ? c.accent : st === 'now' ? c.accent : c.line
  return (
    <div className="mt-3 space-y-3 border-l pl-4" style={{ borderColor: c.line }}>
      {(b.steps || []).map((s, i) => (
        <div key={i} className="relative">
          <span className="absolute -left-[22px] top-1.5 h-1.5 w-1.5 rounded-full" style={{ background: dot(s.state), opacity: s.state === 'next' ? 0.5 : 1 }} />
          <div className="text-[14px]" style={{ color: s.state === 'next' ? c.sub : c.fg }}>{s.name}</div>
          {s.sub && <div className="text-[12px]" style={{ color: c.sub }}>{s.sub}</div>}
        </div>
      ))}
    </div>
  )
}

function Scopes({ b, c }) {
  return (
    <div className="mt-3">
      {b.account && <div className="text-[12px]" style={{ color: c.sub }}>{b.service} · {b.account}</div>}
      <ul className="mt-2 space-y-1.5">
        {(b.items || []).map((it, i) => (
          <li key={i} className="flex items-start gap-2 text-[13px]" style={{ color: c.fg }}>
            <span style={{ color: c.accent }}>·</span>{it}
          </li>
        ))}
      </ul>
      {b.note && <div className="mt-2 text-[11px]" style={{ color: c.sub }}>{b.note}</div>}
    </div>
  )
}

function FileRow({ b, c }) {
  return (
    <div className="mt-3 flex items-center justify-between rounded-xl px-3 py-2.5" style={{ border: `1px solid ${c.line}` }}>
      <div>
        <div className="text-[13px]" style={{ color: c.fg }}>{b.name}</div>
        {b.meta && <div className="text-[11px]" style={{ color: c.sub }}>{b.meta}</div>}
      </div>
      <span className="text-[10px] uppercase tracking-wide" style={{ color: c.sub }}>{b.kind}</span>
    </div>
  )
}

function Graph({ b, c }) {
  const pts = b.points || []
  if (pts.length < 2) return null
  const w = 260, h = 56
  const min = Math.min(...pts), max = Math.max(...pts), range = (max - min) || 1
  const x = (i) => (i / (pts.length - 1)) * w
  const y = (v) => h - ((v - min) / range) * h
  const d = pts.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const ty = b.target != null ? y(b.target) : null
  return (
    <div className="mt-3">
      {b.current_label && <div className="font-serif text-[28px] leading-none" style={{ color: c.fg }}>{b.current_label}</div>}
      <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 w-full" style={{ height: 50 }} preserveAspectRatio="none">
        {ty != null && <line x1="0" y1={ty} x2={w} y2={ty} stroke={c.accent} strokeDasharray="3 3" strokeWidth="1" opacity="0.55" />}
        <path d={d} fill="none" stroke={c.accent} strokeWidth="1.5" />
      </svg>
      {b.target_label && <div className="mt-1 text-[12px]" style={{ color: c.sub }}>{b.target_label}</div>}
    </div>
  )
}

function Actions({ b, c, onAct, acting }) {
  return (
    <div className="mt-4 flex gap-2.5">
      {(b.actions || []).map((a) => {
        const primary = a.style === 'primary'
        return (
          <button
            key={a.action_id}
            disabled={acting}
            onClick={() => onAct?.(a.action_id)}
            className="flex-1 rounded-[13px] px-3 py-2.5 text-[14px] font-semibold transition active:scale-[0.99] disabled:opacity-50"
            style={primary
              ? { background: c.accent, color: c.bg }
              : { background: 'transparent', color: c.sub, border: `1px solid ${c.line}` }}
          >
            {a.label}
          </button>
        )
      })}
    </div>
  )
}

function Footer({ b, c }) {
  return (
    <div className="mt-4 flex items-baseline justify-between text-[11px]" style={{ color: c.sub }}>
      <span>{b.text}</span>
      {b.right && <span>{b.right}</span>}
    </div>
  )
}

function Block({ b, c, onAct, acting }) {
  switch (b.type) {
    case 'header': return <Header b={b} c={c} />
    case 'body': return <Body b={b} c={c} />
    case 'delta': return <Delta b={b} c={c} />
    case 'key_values': return <KeyValues b={b} c={c} />
    case 'steps': return <Steps b={b} c={c} />
    case 'scopes': return <Scopes b={b} c={c} />
    case 'file': return <FileRow b={b} c={c} />
    case 'graph': return <Graph b={b} c={c} />
    case 'actions': return <Actions b={b} c={c} onAct={onAct} acting={acting} />
    case 'footer': return <Footer b={b} c={c} />
    default: return null
  }
}

export default function Card({ card, onAct, acting }) {
  if (!card || !Array.isArray(card.blocks)) return null
  const c = themeColors(card.theme)
  const grain = card.theme === 'dark'
  return (
    <div
      className="rounded-[20px] p-5"
      style={{ background: c.bg, color: c.fg, border: `1px solid ${c.line}`, boxShadow: grain ? '0 6px 24px rgba(20,12,6,0.18)' : 'none', transform: grain ? 'rotate(-0.3deg)' : 'none' }}
    >
      {card.blocks.map((b, i) => <Block key={i} b={b} c={c} onAct={onAct} acting={acting} />)}
    </div>
  )
}
