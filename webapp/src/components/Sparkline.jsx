// Confidence history as rising bars — a belief, visibly alive. The latest value
// is rust; the rest are soft. Tiny by design; uses existing tokens only.
export default function Sparkline({ values = [], className = '' }) {
  if (values.length === 0) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = Math.max(max - min, 1)
  return (
    <span className={`inline-flex items-end gap-[3px] ${className}`} style={{ height: 18 }}>
      {values.map((v, i) => {
        const h = 6 + ((v - min) / range) * 12
        const last = i === values.length - 1
        return (
          <span
            key={i}
            className="w-[3px] rounded-full"
            style={{
              height: h,
              background: last ? 'rgb(var(--rust))' : 'rgb(var(--soft))',
              opacity: last ? 0.9 : 0.4,
            }}
          />
        )
      })}
    </span>
  )
}
