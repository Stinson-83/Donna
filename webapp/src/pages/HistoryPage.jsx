import { useEffect, useRef, useState } from 'react'
import { getHistory } from '../cards.js'

// History (donna-design-spec/reference/history-v3): the cross-surface message
// stream — rust = in app, WhatsApp green = WhatsApp. Backed by ChatMessage.
function rich(text) {
  return String(text || '').split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i} className="font-bold">{p.slice(2, -2)}</strong>
      : <span key={i}>{p}</span>,
  )
}

function Meta({ m }) {
  return (
    <div className="mt-1 px-1 text-[10.5px] font-medium text-faint">
      {m.time} · {m.surface === 'whatsapp' ? 'WhatsApp' : 'In app'}
    </div>
  )
}

function Row({ m }) {
  const wa = m.surface === 'whatsapp'
  if (m.from === 'user') {
    const bg = wa
      ? 'linear-gradient(180deg,#3E7E53,#2F6B45 65%,#27573A)'
      : 'linear-gradient(180deg,#8A604E,#7B5544 60%,#6C4A3A)'
    return (
      <div className="mb-3.5 flex flex-col items-end">
        <div className="max-w-[80%] rounded-[18px] rounded-br-[5px] px-[14px] py-2.5 text-[14.5px] leading-[1.5] text-white" style={{ background: bg }}>
          {m.text}
        </div>
        <Meta m={m} />
      </div>
    )
  }
  return (
    <div className="mb-3.5 flex flex-col items-start">
      <div
        className="max-w-[88%] rounded-[16px] rounded-bl-[5px] border px-[14px] py-2.5 text-[14.5px] leading-[1.52] text-ink"
        style={{ background: wa ? '#EFF4ED' : 'rgb(var(--surface))', borderColor: wa ? 'rgba(47,107,69,0.16)' : 'rgb(var(--line))' }}
      >
        {rich(m.text)}
      </div>
      <Meta m={m} />
    </div>
  )
}

export default function HistoryPage() {
  const [messages, setMessages] = useState([])
  const [ready, setReady] = useState(false)
  const feedRef = useRef(null)

  useEffect(() => {
    getHistory()
      .then((d) => setMessages(d.messages || []))
      .catch(() => {})
      .finally(() => setReady(true))
  }, [])

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight })
  }, [messages])

  return (
    <div className="flex h-full flex-col">
      {/* nav + legend */}
      <div className="flex flex-shrink-0 items-center justify-between px-5 pb-3 pt-4">
        <h1 className="font-serif text-[28px] leading-none text-ink">History</h1>
        <div className="flex items-center gap-3 text-[10.5px] font-semibold text-faint">
          <span className="flex items-center gap-1.5">
            <i className="h-1.5 w-1.5 rounded-full" style={{ background: 'rgb(var(--accent))' }} />App
          </span>
          <span className="flex items-center gap-1.5">
            <i className="h-1.5 w-1.5 rounded-full" style={{ background: '#2F6B45' }} />WhatsApp
          </span>
        </div>
      </div>

      <div ref={feedRef} className="scroll flex-1 overflow-y-auto px-[18px] pb-28 pt-2">
        {ready && messages.length === 0 && (
          <p className="pt-10 text-[15px] leading-relaxed lowercase text-soft">
            no history yet. your conversations across whatsapp and the app will collect here.
          </p>
        )}
        {messages.map((m, i) => {
          const showDay = i === 0 || messages[i - 1].date !== m.date
          return (
            <div key={i}>
              {showDay && m.date && (
                <div className="my-5 flex justify-center">
                  <span className="rounded-[13px] border border-line bg-white/60 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-soft">
                    {m.date}
                  </span>
                </div>
              )}
              <Row m={m} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
