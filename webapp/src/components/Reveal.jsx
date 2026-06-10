// Calm staggered entrance. Wrap content and pass a delay (ms). Replays whenever
// the element remounts (e.g. page change via a keyed parent).
export default function Reveal({ delay = 0, className = '', style, children }) {
  return (
    <div className={`reveal ${className}`} style={{ animationDelay: `${delay}ms`, ...style }}>
      {children}
    </div>
  )
}
