import { useEffect, useState } from 'react'
import Card from '../components/Card.jsx'
import WatchBar from '../components/WatchBar.jsx'
import { actCard, getCards, getToday, getWatchbar, getWatches } from '../cards.js'

// The Today / Dashboard screen (donna-design-spec/reference/dashboard-v3).
// Needs-you cards (the hero is the top dark card) → watching → your day → pulse.
export default function TodayPage({ onMenu }) {
  const [cards, setCards] = useState([])
  const [watching, setWatching] = useState([])
  const [today, setToday] = useState({ calendar: [], holding: 0, date: '' })
  const [bar, setBar] = useState([])
  const [acting, setActing] = useState(null)
  const [ready, setReady] = useState(false)

  async function load() {
    try {
      const [cs, ws, td, wb] = await Promise.all([getCards(), getWatches(), getToday(), getWatchbar()])
      setCards(cs.cards || [])
      setWatching(ws.watching || [])
      setToday(td || {})
      setBar(wb.items || [])
    } catch {
      /* fail soft */
    } finally {
      setReady(true)
    }
  }
  useEffect(() => { load() }, [])

  async function onAct(cardId, actionId) {
    setActing(cardId)
    try {
      const res = await actCard(cardId, actionId)
      if (Array.isArray(res.cards)) setCards(res.cards)
      else setCards((cs) => cs.filter((c) => c.card_id !== cardId))
    } catch {
      /* leave the card */
    } finally {
      setActing(null)
    }
  }

  // trackers are passive widgets (a fare graph), not "needs you" decisions — split them out
  const needCards = cards.filter((c) => c.intent !== 'tracker')
  const trackerCards = cards.filter((c) => c.intent === 'tracker')
  const empty = ready && cards.length === 0 && watching.length === 0 && (today.calendar?.length || 0) === 0 && !(today.done?.length) && !today.lifetime

  return (
    <div className="flex h-full flex-col">
      {/* nav */}
      <div className="flex flex-shrink-0 items-center justify-between px-5 pb-3 pt-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onMenu}
            aria-label="open library"
            className="grid h-9 w-9 place-items-center rounded-full border border-line bg-surface text-soft shadow-bubble transition active:bg-ink/5"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 7h16M4 12h16M4 17h10" />
            </svg>
          </button>
          <h1 className="font-serif text-[28px] leading-none text-ink">Today</h1>
        </div>
        <span className="sec mr-9">{today.date}</span>
      </div>

      {/* the dynamic watch bar — pinned "what matters now" */}
      <WatchBar items={bar} />

      <div data-dash-feed className="scroll flex-1 overflow-y-auto px-[18px] pb-28 pt-1">
        {/* NEEDS YOU — the decision cards (top dark card is the hero) */}
        {needCards.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">needs you · {needCards.length}</div>
            <div className="space-y-4">
              {needCards.map((card) => (
                <Card key={card.card_id} card={card} acting={acting === card.card_id} onAct={(a) => onAct(card.card_id, a)} />
              ))}
            </div>
          </section>
        )}

        {/* TRACKING — passive tracker cards (fare graphs etc.) she watches for you */}
        {trackerCards.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">tracking · {trackerCards.length}</div>
            <div className="space-y-4">
              {trackerCards.map((card) => (
                <Card key={card.card_id} card={card} acting={acting === card.card_id} onAct={(a) => onAct(card.card_id, a)} />
              ))}
            </div>
          </section>
        )}

        {/* WATCHING */}
        {watching.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">watching · {watching.length}</div>
            <div className="overflow-hidden rounded-[18px] border border-line bg-surface" style={{ boxShadow: '0 1px 1px rgba(63,42,30,0.05), 0 10px 20px rgba(63,42,30,0.05)' }}>
              {watching.map((w, i) => (
                <div key={w.id} className={`flex items-center gap-3 px-[17px] py-3 ${i ? 'border-t border-line' : ''}`}>
                  <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full" style={{ background: w.type === 'reply' ? 'rgb(var(--accent))' : '#C99A7E' }} />
                  <span className="truncate text-[14px] font-semibold text-ink/80">{w.title}</span>
                  <span className="ml-auto flex-shrink-0 text-[11px] font-bold uppercase tracking-wide text-faint">{w.type}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* YOUR DAY — the rail */}
        {today.calendar?.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">your day</div>
            <div className="overflow-hidden rounded-[18px] border border-line bg-surface" style={{ boxShadow: '0 1px 1px rgba(63,42,30,0.05)' }}>
              {today.calendar.map((e, i) => (
                <div key={i} className={`flex items-start gap-3 px-[17px] py-2.5 ${i ? 'border-t border-line' : ''}`}>
                  <span className="w-[58px] flex-shrink-0 pt-px text-[12.5px] font-bold tabular-nums text-faint">{e.time}</span>
                  <div>
                    <div className="text-[14px] font-semibold text-ink/85">{e.title}</div>
                    {e.note && <div className="mt-px text-[11.5px] text-faint">{e.note}</div>}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* TRACKERS — glanceable stats she keeps (calories / sleep / gym / spend) */}
        {today.trackers?.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">trackers</div>
            <div className="grid grid-cols-2 gap-2">
              {today.trackers.map((t, i) => (
                <div key={i} className="rounded-[16px] border border-line bg-surface px-3.5 py-3" style={{ boxShadow: '0 1px 1px rgba(63,42,30,0.05)' }}>
                  <div className="font-serif text-[23px] leading-none text-ink">{t.value}</div>
                  <div className="mt-1 text-[11px] font-semibold text-faint">{t.label}{t.sub ? ` · ${t.sub}` : ''}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* SCHEDULED — tasks with a due time */}
        {today.scheduled?.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">scheduled · {today.scheduled.length}</div>
            <div className="overflow-hidden rounded-[18px] border border-line bg-surface" style={{ boxShadow: '0 1px 1px rgba(63,42,30,0.05)' }}>
              {today.scheduled.map((s, i) => (
                <div key={i} className={`flex items-center gap-3 px-[17px] py-3 ${i ? 'border-t border-line' : ''}`}>
                  <svg className="h-[15px] w-[15px] flex-shrink-0 text-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="9" /><path d="M12 8v4l2.5 1.5" />
                  </svg>
                  <span className="min-w-0 flex-1 truncate text-[14px] font-semibold text-ink/80">{s.title}</span>
                  <span className={`flex-shrink-0 text-[11px] font-bold ${s.urgent ? 'text-rust' : 'text-faint'}`}>{s.when}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* TODAY · DONE — the day's resolved wins (M9 close, demo) */}
        {today.done?.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">today · done · {today.done.length}</div>
            <div className="overflow-hidden rounded-[18px] border border-line bg-surface" style={{ boxShadow: '0 1px 1px rgba(63,42,30,0.05)' }}>
              {today.done.map((d, i) => (
                <div key={i} className={`flex items-center gap-3 px-[17px] py-2.5 ${i ? 'border-t border-line' : ''}`}>
                  <svg className="h-3.5 w-3.5 flex-shrink-0 text-rust" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 6" /></svg>
                  <span className="flex-1 text-[13.5px] text-ink/80">{d.text}</span>
                  <span className="flex-shrink-0 text-[11px] font-bold tabular-nums text-faint">{d.time}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* STILL HOLDING */}
        {today.holding_open?.length > 0 && (
          <section className="mb-[22px]">
            <div className="sec mb-2.5">still holding · {today.holding_open.length}</div>
            <div className="overflow-hidden rounded-[18px] border border-line bg-surface" style={{ boxShadow: '0 1px 1px rgba(63,42,30,0.05)' }}>
              {today.holding_open.map((w, i) => (
                <div key={i} className={`flex items-center gap-3 px-[17px] py-3 ${i ? 'border-t border-line' : ''}`}>
                  <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full" style={{ background: '#C99A7E' }} />
                  <span className="truncate text-[14px] font-semibold text-ink/80">{w.title}</span>
                  <span className="ml-auto flex-shrink-0 text-[11px] font-bold uppercase tracking-wide text-faint">{w.type}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* THE MOAT — lifetime stats */}
        {today.lifetime && (
          <section className="mb-[22px] grid grid-cols-3 gap-2 text-center">
            {[['days with donna', today.lifetime.days], ['things caught', today.lifetime.caught], ['on time', today.lifetime.on_time]].map(([label, val], i) => (
              <div key={i} className="rounded-[16px] border border-line bg-surface py-4">
                <div className="font-serif text-[25px] leading-none text-ink">{val}</div>
                <div className="mt-1 px-1 text-[9px] font-bold uppercase leading-tight tracking-wide text-faint">{label}</div>
              </div>
            ))}
          </section>
        )}

        {/* empty */}
        {empty && (
          <div className="px-2 pt-12">
            <h2 className="font-serif text-[26px] lowercase text-ink">all quiet.</h2>
            <p className="mt-2.5 text-[14.5px] leading-relaxed lowercase text-soft">
              nothing needs you right now. connect your accounts and i'll start
              filling this in — what matters, who's waiting, what to watch.
            </p>
          </div>
        )}

        {/* pulse */}
        {today.holding > 0 && !today.done && (
          <div className="pt-1 text-center text-[12px] font-semibold text-faint">
            holding <b className="text-soft">{today.holding} things</b> · all quiet otherwise
          </div>
        )}
      </div>
    </div>
  )
}
