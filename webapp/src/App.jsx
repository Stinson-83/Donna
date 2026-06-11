import { useEffect, useState } from 'react'
import { applyTheme, initNative } from './native.js'
import { initPush } from './push.js'
import PhoneFrame from './components/PhoneFrame.jsx'
import TabBar from './components/TabBar.jsx'
import Fab from './components/Fab.jsx'
import Capture from './components/Capture.jsx'
import Onboarding from './components/Onboarding.jsx'
import TodayPage from './pages/TodayPage.jsx'
import LivePage from './pages/LivePage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import { hasIdentity, getUserId } from './identity.js'

const PAGES = { dashboard: TodayPage, live: LivePage, history: HistoryPage }

export default function App() {
  const [tab, setTab] = useState('dashboard')
  // First-run identity gate. A version bump re-renders (and remounts pages on a
  // new id) once they claim a profile or pick the demo.
  const [ident, setIdent] = useState(0)
  const [capture, setCapture] = useState(null) // null | 'journal' | 'capture' | 'voice'
  // Donna notices the time of day. Evenings open in Night.
  const hour = new Date().getHours()
  const [night, setNight] = useState(hour >= 19 || hour < 6)

  // Native: hide splash once mounted, keep the status bar in sync with theme.
  useEffect(() => {
    initNative(night)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    applyTheme(night)
  }, [night])

  // Once we know who's using the app, register for push under that identity.
  // Re-runs on identity change (demo -> claimed profile) to re-key the token.
  useEffect(() => {
    if (hasIdentity()) initPush(() => setTab('chat'))
  }, [ident])

  if (!hasIdentity()) {
    return (
      <PhoneFrame night={night}>
        <Onboarding onDone={() => setIdent((v) => v + 1)} />
      </PhoneFrame>
    )
  }

  // The FAB leaves a thought with Donna. 'a thought' opens the live chat; the
  // rest open the quick-capture sheet, which writes into the cognition layer.
  function onFabAction(key) {
    if (key === 'chat') setTab('live')
    else setCapture(key)
  }

  const Page = PAGES[tab]

  return (
    <PhoneFrame night={night}>
      <div className="relative flex flex-1 flex-col overflow-hidden">
        {/* quiet theme toggle — the only chrome */}
        <button
          onClick={() => setNight((n) => !n)}
          aria-label="toggle light and dark"
          className="absolute right-5 top-4 z-30 text-soft/60 transition hover:text-soft"
        >
          {night ? (
            <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19" strokeLinecap="round" />
            </svg>
          ) : (
            <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z" strokeLinejoin="round" />
            </svg>
          )}
        </button>

        {/* page — keyed on identity + tab so it remounts (and refetches the
            right person's model) on navigation or a profile switch */}
        <div key={`${getUserId()}:${tab}`} className="fade-in flex flex-1 flex-col overflow-hidden">
          <Page />
        </div>

        {tab !== 'live' && <Fab onAction={onFabAction} />}
        {capture && <Capture kind={capture} onClose={() => setCapture(null)} />}
      </div>

      <TabBar tab={tab} onChange={setTab} />
    </PhoneFrame>
  )
}
