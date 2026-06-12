import { useMemo, useState } from 'react'

// A constellation of a life. YOU is the still center; people, projects, goals,
// patterns and observations float around you, breathing, connected by thin
// threads. Tap a memory and its connections light up. Not a graph widget —
// a night sky of what Donna remembers.

const YOU = { id: 'you', x: 50, y: 50 }

const NODES = [
  { id: 'poke', label: 'poke', x: 28, y: 27, weight: 1, recent: true },
  { id: 'sequoia', label: 'sequoia', x: 72, y: 23, weight: 1, recent: true, supports: { belief: 'you avoid outreach when the story feels weak', conf: 74 } },
  { id: 'raghav', label: 'raghav', x: 16, y: 55, weight: 0.92, supports: { belief: 'you trust raghav on product, push back on pricing', conf: 82 } },
  { id: 'aniroodh', label: 'aniroodh', x: 86, y: 52, weight: 0.82, supports: { belief: 'you keep family time even mid-sprint', conf: 77 } },
  { id: 'pitch', label: 'pitch nerves', x: 55, y: 13, weight: 0.86, recent: true, supports: { belief: 'you overprepare when uncertain', conf: 84 } },
  { id: 'sleep', label: 'sleep', x: 38, y: 86, weight: 0.84, supports: { belief: 'sleep predicts your stress better than workload', conf: 89 } },
  { id: 'mornings', label: 'mornings', x: 81, y: 81, weight: 0.78, supports: { belief: 'your best work happens before noon', conf: 92 } },
  { id: 'move', label: 'the move', x: 18, y: 84, weight: 0.78, supports: { belief: "you won't relocate with the round still open", conf: 73 } },
]

const LINKS = [
  ...NODES.map((n) => ['you', n.id]),
  ['poke', 'raghav'],
  ['sequoia', 'pitch'],
  ['pitch', 'sleep'],
  ['sequoia', 'move'],
]

const POS = Object.fromEntries([[YOU.id, YOU], ...NODES.map((n) => [n.id, n])])
const LABEL = Object.fromEntries(NODES.map((n) => [n.id, n.label]))

// faint fixed starfield
const STARS = [
  [12, 18], [88, 14], [22, 40], [66, 8], [44, 32], [78, 44],
  [10, 70], [92, 74], [34, 64], [60, 90], [50, 70], [70, 64], [26, 92], [84, 32],
]

function curve(a, b) {
  const mx = (a.x + b.x) / 2
  const my = (a.y + b.y) / 2
  const dx = b.x - a.x
  const dy = b.y - a.y
  const cx = mx - dy * 0.12
  const cy = my + dx * 0.12
  return `M${a.x},${a.y} Q${cx},${cy} ${b.x},${b.y}`
}

export default function MemoryConstellation() {
  const [active, setActive] = useState(null)

  const adj = useMemo(() => {
    const m = {}
    for (const [a, b] of LINKS) {
      ;(m[a] ||= new Set()).add(b)
      ;(m[b] ||= new Set()).add(a)
    }
    return m
  }, [])

  const connections = active ? [...(adj[active] || [])].filter((id) => id !== 'you') : []

  return (
    <div className="relative aspect-square w-full select-none" onClick={() => setActive(null)}>
      {/* starfield */}
      {STARS.map(([x, y], i) => (
        <span
          key={i}
          className="absolute h-[2px] w-[2px] rounded-full"
          style={{
            left: `${x}%`,
            top: `${y}%`,
            background: 'rgb(var(--soft))',
            animation: `twinkle ${4 + (i % 5)}s ease-in-out ${i * 0.3}s infinite`,
          }}
        />
      ))}

      {/* threads */}
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        fill="none"
        aria-hidden="true"
      >
        {LINKS.map(([a, b], i) => {
          const touches = active && (a === active || b === active)
          const dim = active && !touches
          return (
            <path
              key={i}
              d={curve(POS[a], POS[b])}
              stroke={touches ? 'rgb(var(--rust))' : 'rgb(var(--soft))'}
              strokeOpacity={dim ? 0.05 : touches ? 0.6 : a === 'you' || b === 'you' ? 0.26 : 0.14}
              strokeWidth={touches ? 0.7 : 0.5}
              vectorEffect="non-scaling-stroke"
              style={{ transition: 'stroke-opacity 0.6s ease' }}
            />
          )
        })}
      </svg>

      {/* you — the still center */}
      <div className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: '50%', top: '50%' }}>
        <div className="relative grid h-[66px] w-[66px] place-items-center">
          <span className="absolute inset-0 rounded-full border" style={{ borderColor: 'rgb(var(--rust))', opacity: 0.4 }} />
          <span className="absolute inset-[9px] rounded-full" style={{ background: 'rgb(var(--surface))' }} />
          <span className="relative font-serif text-2xl lowercase text-ink">you</span>
        </div>
      </div>

      {/* memories */}
      {NODES.map((n, i) => {
        const isActive = active === n.id
        const isAdj = active && adj[active]?.has(n.id)
        const dim = active && !isActive && !isAdj
        return (
          <button
            key={n.id}
            onClick={(e) => {
              e.stopPropagation()
              setActive((a) => (a === n.id ? null : n.id))
            }}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${n.x}%`, top: `${n.y}%` }}
          >
            <div style={{ animation: `float ${9 + (i % 5) * 1.6}s ease-in-out ${i * 0.5}s infinite` }}>
              <div style={{ animation: `breathe ${6 + (i % 4)}s ease-in-out ${i * 0.4}s infinite` }}>
                <div className="relative flex flex-col items-center gap-1" style={{ transition: 'opacity 0.5s ease', opacity: dim ? 0.22 : 1 }}>
                  {n.recent && (
                    <span
                      className="absolute left-1/2 top-1 h-7 w-7 -translate-x-1/2 rounded-full blur-md"
                      style={{ background: 'rgb(var(--rust))', animation: `glow ${5 + (i % 3)}s ease-in-out infinite` }}
                    />
                  )}
                  <span
                    className="relative rounded-full"
                    style={{
                      width: 4 * n.weight + 3,
                      height: 4 * n.weight + 3,
                      background: isActive ? 'rgb(var(--rust))' : 'rgb(var(--soft))',
                      opacity: isActive ? 0.9 : 0.55,
                    }}
                  />
                  <span
                    className="relative whitespace-nowrap font-serif lowercase text-ink"
                    style={{ fontSize: 15 + n.weight * 4, opacity: 0.55 + n.weight * 0.35 }}
                  >
                    {n.label}
                  </span>
                </div>
              </div>
            </div>
          </button>
        )
      })}

      {/* on tap — reveal the belief this memory supports (memory → intelligence) */}
      <div className="absolute inset-x-0 bottom-0 px-4 text-center">
        {active &&
          (POS[active]?.supports ? (
            <div className="fade-in">
              <span className="label">supports</span>
              <p className="mt-1.5 font-serif text-[16px] leading-snug text-ink">
                {POS[active].supports.belief}
              </p>
              <span className="mt-1 inline-block text-[12px] tabular-nums text-soft">
                {POS[active].supports.conf}% confident
              </span>
            </div>
          ) : (
            <span className="fade-in text-[12px] lowercase tracking-wide text-soft">
              {LABEL[active]} &nbsp;·&nbsp; {connections.map((id) => LABEL[id]).join('  ·  ')}
            </span>
          ))}
      </div>
    </div>
  )
}
