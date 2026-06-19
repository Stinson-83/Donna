// Design-spec navigation (donna-design-spec): Dashboard / Beliefs / Memory / Live / History.
// Understanding-first: beliefs (what Donna believes) + memory (the evidence) sit
// right after the dashboard; live + history hold the conversation.
// Single-weight stroke icons + label; rust marks the active tab.
const ICON = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  ),
  beliefs: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18h6M10 21h4" /><path d="M12 3a6 6 0 0 0-3.8 10.6c.5.5.8 1.2.8 1.9v.5h6v-.5c0-.7.3-1.4.8-1.9A6 6 0 0 0 12 3z" />
    </svg>
  ),
  memory: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="6" cy="7" r="1.4" /><circle cx="18" cy="8.5" r="1.4" /><circle cx="9" cy="17.5" r="1.4" /><circle cx="16.5" cy="16" r="1.4" />
      <path d="M7.3 7.6 8 16.2M7.2 7.9 16.7 8.2M9.9 16.9 15.2 16.2M16.6 9.7 16.5 14.6" />
    </svg>
  ),
  live: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.3 8.8 8.8 0 0 1-3.9-.9L3 20l1.2-5.3a8 8 0 0 1-.7-3.2A8.4 8.4 0 0 1 12 3.2a8.4 8.4 0 0 1 9 8.3z" />
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
  { key: 'beliefs', label: 'Beliefs' },
  { key: 'memory', label: 'Memory' },
  { key: 'live', label: 'Live' },
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
