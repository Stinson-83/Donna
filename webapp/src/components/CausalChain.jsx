// "Why this matters" — Donna's reasoning made visible. A vertical causal chain
//   deck quality
//     ↓
//   investor confidence
//     ↓
//   fundraising
// Appears across the app wherever Donna explains how she thinks.
export default function CausalChain({ label, steps = [], className = '' }) {
  return (
    <div className={className}>
      {label && <div className="label mb-3">{label}</div>}
      <div className="flex flex-col">
        {steps.map((s, i) => (
          <div key={i}>
            {i > 0 && (
              <div
                className="ml-[2px] my-1.5 h-5 w-px origin-top"
                style={{
                  background: 'rgb(var(--soft))',
                  opacity: 0.45,
                  animation: `thread-grow-y 0.45s ease ${0.12 + i * 0.18}s both`,
                }}
              />
            )}
            <div
              className="text-[15px] lowercase text-ink"
              style={{ animation: `fade-in 0.5s ease ${i * 0.18}s both` }}
            >
              {s}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
