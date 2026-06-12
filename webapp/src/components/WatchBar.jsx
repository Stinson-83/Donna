// The Dynamic Watch Bar ("Dynamic Island for life"): a pinned, horizontally
// scrolling strip of what Donna believes deserves attention right now, ordered by
// priority and reordering live. Backed by GET /watchbar (knowledge.attention).
const TIER = {
  critical: { dot: 'rgb(var(--rust))', ring: 'rgb(var(--rust) / 0.28)' },
  high: { dot: '#C99A7E', ring: 'rgb(201 154 126 / 0.28)' },
  medium: { dot: 'rgb(var(--soft))', ring: 'rgb(var(--line))' },
  low: { dot: 'rgb(var(--faint))', ring: 'rgb(var(--line))' },
}

export default function WatchBar({ items }) {
  if (!items?.length) return null
  return (
    <div className="flex-shrink-0 pb-2.5 pt-0.5">
      <div className="sec mb-2 px-[18px]">what matters now</div>
      <div className="scroll flex gap-2 overflow-x-auto px-[18px] pb-1">
        {items.map((it) => {
          const t = TIER[it.tier] || TIER.low
          return (
            <div
              key={`${it.kind}:${it.ref_id}`}
              className="flex min-w-[148px] max-w-[210px] flex-shrink-0 items-center gap-2.5 rounded-full border bg-surface px-3 py-2"
              style={{ borderColor: t.ring, boxShadow: '0 1px 2px rgba(63,42,30,0.05)' }}
            >
              <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ background: t.dot }} />
              <div className="min-w-0">
                <div className="truncate text-[12.5px] font-semibold leading-tight text-ink/85">{it.title}</div>
                {it.note && <div className="truncate text-[10.5px] leading-tight text-faint">{it.note}</div>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
