import { useEffect, useRef, useState } from 'react'
import Bubble from '../components/Bubble.jsx'
import TypingDots from '../components/TypingDots.jsx'
import Composer from '../components/Composer.jsx'
import { sendChat } from '../api.js'
import { CHAT_HISTORY } from '../data/mockData.js'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const clamp = (n, lo, hi) => Math.max(lo, Math.min(n, hi))

function getUserId() {
  let id = localStorage.getItem('donna_user')
  if (!id) {
    id = 'demo-' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem('donna_user', id)
  }
  return id
}

const FOLLOWUPS = ['why does it feel flat', 'what did i say last time']

export default function ChatPage() {
  const [messages, setMessages] = useState(CHAT_HISTORY)
  const [typing, setTyping] = useState(false)
  const [busy, setBusy] = useState(false)
  const userId = useRef(getUserId())
  const threadRef = useRef(null)

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, typing])

  async function handleSend(text) {
    if (!text.trim() || busy) return
    setMessages((m) => [...m, { from: 'user', item: { type: 'text', text } }])
    setBusy(true)
    setTyping(true)
    try {
      const data = await sendChat(text, userId.current)
      for (const b of data.reply || []) {
        if (b.type === 'delay') {
          await sleep(clamp((b.seconds || 1) * 1000, 400, 4000))
          continue
        }
        const txt = b.text || b.caption || ''
        await sleep(clamp(400 + txt.length * 13, 400, 1200))
        setMessages((m) => [...m, { from: 'donna', item: b }])
      }
    } catch {
      setMessages((m) => [
        ...m,
        { from: 'donna', item: { type: 'text', text: "hmm, can't reach my brain right now." } },
      ])
    } finally {
      setTyping(false)
      setBusy(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* header */}
      <div className="px-7 pb-4 pt-12">
        <div className="font-serif text-[26px] lowercase text-ink">donna</div>
        <div className="label mt-1">{typing ? 'thinking…' : 'here'}</div>
      </div>

      {/* thread */}
      <div ref={threadRef} className="scroll flex-1 space-y-5 overflow-y-auto px-7 py-3">
        {messages.map((m, i) => (
          <div key={i}>
            <Bubble item={m.item} from={m.from} onQuickReply={handleSend} />
            {m.source && (
              <div className="mt-1 text-[10px] lowercase tracking-wide text-soft/70">
                {m.source.toLowerCase()}
              </div>
            )}
          </div>
        ))}
        {typing && <TypingDots />}

        {!busy && (
          <div className="flex flex-wrap gap-x-6 gap-y-2 pt-2">
            {FOLLOWUPS.map((f) => (
              <button
                key={f}
                onClick={() => handleSend(f)}
                className="text-[14px] lowercase text-soft underline-offset-4 transition hover:text-ink hover:underline"
              >
                {f}
              </button>
            ))}
          </div>
        )}
      </div>

      <Composer onSend={handleSend} disabled={busy} />
    </div>
  )
}
