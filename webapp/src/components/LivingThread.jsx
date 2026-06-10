// Living Memory Thread — when a topic surfaces, Donna briefly reveals how it
// connects in her mind (sleep → stress → review), then it settles to a faint
// presence. Invisible reasoning, made momentarily visible. Product-wide.
export default function LivingThread({ chain = [], className = '' }) {
  return (
    <div className={`living-thread flex items-center gap-2.5 ${className}`}>
      {chain.map((word, i) => (
        <span key={i} className="flex items-center gap-2.5">
          {i > 0 && (
            <span
              className="block h-px w-5 origin-left"
              style={{
                background: 'rgb(var(--soft))',
                opacity: 0.5,
                animation: `thread-grow 0.5s ease ${0.15 + i * 0.22}s both`,
              }}
            />
          )}
          <span
            className="whitespace-nowrap text-[12px] lowercase tracking-wide text-soft"
            style={{ animation: `fade-in 0.5s ease ${i * 0.22}s both` }}
          >
            {word}
          </span>
        </span>
      ))}
    </div>
  )
}
