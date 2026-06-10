// Quiet, editorial navigation. No filled icons, no badges — just words, with a
// single rust mark under the active tab (rust used sparingly, by design).
const TABS = [
  { key: 'plan', label: 'plan' },
  { key: 'chat', label: 'chat' },
  { key: 'beliefs', label: 'beliefs' },
  { key: 'memory', label: 'memory' },
]

export default function TabBar({ tab, onChange }) {
  return (
    <div className="z-20 flex items-stretch px-6 pb-3 pt-2.5">
      {TABS.map((t) => {
        const active = tab === t.key
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className="flex flex-1 flex-col items-center gap-1.5 py-1"
          >
            <span
              className={`text-[13px] lowercase tracking-wide transition-colors duration-300 ${
                active ? 'text-ink' : 'text-soft/60'
              }`}
            >
              {t.label}
            </span>
            <span
              className="h-[3px] w-[3px] rounded-full transition-all duration-300"
              style={{ background: active ? 'rgb(var(--rust))' : 'transparent' }}
            />
          </button>
        )
      })}
    </div>
  )
}
