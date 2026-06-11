// DonnaCard renderer — the design-spec block vocabulary + the design-spec card
// styling (donna-design-spec/tokens + reference HTML). A card's theme is
// intrinsic: dark = espresso "she needs you", light = informational, settled =
// resolved/sunk. Numerals use EB Garamond; everything else Red Hat Text.

const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")"

function theme(t) {
  if (t === 'dark')
    return {
      bg: 'radial-gradient(140% 90% at 20% 0%, #3A2C20 0%, #251D16 52%, #1B140E 100%)',
      fg: '#F3EBE1', sub: 'rgba(243,235,225,0.62)', line: 'rgba(243,235,225,0.14)', accent: '#C99A7E',
      shadow: '0 2px 4px rgba(32,22,14,0.18), 0 10px 24px rgba(32,22,14,0.22), 0 30px 60px rgba(32,22,14,0.25), inset 0 1px 0 rgba(255,255,255,0.09)',
      tilt: '-0.4deg', grain: true,
      primary: { background: 'linear-gradient(180deg,#FBF6EE 0%,#F3EBE1 100%)', color: '#251D16', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.5)' },
      secondary: { background: 'transparent', color: 'rgba(243,235,225,0.62)', border: '1px solid rgba(243,235,225,0.16)' },
    }
  if (t === 'settled')
    return {
      bg: 'rgba(255,255,255,0.5)', fg: '#201A14', sub: '#6F665C', line: 'rgba(63,46,35,0.08)', accent: '#6F665C',
      shadow: 'inset 0 1.5px 3px rgba(63,42,30,0.05)', tilt: '0.3deg', grain: false,
      primary: { background: 'transparent', color: '#6F665C', border: '1px solid rgba(63,46,35,0.08)' },
      secondary: { background: 'transparent', color: '#6F665C', border: '1px solid rgba(63,46,35,0.08)' },
    }
  return {
    bg: 'linear-gradient(180deg,#FFFFFF 0%,#FDF9F5 100%)', fg: '#201A14', sub: '#6F665C', line: 'rgba(63,46,35,0.08)', accent: '#7B5544',
    shadow: '0 1px 1px rgba(63,42,30,0.05), 0 3px 6px rgba(63,42,30,0.05), 0 10px 20px rgba(63,42,30,0.06), inset 0 1.5px 0 #FFF',
    tilt: '0deg', grain: false,
    primary: { background: 'linear-gradient(180deg,#88604E 0%,#7B5544 65%,#6C4A3A 100%)', color: '#F3EBE1', boxShadow: '0 2px 5px rgba(101,68,53,0.35), inset 0 1px 0 rgba(255,255,255,0.25)' },
    secondary: { background: 'transparent', color: '#6F665C', border: '1px solid rgba(63,46,35,0.08)' },
  }
}

// body supports **bold** only (design-spec richText law)
function richText(text) {
  return String(text || '').split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i} style={{ fontWeight: 600 }}>{p.slice(2, -2)}</strong>
      : <span key={i}>{p}</span>,
  )
}

const serif = { fontFamily: "'EB Garamond', Georgia, serif", fontWeight: 600 }

function Header({ b, c }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="text-[10.5px] font-bold uppercase tracking-[0.08em]" style={{ color: c.sub }}>{b.label}</span>
      {b.ref && <span className="text-[11px] font-semibold" style={{ color: c.sub }}>{b.ref}</span>}
    </div>
  )
}
function Body({ b, c }) {
  return <p className="mt-2.5 text-[14.5px] leading-[1.5]" style={{ color: c.fg }}>{richText(b.text)}</p>
}
function Delta({ b, c }) {
  return (
    <div className="mt-3 flex items-end gap-3">
      {b.from && (
        <div>
          {b.from_caption && <div className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: c.sub }}>{b.from_caption}</div>}
          <div className="text-[22px] line-through" style={{ ...serif, color: c.sub }}>{b.from}</div>
        </div>
      )}
      <div>
        {b.to_caption && <div className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: c.sub }}>{b.to_caption}</div>}
        <div className="text-[32px] leading-none" style={{ ...serif, color: c.fg }}>{b.to}</div>
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
          <span className="font-medium" style={{ color: c.fg }}>{r.strike && <span className="mr-1.5 line-through" style={{ color: c.sub }}>{r.strike}</span>}{r.v}</span>
        </div>
      ))}
    </div>
  )
}
function Steps({ b, c }) {
  const dot = (st) => (st === 'next' ? c.line : c.accent)
  return (
    <div className="mt-3 space-y-3 border-l pl-4" style={{ borderColor: c.line }}>
      {(b.steps || []).map((s, i) => (
        <div key={i} className="relative">
          <span className="absolute -left-[22px] top-1.5 h-1.5 w-1.5 rounded-full" style={{ background: dot(s.state), opacity: s.state === 'next' ? 0.6 : 1 }} />
          <div className="text-[14px] font-medium" style={{ color: s.state === 'next' ? c.sub : c.fg }}>{s.name}</div>
          {s.sub && <div className="text-[12px]" style={{ color: c.sub }}>{s.sub}</div>}
        </div>
      ))}
    </div>
  )
}
function Scopes({ b, c }) {
  return (
    <div className="mt-3">
      {b.account && <div className="text-[12px] font-medium" style={{ color: c.sub }}>{b.service} · {b.account}</div>}
      <ul className="mt-2 space-y-1.5">
        {(b.items || []).map((it, i) => (
          <li key={i} className="flex items-start gap-2 text-[13px]" style={{ color: c.fg }}><span style={{ color: c.accent }}>·</span>{it}</li>
        ))}
      </ul>
      {b.note && <div className="mt-2 text-[11px]" style={{ color: c.sub }}>{b.note}</div>}
    </div>
  )
}
function FileRow({ b, c }) {
  return (
    <div className="mt-3 flex items-center justify-between rounded-[15px] px-3 py-2.5" style={{ border: `1px solid ${c.line}` }}>
      <div>
        <div className="text-[13px] font-medium" style={{ color: c.fg }}>{b.name}</div>
        {b.meta && <div className="text-[11px]" style={{ color: c.sub }}>{b.meta}</div>}
      </div>
      <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: c.sub }}>{b.kind}</span>
    </div>
  )
}
function Graph({ b, c }) {
  const pts = b.points || []
  if (pts.length < 2) return null
  const w = 260, h = 54
  const min = Math.min(...pts), max = Math.max(...pts), range = max - min || 1
  const x = (i) => (i / (pts.length - 1)) * w
  const y = (v) => h - ((v - min) / range) * h
  const d = pts.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const ty = b.target != null ? y(b.target) : null
  return (
    <div className="mt-3">
      {b.current_label && <div className="text-[28px] leading-none" style={{ ...serif, color: c.fg }}>{b.current_label}</div>}
      <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 w-full" style={{ height: 48 }} preserveAspectRatio="none">
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
      {(b.actions || []).map((a) => (
        <button
          key={a.action_id}
          disabled={acting}
          onClick={() => onAct?.(a.action_id)}
          className="flex-1 rounded-[13px] px-3 py-2.5 text-[14.5px] font-bold transition active:translate-y-[1.5px] disabled:opacity-40"
          style={a.style === 'primary' ? c.primary : c.secondary}
        >
          {a.label}
        </button>
      ))}
    </div>
  )
}
function Footer({ b, c }) {
  return (
    <div className="mt-4 flex items-baseline justify-between text-[11px] font-medium" style={{ color: c.sub }}>
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
  const c = theme(card.theme)
  return (
    <div
      className="relative overflow-hidden rounded-[20px] px-[18px] py-5"
      style={{ background: c.bg, color: c.fg, boxShadow: c.shadow, transform: `rotate(${c.tilt})` }}
    >
      {c.grain && (
        <div aria-hidden className="pointer-events-none absolute inset-0" style={{ backgroundImage: GRAIN, opacity: 0.05, mixBlendMode: 'overlay' }} />
      )}
      <div className="relative">
        {card.blocks.map((b, i) => <Block key={i} b={b} c={c} onAct={onAct} acting={acting} />)}
      </div>
    </div>
  )
}
