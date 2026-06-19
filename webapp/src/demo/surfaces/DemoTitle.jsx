// Title + end card. Paper, the italic-serif rust wordmark, an optional sub-line.

export default function DemoTitle({ title = 'donna', sub }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-bg px-10 text-center">
      <div className="font-serif italic text-rust" style={{ fontSize: 58, letterSpacing: '-0.01em' }}>{title}</div>
      {sub && <div className="mt-4 font-serif text-[17px] text-soft">{sub}</div>}
    </div>
  )
}
