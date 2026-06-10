import { useEffect, useRef, useState } from 'react'
import Bubble from '../components/Bubble.jsx'
import TypingDots from '../components/TypingDots.jsx'
import Composer from '../components/Composer.jsx'
import { streamChat } from '../api.js'
import { getUserId, isDemo } from '../identity.js'
import { CHAT_HISTORY } from '../data/mockData.js'

const FOLLOWUPS = ['why does it feel flat', 'what did i say last time']

export default function ChatPage() {
  // Demo user sees the showcase thread; a real person starts with a clean slate.
  const [messages, setMessages] = useState(isDemo() ? CHAT_HISTORY : [])
  const [typing, setTyping] = useState(false)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState(null) // live "what she's doing" line
  const userId = useRef(getUserId())
  const threadRef = useRef(null)

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, typing, status])

  async function handleSend(text) {
    if (!text.trim() || busy) return
    setMessages((m) => [...m, { from: 'user', item: { type: 'text', text } }])
    setBusy(true)
    setTyping(true)
    setStatus('thinking')
    await streamChat(text, userId.current, {
      onStatus: (t) => setStatus(t),
      onBubble: (b) => setMessages((m) => [...m, { from: 'donna', item: b }]),
      onDone: () => {
        setTyping(false)
        setBusy(false)
        setStatus(null)
      },
      onError: () => {
        setMessages((m) => [
          ...m,
          { from: 'donna', item: { type: 'text', text: "hmm, can't reach my brain right now." } },
        ])
        setTyping(false)
        setBusy(false)
        setStatus(null)
      },
    })
  }

  return (
    <div className="flex h-full flex-col">
      {/* header */}
      <div className="px-7 pb-4 pt-12">
        <div className="font-serif text-[26px] lowercase text-ink">donna</div>
        <div className="label mt-1">{typing ? `${status || 'thinking'}…` : 'here'}</div>
      </div>

      {/* thread */}
      <div ref={threadRef} className="scroll flex-1 space-y-5 overflow-y-auto px-7 py-3">
        {messages.length === 0 && !typing && (
          <p className="pt-6 font-serif text-[22px] leading-snug lowercase text-soft">
            tell me what's on your mind. i'll remember the parts that matter.
          </p>
        )}
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

        {!busy && messages.length > 0 && (
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
