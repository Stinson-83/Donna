import { useEffect, useState } from 'react'
import TodayPage from '../../pages/TodayPage.jsx'
import Drawer from '../../components/Drawer.jsx'
import TabBar from '../../components/TabBar.jsx'

// S1.5 — the dashboard beat. Plays a scripted tour: hold on the top (the Boka
// attention card + watch bar), scroll down through trackers / watches / schedule /
// reminders, scroll back up, then tap the menu to open the Library drawer
// ("everything she's holding"). All motion is setTimeout-stepped so it advances
// frame-by-frame under the capture clock.

const easeInOut = (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2)

export default function DashboardScene() {
  const [drawer, setDrawer] = useState(false)

  useEffect(() => {
    let cancelled = false
    const timers = []
    const add = (d, fn) => timers.push(setTimeout(() => { if (!cancelled) fn() }, d))
    const FR = 33
    const feed = () => document.querySelector('[data-dash-feed]')

    // glide the feed from its current scrollTop to toFn(el), eased, over `dur` ms
    function glide(startMs, dur, toFn) {
      const steps = Math.max(1, Math.round(dur / FR))
      let from = 0, to = 0, init = false
      for (let i = 0; i <= steps; i++) {
        add(startMs + i * FR, () => {
          const el = feed(); if (!el) return
          if (!init) { from = el.scrollTop; to = toFn(el); init = true }
          el.scrollTop = from + (to - from) * easeInOut(i / steps)
        })
      }
    }

    let at = 850
    glide(at, 3200, (el) => el.scrollHeight - el.clientHeight); at += 3200 + 650 // scroll down + hold bottom
    glide(at, 1150, () => 0); at += 1150 + 350                                   // scroll back up + settle
    add(at, () => setDrawer(true)); at += 500 + 3000                             // open the menu + hold (full reveal)
    const total = at + 250
    window.__demoPlay = { done: false, duration: total }
    add(total, () => { window.__demoPlay = { done: true, duration: total } })
    return () => { cancelled = true; timers.forEach(clearTimeout) }
  }, [])

  return (
    <div className="relative flex h-full flex-col">
      <div className="relative flex flex-1 flex-col overflow-hidden">
        <TodayPage onMenu={() => setDrawer(true)} />
      </div>
      <TabBar tab="dashboard" onChange={() => {}} />
      <Drawer open={drawer} onClose={() => {}} onNavigate={() => {}} />
    </div>
  )
}
