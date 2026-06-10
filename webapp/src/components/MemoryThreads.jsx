// Memory Threads — Donna's signature visual language. Thin organic lines that
// drift slowly in the background, suggesting a connected life. Deliberately
// faint and ambient: a feeling, not a graph. Used behind Plan, transitions, etc.
const PATHS = [
  'M-5,34 C22,18 38,54 58,33 S96,28 110,50',
  'M-8,66 C20,52 34,86 62,70 S94,64 112,82',
  'M-6,14 C28,28 48,8 70,26 S98,18 112,16',
  'M-6,90 C26,78 52,96 74,82 S98,86 112,72',
]

export default function MemoryThreads({ className = '', opacity = 0.13 }) {
  return (
    <svg
      className={`pointer-events-none ${className}`}
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      fill="none"
      aria-hidden="true"
    >
      <g style={{ animation: 'drift 16s ease-in-out infinite' }}>
        {PATHS.map((d, i) => (
          <path
            key={i}
            d={d}
            stroke="rgb(var(--soft))"
            strokeOpacity={opacity}
            strokeWidth="0.5"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </g>
    </svg>
  )
}
