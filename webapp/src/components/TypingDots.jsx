export default function TypingDots() {
  return (
    <div className="mr-auto inline-flex items-center gap-1.5 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: 'rgb(var(--soft))', animation: `dot 1.2s ${i * 0.15}s infinite ease-in-out` }}
        />
      ))}
    </div>
  )
}
