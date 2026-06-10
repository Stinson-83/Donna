import { useState } from 'react'
import PhoneFrame from './components/PhoneFrame.jsx'
import TabBar from './components/TabBar.jsx'
import Fab from './components/Fab.jsx'
import PlanPage from './pages/PlanPage.jsx'
import ChatPage from './pages/ChatPage.jsx'
import BeliefsPage from './pages/BeliefsPage.jsx'
import MemoryPage from './pages/MemoryPage.jsx'

const PAGES = { plan: PlanPage, chat: ChatPage, beliefs: BeliefsPage, memory: MemoryPage }

export default function App() {
  const [tab, setTab] = useState('plan')
  // Donna notices the time of day. Evenings open in Night.
  const hour = new Date().getHours()
  const [night, setNight] = useState(hour >= 19 || hour < 6)

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

        {/* page — keyed so the calm entrance replays on each navigation */}
        <div key={tab} className="fade-in flex flex-1 flex-col overflow-hidden">
          <Page />
        </div>

        {tab !== 'chat' && <Fab onAction={() => setTab('chat')} />}
      </div>

      <TabBar tab={tab} onChange={setTab} />
    </PhoneFrame>
  )
}
