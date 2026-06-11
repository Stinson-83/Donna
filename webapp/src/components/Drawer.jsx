import { useEffect, useState } from 'react'
import { getLibrary, getSettings, setNotifyChannel } from '../cards.js'

// The Library drawer (donna-design-spec/reference/dashboard-v3 — the menu panel).
// "everything she's holding for you": real counts of people, documents, trackers
// (active watches), to-dos (open loops) and connected accounts, plus Settings —
// which is where the notify-channel preference becomes changeable post-onboarding.

const DRAWER_BG =
  'radial-gradient(120% 40% at 30% -5%, rgb(var(--surface-warm)) 0%, rgb(var(--bg)) 60%, rgb(var(--bg-deep)) 100%)'

const CHANNELS = [
  { key: 'auto', label: 'Either', hint: 'app if installed, else whatsapp' },
  { key: 'app', label: 'App', hint: 'push to the app' },
  { key: 'whatsapp', label: 'WhatsApp', hint: 'always whatsapp' },
]

function Chevron() {
  return (
    <svg
      className="ml-auto h-[15px] w-[15px] flex-shrink-0 text-faint"
      viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  )
}

export default function Drawer({ open, onClose, onNavigate }) {
  const [lib, setLib] = useState(null)
  const [view, setView] = useState('browse') // browse | settings

  useEffect(() => {
    if (open) getLibrary().then(setLib).catch(() => {})
    else setView('browse') // always reopen on the browse view
  }, [open])

  return (
    <>
      {/* scrim */}
      <div
        onClick={onClose}
        className={`absolute inset-0 z-40 transition-opacity duration-300 ${
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        style={{ background: 'rgba(32,22,14,0.35)', backdropFilter: 'blur(2px)', WebkitBackdropFilter: 'blur(2px)' }}
      />
      <aside
        className="absolute inset-y-0 left-0 z-50 flex w-[79%] max-w-[330px] flex-col border-r border-line"
        style={{
          background: DRAWER_BG,
          transform: open ? 'none' : 'translateX(-104%)',
          transition: 'transform 0.38s cubic-bezier(0.22,1,0.36,1)',
          boxShadow: open ? '8px 0 40px rgba(32,22,14,0.25)' : 'none',
        }}
      >
        {view === 'settings' ? (
          <SettingsView onBack={() => setView('browse')} />
        ) : (
          <Browse lib={lib} onClose={onClose} onNavigate={onNavigate} onSettings={() => setView('settings')} />
        )}
      </aside>
    </>
  )
}

function Row({ name, count, onClick, active }) {
  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className={`flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left transition active:bg-ink/5 ${
        active ? 'bg-rust/[0.08]' : ''
      } ${onClick ? '' : 'cursor-default'}`}
    >
      <div className="min-w-0">
        <div className={`text-[14.5px] font-bold ${active ? 'text-rust' : 'text-ink'}`}>{name}</div>
        {count != null && <div className="mt-px text-[11px] font-semibold text-faint">{count}</div>}
      </div>
      {onClick && !active && <Chevron />}
    </button>
  )
}

function Browse({ lib, onClose, onNavigate, onSettings }) {
  const n = (v) => (v == null ? '—' : v)
  const plural = (v, one, many) => (v === 1 ? one : many)

  function goToday() {
    onNavigate?.('dashboard')
    onClose?.()
  }

  return (
    <>
      <div className="flex-shrink-0 border-b border-line px-[22px] pb-4 pt-[calc(20px+env(safe-area-inset-top))]">
        <div className="font-serif text-[24px] tracking-tight text-ink">Library</div>
        <div className="mt-0.5 text-[12px] font-semibold text-faint">everything she's holding for you</div>
      </div>

      <div className="scroll flex-1 overflow-y-auto px-3 py-2.5">
        <div className="mb-1.5 mt-3 px-3 text-[10px] font-bold uppercase tracking-[0.09em] text-faint">Browse</div>

        <Row name="Today" count="the live view" active onClick={goToday} />
        <Row name="People" count={lib ? `${n(lib.people)} ${plural(lib.people, 'person', 'people')}` : null} />
        <Row name="Documents" count={lib ? `${n(lib.documents)} ${plural(lib.documents, 'file', 'files')}` : null} />
        <Row name="Trackers" count={lib ? `${n(lib.trackers)} active` : null} />
        <Row name="To-dos" count={lib ? `${n(lib.todos)} open` : null} />
        <Row name="Connected" count={lib ? `${n(lib.connected)} ${plural(lib.connected, 'account', 'accounts')}` : null} />
      </div>

      <div className="flex-shrink-0 border-t border-line px-3 pb-[calc(16px+env(safe-area-inset-bottom))] pt-3">
        <button
          onClick={onSettings}
          className="flex w-full items-center gap-2.5 rounded-2xl px-3 py-3 text-left text-[13.5px] font-semibold text-soft transition active:bg-ink/5"
        >
          <svg className="h-[18px] w-[18px] text-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
          </svg>
          Settings
        </button>
      </div>
    </>
  )
}

function SettingsView({ onBack }) {
  const [channel, setChannel] = useState(null) // null until loaded
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getSettings().then((s) => setChannel(s.notify_channel || 'auto')).catch(() => setChannel('auto'))
  }, [])

  async function pick(key) {
    if (key === channel) return
    const prev = channel
    setChannel(key)
    setSaving(true)
    try {
      await setNotifyChannel(key)
    } catch {
      setChannel(prev) // revert on failure
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="flex flex-shrink-0 items-center gap-3 border-b border-line px-[18px] pb-4 pt-[calc(20px+env(safe-area-inset-top))]">
        <button onClick={onBack} className="grid h-9 w-9 flex-shrink-0 place-items-center rounded-full border border-line bg-surface text-soft transition active:bg-ink/5">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 6l-6 6 6 6" />
          </svg>
        </button>
        <div className="font-serif text-[22px] tracking-tight text-ink">Settings</div>
      </div>

      <div className="scroll flex-1 overflow-y-auto px-[18px] py-5">
        <div className="mb-2.5 text-[10px] font-bold uppercase tracking-[0.09em] text-faint">reach me on</div>
        <div className="space-y-2">
          {CHANNELS.map((c) => {
            const on = channel === c.key
            return (
              <button
                key={c.key}
                onClick={() => pick(c.key)}
                disabled={saving || channel == null}
                className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition ${
                  on ? 'border-rust bg-rust/[0.08]' : 'border-line bg-surface'
                }`}
              >
                <div className="min-w-0">
                  <div className={`text-[14.5px] font-bold ${on ? 'text-rust' : 'text-ink'}`}>{c.label}</div>
                  <div className="mt-px text-[11.5px] text-faint">{c.hint}</div>
                </div>
                <span className={`ml-auto grid h-5 w-5 flex-shrink-0 place-items-center rounded-full border ${on ? 'border-rust bg-rust text-white' : 'border-line'}`}>
                  {on && (
                    <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 12l5 5L20 6" />
                    </svg>
                  )}
                </span>
              </button>
            )
          })}
        </div>
        <p className="mt-4 px-1 text-[12px] leading-relaxed text-faint">
          she alerts you on one surface, never both. this sets which one she prefers — the other is just a fallback.
        </p>
      </div>
    </>
  )
}
