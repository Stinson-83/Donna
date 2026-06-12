// Design-spec navigation (donna-design-spec): Dashboard / Live / Memory / History.
// Single-weight stroke icons + label; rust marks the active tab.
const ICON = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  ),
  live: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.3 8.8 8.8 0 0 1-3.9-.9L3 20l1.2-5.3a8 8 0 0 1-.7-3.2A8.4 8.4 0 0 1 12 3.2a8.4 8.4 0 0 1 9 8.3z" />
    </svg>
  ),
  memory: (
    // a small constellation — "what donna knows" (mirrors the MemoryPage hero)
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="2.3" /><circle cx="5" cy="6" r="1.5" /><circle cx="19" cy="7" r="1.5" /><circle cx="7.5" cy="19" r="1.5" />
      <path d="M10.1 10.6 6.2 7.2M14 11.1 17.5 8.2M11 14 8.4 17.4" />
    </svg>
  ),
  history: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" />
    </svg>
  ),
}

const TABS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'live', label: 'Live' },
  { key: 'memory', label: 'Memory' },
  { key: 'history', label: 'History' },
]

export default function TabBar({ tab, onChange }) {
  return (
    <div
      className="safe-bottom safe-x z-20 flex"
      style={{ background: 'rgba(248,243,236,0.94)', borderTop: '1px solid rgba(63,46,35,0.05)' }}
    >
      {TABS.map((t) => {
        const active = tab === t.key
        return (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            className={`flex flex-1 flex-col items-center gap-[3px] pb-1 pt-2.5 transition-colors ${active ? 'text-accent' : 'text-faint'}`}
          >
            <span className="h-[22px] w-[22px]">{ICON[t.key]}</span>
            <span className="text-[10.5px] font-semibold">{t.label}</span>
          </button>
        )
      })}
    </div>
  )
}
