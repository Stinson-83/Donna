import { useEffect } from 'react'
import { applyTheme } from '../native.js'
import PhoneFrame from '../components/PhoneFrame.jsx'
import TabBar from '../components/TabBar.jsx'
import TodayPage from '../pages/TodayPage.jsx'
import LivePage from '../pages/LivePage.jsx'
import HistoryPage from '../pages/HistoryPage.jsx'
import DemoIsland from './surfaces/DemoIsland.jsx'
import DemoTitle from './surfaces/DemoTitle.jsx'
import WhatsApp from './surfaces/WhatsApp.jsx'
import DashboardScene from './surfaces/DashboardScene.jsx'
import OperatorStrip from './OperatorStrip.jsx'
import { SCENE_BY_ID, SCENES } from './scenes.js'
import { installScene } from './store.js'

const noop = () => {}

function Surface({ scene }) {
  switch (scene.surface) {
    case 'dashboard': return <DashboardScene />
    case 'live': return (
      <LivePage
        now={scene.at}
        seedThread={scene.play ? null : scene.chatThread}
        play={scene.play ? scene.chatThread : null}
      />
    )
    case 'history': return <HistoryPage />
    case 'whatsapp': return <WhatsApp history={scene.history || []} play={scene.play ? scene.chatThread : null} at={scene.at} />
    case 'island': return <DemoIsland {...(scene.island || {})} />
    case 'title': return <DemoTitle title={scene.title} sub={scene.sub} />
    default: return <DemoTitle title="unknown scene" />
  }
}

export default function DemoRoot() {
  const params = new URLSearchParams(window.location.search)
  const id = params.get('scene')
  const bare = params.has('bare')             // ?bare=1 → no operator strip (clean capture)
  const scene = SCENE_BY_ID[id] || SCENES[0]
  installScene(scene)                         // make fixtures live BEFORE the surface mounts

  useEffect(() => { applyTheme(false) }, [])  // paper treatment, always

  const isApp = ['live', 'history'].includes(scene.surface)  // dashboard renders its own tab bar

  return (
    <>
      {!bare && <OperatorStrip current={scene} />}
      <PhoneFrame night={false}>
        <div className="relative flex flex-1 flex-col overflow-hidden">
          <Surface scene={scene} />
          {/* live folds time into the pill; whatsapp + dashboard have their own headers */}
          {scene.at && !['live', 'whatsapp', 'dashboard'].includes(scene.surface) && (
            <div className="pointer-events-none absolute right-5 top-3 z-40 font-serif italic text-[13px] text-rust/90">
              {scene.at}
            </div>
          )}
        </div>
        {isApp && <TabBar tab={scene.tab || 'dashboard'} onChange={noop} />}
      </PhoneFrame>
    </>
  )
}
