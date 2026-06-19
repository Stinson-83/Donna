import { useEffect, useRef, useState } from 'react'

// A faithful WhatsApp chat surface for the "Meta moat" scene. donna is the contact
// (incoming, white bubbles); matt is the user (outgoing, green). It seeds the
// running history (Tue/Wed), scrolls through it, then plays today's exchange.

// ── timing (mirrors LivePage play mode) ──────────────────────────────────────
const textLen = (it) => (it.text || it.caption || '').length
const typeMs = (it) => Math.min(2100, 620 + textLen(it) * 15)
const tailMs = () => 560
const easeInOut = (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2)

function Waveform({ n = 26, color }) {
  return (
    <span className="flex items-center gap-[2px]">
      {Array.from({ length: n }).map((_, i) => {
        const h = 3 + Math.round(9 * Math.abs(Math.sin(i * 1.3) * Math.cos(i * 0.5)))
        return <span key={i} style={{ width: 2, height: h, borderRadius: 1, background: color, opacity: 0.5 + h / 26 }} />
      })}
    </span>
  )
}

function Play({ color }) {
  return <svg viewBox="0 0 24 24" className="h-4 w-4 flex-shrink-0" style={{ fill: color }}><path d="M8 5v14l11-7z" /></svg>
}

function Ticks() {
  return (
    <svg viewBox="0 0 18 12" className="h-3 w-[18px]" style={{ fill: 'none', stroke: '#53BDEB', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round' }}>
      <path d="M1 6.5l3 3 6-7" /><path d="M6.5 9.5l1 1 6-7" />
    </svg>
  )
}

function Divider({ label }) {
  return (
    <div className="my-2 flex justify-center">
      <div className="rounded-md bg-[#FCF5C7] px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-[#54656F] shadow-sm">{label}</div>
    </div>
  )
}

function Msg({ m, at, animate }) {
  if (m.divider) return <Divider label={m.divider} />
  const out = m.from === 'user'
  const it = m.item
  const ts = m.ts || at
  return (
    <div className={`${animate ? 'reveal ' : ''}mb-1.5 flex ${out ? 'justify-end' : 'justify-start'}`}>
      <div
        className="relative max-w-[82%] px-2 py-1.5 text-[14.5px] leading-[1.35] text-[#111B21]"
        style={{ background: out ? '#DCF8C6' : '#FFFFFF', borderRadius: 8, boxShadow: '0 1px 0.5px rgba(11,20,26,0.13)' }}
      >
        {it.type === 'voice' ? (
          <div className="flex items-center gap-2.5 py-0.5 pr-1">
            <div className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-full" style={{ background: out ? '#7B5544' : '#bfc7cc' }}><Play color="#fff" /></div>
            <Waveform color={out ? '#7B5544' : '#8696A0'} />
            <span className="ml-1 text-[11px] tabular-nums text-[#667781]">{it.dur || '0:03'}</span>
          </div>
        ) : it.type === 'link' ? (
          <>
            <div className="mb-1 overflow-hidden rounded-md border-l-[3px]" style={{ borderColor: '#7B5544', background: 'rgba(0,0,0,0.05)' }}>
              <div className="px-2.5 py-1.5">
                <div className="text-[13px] font-semibold leading-tight text-[#111B21]">{it.title}</div>
                <div className="mt-0.5 text-[11px] text-[#667781]">{it.domain}</div>
              </div>
            </div>
            <span className="px-1">{it.caption}</span>
          </>
        ) : it.type === 'pdf' ? (
          <>
            <div className="mb-1 flex items-center gap-2.5 rounded-md px-2 py-2" style={{ background: 'rgba(0,0,0,0.05)' }}>
              <span className="grid h-9 w-9 flex-shrink-0 place-items-center rounded" style={{ background: 'rgba(226,67,59,0.12)', color: '#E2433B' }}>
                <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3v5h5M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /></svg>
              </span>
              <div className="min-w-0">
                <div className="truncate text-[13px] font-semibold text-[#111B21]">{it.name}</div>
                <div className="text-[11px] text-[#667781]">{it.meta}</div>
              </div>
            </div>
            <span className="px-1">{it.caption}</span>
          </>
        ) : (
          <span className="px-1">{it.text}</span>
        )}
        <span className="float-right ml-2 mt-1 flex items-center gap-1 text-[10.5px] text-[#667781]">{ts}{out && <Ticks />}</span>
      </div>
    </div>
  )
}

export default function WhatsApp({ history = [], play = [], at = '7:32 PM' }) {
  const [messages, setMessages] = useState([])
  const [typing, setTyping] = useState(false)
  const feedRef = useRef(null)

  // keep the latest revealed message in view. instant (not smooth) — a compositor
  // smooth-scroll doesn't advance under the capture's virtual clock.
  useEffect(() => {
    if (messages.length) { const el = feedRef.current; if (el) el.scrollTop = el.scrollHeight }
  }, [messages])

  useEffect(() => {
    let cancelled = false
    const timers = []
    const add = (d, fn) => timers.push(setTimeout(() => { if (!cancelled) fn() }, d))
    const FR = 33
    if (feedRef.current) feedRef.current.scrollTop = 0 // start on the oldest history

    // scroll the feed from its current top to the bottom over `dur` ms
    function glide(startMs, dur) {
      const steps = Math.max(1, Math.round(dur / FR))
      let from = 0, to = 0, init = false
      for (let i = 0; i <= steps; i++) {
        add(startMs + i * FR, () => {
          const el = feedRef.current; if (!el) return
          if (!init) { from = el.scrollTop; to = Math.max(0, el.scrollHeight - el.clientHeight); init = true }
          el.scrollTop = from + (to - from) * easeInOut(i / steps)
        })
      }
    }

    let acc = 700
    if (history.length) { glide(acc, 1700); acc += 1700 + 700 } // read the history, land on TODAY
    play.forEach((m) => {
      if (m.from === 'donna') {
        add(acc, () => setTyping(true))
        acc += typeMs(m.item)
        add(acc, () => { setTyping(false); setMessages((c) => [...c, m]) })
        acc += tailMs()
      } else {
        acc += 760
        add(acc, () => setMessages((c) => [...c, m]))
        acc += 340
      }
    })
    acc += 850
    window.__demoPlay = { done: false, duration: acc }
    add(acc, () => { window.__demoPlay = { done: true, duration: acc } })
    return () => { cancelled = true; timers.forEach(clearTimeout) }
  }, [play, history])

  return (
    <div className="flex h-full flex-col" style={{ background: '#ECE5DD' }}>
      {/* header */}
      <div className="flex flex-shrink-0 items-center gap-3 px-3 py-2.5 text-white" style={{ background: '#075E54' }}>
        <svg viewBox="0 0 24 24" className="h-5 w-5" style={{ fill: 'none', stroke: '#fff', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' }}><path d="M15 18l-6-6 6-6" /></svg>
        <div className="grid h-9 w-9 place-items-center rounded-full" style={{ background: '#7B5544' }}>
          <span className="font-serif text-[18px] italic leading-none text-white">d</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[15px] font-semibold leading-tight">donna</div>
          <div className="text-[11.5px] leading-tight text-white/80">{typing ? 'typing…' : 'online'}</div>
        </div>
        <svg viewBox="0 0 24 24" className="h-5 w-5" style={{ fill: 'none', stroke: '#fff', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }}><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2" /></svg>
        <svg viewBox="0 0 24 24" className="h-5 w-5" style={{ fill: '#fff' }}><path d="M20 15.5c-1.2 0-2.5-.2-3.6-.6a1 1 0 0 0-1 .2l-2.2 2.2a15 15 0 0 1-6.6-6.6l2.2-2.2a1 1 0 0 0 .2-1A11.4 11.4 0 0 1 8.5 4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1 17 17 0 0 0 17 17 1 1 0 0 0 1-1v-3.5a1 1 0 0 0-1-1z" /></svg>
        <svg viewBox="0 0 24 24" className="h-5 w-5" style={{ fill: '#fff' }}><circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" /></svg>
      </div>

      {/* feed */}
      <div ref={feedRef} className="scroll flex-1 overflow-y-auto px-3 py-3"
        style={{ backgroundImage: 'radial-gradient(rgba(0,0,0,0.025) 1px, transparent 1px)', backgroundSize: '22px 22px' }}>
        {history.map((m, i) => <Msg key={`h${i}`} m={m} at={at} animate={false} />)}
        {history.length > 0 && <Divider label="TODAY" />}
        {messages.map((m, i) => <Msg key={`t${i}`} m={m} at={at} animate />)}
      </div>

      {/* composer */}
      <div className="flex flex-shrink-0 items-center gap-2 px-2 py-2" style={{ background: '#F0F2F5' }}>
        <div className="flex flex-1 items-center gap-2 rounded-full bg-white px-3 py-2.5 shadow-sm">
          <svg viewBox="0 0 24 24" className="h-5 w-5" style={{ fill: 'none', stroke: '#8696A0', strokeWidth: 1.8 }}><circle cx="12" cy="12" r="9" /><path d="M8.5 14a4 4 0 0 0 7 0M9 9.5h.01M15 9.5h.01" strokeLinecap="round" /></svg>
          <span className="flex-1 text-[15px] text-[#8696A0]">Message</span>
          <svg viewBox="0 0 24 24" className="h-5 w-5" style={{ fill: 'none', stroke: '#8696A0', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }}><path d="M21.4 11.6 12.5 20.5a5.5 5.5 0 0 1-7.8-7.8l8.5-8.5a3.7 3.7 0 0 1 5.2 5.2l-8.5 8.5a1.8 1.8 0 0 1-2.6-2.6l7.9-7.9" /></svg>
        </div>
        <div className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-full" style={{ background: '#00A884' }}>
          <svg viewBox="0 0 24 24" className="h-5 w-5" style={{ fill: '#fff' }}><path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z" /><path d="M19 11a7 7 0 0 1-14 0M12 18v3" style={{ fill: 'none', stroke: '#fff', strokeWidth: 2, strokeLinecap: 'round' }} /></svg>
        </div>
      </div>
    </div>
  )
}
