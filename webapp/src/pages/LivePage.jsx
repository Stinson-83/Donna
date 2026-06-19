import { useEffect, useRef, useState } from 'react'
import Bubble from '../components/Bubble.jsx'
import Card from '../components/Card.jsx'
import { streamChat } from '../api.js'
import { getUserId } from '../identity.js'
import { loadThread, saveThread } from '../chatStore.js'

// The Live tab (donna-design-spec/reference/live-tab-v6): Donna speaks in free
// prose (no bubble); the user is in rust bubbles; a working shimmer while she's
// thinking; a Talk button for the voice session. Wired to the real chat stream.
const PROSE_TYPES = new Set(['text', 'cta'])

// ── DEMO play mode timing — how long Donna "types" before a turn, and the beat
// after it. Proportional to message length so longer messages feel weightier.
function textLen(item) {
  if (item.type === 'text' || item.type === 'cta') return (item.text || '').length
  if (item.type === 'card') return 64
  return (item.statement || item.question || item.text || item.explanation || '').length + 38
}
const typeMs = (item) => Math.min(2100, 640 + textLen(item) * 15)
const tailMs = (item) => (item.type === 'card' ? 820 : 560)

// A voice-note waveform — deterministic bar heights (no randomness so renders are
// reproducible). Light bars on the rust user bubble.
export function Waveform({ bars = 30, color = 'rgba(255,255,255,0.78)' }) {
  return (
    <span className="flex items-center gap-[2px]">
      {Array.from({ length: bars }).map((_, i) => {
        const h = 3 + Math.round(9 * Math.abs(Math.sin(i * 1.3) * Math.cos(i * 0.5)))
        return <span key={i} style={{ width: 2, height: h, borderRadius: 1, background: color, opacity: 0.55 + (h / 24) }} />
      })}
    </span>
  )
}

export function PlayGlyph({ color = '#fff' }) {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 flex-shrink-0" style={{ fill: color }}>
      <path d="M8 5v14l11-7z" />
    </svg>
  )
}

function rich(text) {
  return String(text || '').split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith('**') && p.endsWith('**')
      ? <strong key={i} className="font-bold">{p.slice(2, -2)}</strong>
      : <span key={i}>{p}</span>,
  )
}

export default function LivePage({ seedThread = null, now = null, play = null } = {}) {
  const [messages, setMessages] = useState(() => (play ? [] : (seedThread ?? loadThread())))
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState(null)
  const [calling, setCalling] = useState(false)
  const userId = useRef(getUserId())
  const feedRef = useRef(null)

  useEffect(() => { if (!seedThread && !play) saveThread(messages) }, [messages, seedThread, play])

  // DEMO play mode: reveal `play` thread over time with a typing beat before each
  // Donna turn, so a recorder can film one continuous conversation. Signals
  // window.__demoPlay.done when finished (the capture script waits on it).
  useEffect(() => {
    if (!play) return
    let cancelled = false
    const timers = []
    const add = (delay, fn) => timers.push(setTimeout(() => { if (!cancelled) fn() }, delay))
    let at = 650 // preroll on the empty chat
    play.forEach((m) => {
      if (m.from === 'donna') {
        add(at, () => { setBusy(true); setStatus('thinking') })
        at += typeMs(m.item)
        add(at, () => { setBusy(false); setStatus(null); setMessages((cur) => [...cur, m]) })
        at += tailMs(m.item)
      } else {
        at += 760 // you read, then reply
        add(at, () => setMessages((cur) => [...cur, m]))
        at += 340
      }
    })
    at += 720 // hold on the last frame
    window.__demoPlay = { done: false, duration: at }
    add(at, () => { window.__demoPlay = { done: true, duration: at } })
    return () => { cancelled = true; timers.forEach(clearTimeout) }
  }, [play])
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, status])

  async function send(text) {
    if (!text.trim() || busy) return
    setMessages((m) => [...m, { from: 'user', item: { type: 'text', text } }])
    setBusy(true)
    setStatus('thinking')
    await streamChat(text, userId.current, {
      onStatus: (t) => setStatus(t),
      onBubble: (b) => setMessages((m) => [...m, { from: 'donna', item: b }]),
      onDone: () => { setBusy(false); setStatus(null) },
      onError: () => {
        setMessages((m) => [...m, { from: 'donna', item: { type: 'text', text: "hmm, can't reach my brain right now." } }])
        setBusy(false); setStatus(null)
      },
    })
  }

  return (
    <div className="relative flex h-full flex-col">
      {/* nav */}
      <div className="flex flex-shrink-0 items-center justify-between px-5 pb-3 pt-4">
        <h1 className="font-serif text-[28px] leading-none text-ink">Live</h1>
        <span className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-[12px] font-semibold text-soft">
          {now && <span className="tabular-nums text-faint">{now}</span>}
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: '#3D7A4E', boxShadow: '0 0 0 3px rgba(61,122,78,0.15)' }} />
          {busy ? status || 'thinking' : 'here'}
        </span>
      </div>

      {/* feed */}
      <div ref={feedRef} className="scroll flex-1 overflow-y-auto px-[18px] pb-4 pt-1">
        {messages.length === 0 && !busy && !play && (
          <p className="pt-8 text-[16.5px] leading-[1.62] text-soft">
            tell me what's on your mind. i'll remember the parts that matter.
          </p>
        )}

        {messages.map((m, i) => {
          const prevSame = i > 0 && messages[i - 1].from === m.from
          if (m.from === 'user') {
            const isVoice = m.item.type === 'voice'
            return (
              <div key={i} className="reveal mb-7 flex flex-col items-end">
                <div
                  className="max-w-[84%] rounded-[18px] rounded-br-[5px] px-[16px] py-[11px] text-[15.5px] font-medium leading-[1.5] text-white"
                  style={{ background: 'linear-gradient(180deg,#8A604E 0%,#7B5544 60%,#6C4A3A 100%)', boxShadow: '0 2px 6px rgba(101,68,53,0.28), inset 0 1px 0 rgba(255,255,255,0.2)' }}
                >
                  {isVoice ? (
                    <span className="flex items-center gap-2.5">
                      <PlayGlyph />
                      <Waveform />
                      <span className="text-[11px] tabular-nums text-white/80">{m.item.dur || '0:03'}</span>
                    </span>
                  ) : (
                    m.item.text || m.item.caption || ''
                  )}
                </div>
                {isVoice ? (
                  <div className="mt-1.5 mr-1 max-w-[80%] text-right text-[13px] italic leading-snug text-soft">“{m.item.text}”</div>
                ) : (
                  <div className="mt-1.5 mr-1 text-[11px] font-medium text-faint">Delivered</div>
                )}
              </div>
            )
          }
          const it = m.item || {}
          return (
            <div key={i} className="mb-7">
              {!prevSame && (
                <div className="mb-2 text-[11.5px] font-semibold text-faint">
                  <b className="font-bold text-accent">Donna</b>
                </div>
              )}
              {it.type === 'card' ? (
                <div className="reveal"><Card card={it.card} onAct={() => {}} /></div>
              ) : PROSE_TYPES.has(it.type) ? (
                <>
                  <p className="reveal text-[17.5px] font-medium leading-[1.55] tracking-[-0.004em] text-ink">{rich(it.text)}</p>
                  {it.type === 'cta' && Array.isArray(it.buttons) && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {it.buttons.map((b) => (
                        <button
                          key={b.id || b.title}
                          disabled={busy}
                          onClick={() => send(b.title)}
                          className="rounded-[13px] border border-line bg-surface px-3.5 py-2 text-[14px] font-bold text-accent transition active:translate-y-[1.5px] disabled:opacity-40"
                        >
                          {b.title}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                // rich cognition bubbles (memory/thread/pattern/etc.) reuse the existing renderer
                <Bubble item={it} from="donna" onQuickReply={send} />
              )}
            </div>
          )
        })}

        {busy && (
          <div className="mb-4 flex items-center gap-2.5">
            <div className="wd"><i /><i /><i /></div>
            <span className="working-text text-[13px] font-semibold">{status || 'thinking'}</span>
          </div>
        )}
      </div>

      {/* composer */}
      <Composer onSend={send} busy={busy} onTalk={() => setCalling(true)} />

      {calling && <VoiceSession onEnd={() => setCalling(false)} />}
    </div>
  )
}

function Composer({ onSend, busy, onTalk }) {
  const [text, setText] = useState('')
  function submit(e) {
    e.preventDefault()
    if (!text.trim()) return
    onSend(text.trim())
    setText('')
  }
  return (
    <form
      onSubmit={submit}
      className="flex flex-shrink-0 items-center gap-2.5 border-t px-4 pb-3 pt-2.5"
      style={{ borderColor: 'rgba(63,46,35,0.05)', background: 'rgba(248,243,236,0.82)' }}
    >
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Message"
        className="h-[47px] flex-1 rounded-[24px] border border-line bg-surface px-[17px] text-[15px] text-ink placeholder:text-faint focus:outline-none"
        style={{ boxShadow: '0 1px 2px rgba(63,42,30,0.05), inset 0 1px 0 #FFF' }}
      />
      <button
        type="button"
        onClick={onTalk}
        disabled={busy}
        className="flex h-[47px] flex-shrink-0 items-center gap-2 rounded-[24px] px-[18px] text-[14.5px] font-bold transition active:translate-y-[1.5px] disabled:opacity-50"
        style={{ background: 'radial-gradient(120% 150% at 25% 0%, #3C2D20 0%, #251D16 60%, #19120C 100%)', color: '#F3EBE1', boxShadow: '0 2px 6px rgba(32,22,14,0.3), inset 0 1px 0 rgba(255,255,255,0.12)' }}
      >
        Talk
      </button>
    </form>
  )
}

// Voice session — the espresso takeover. Voice (STT/TTS) isn't wired yet, so this
// is honest: it shows Donna's presence and invites typing, not a fake call.
function VoiceSession({ onEnd }) {
  return (
    <div
      className="absolute inset-0 z-50 flex flex-col items-center justify-center px-8 text-center"
      style={{ background: 'radial-gradient(120% 80% at 50% 0%, #38291C 0%, #251D16 48%, #150F0A 100%)', color: '#F3EBE1' }}
    >
      <div
        className="presence-form mb-9 h-[150px] w-[150px]"
        style={{
          background: 'linear-gradient(160deg, #F7EFE3 0%, #E2CDB8 55%, #C99A7E 130%)',
          borderRadius: '46% 54% 57% 43% / 49% 44% 56% 51%',
          boxShadow: '0 18px 50px rgba(0,0,0,0.4), inset 0 2px 6px rgba(255,255,255,0.6)',
          animation: 'presence-pulse 4.5s ease-in-out infinite',
        }}
      />
      <div className="text-[12px] font-bold uppercase tracking-[0.1em]" style={{ color: '#C99A7E' }}>coming soon</div>
      <p className="mt-3.5 max-w-[300px] text-[17px] leading-[1.55]" style={{ color: 'rgba(243,235,225,0.62)' }}>
        live voice is on the way. for now, talk to me by typing — i'm listening either way.
      </p>
      <button
        onClick={onEnd}
        className="mt-10 flex h-16 w-16 items-center justify-center rounded-full"
        style={{ background: 'linear-gradient(180deg,#C05A45,#A8462F)', boxShadow: '0 4px 14px rgba(168,70,47,0.45)' }}
        aria-label="end"
      >
        <svg viewBox="0 0 24 24" className="h-6 w-6" style={{ stroke: '#fff', fill: 'none', strokeWidth: 1.8, transform: 'rotate(135deg)' }}>
          <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.6A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8 10a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2z" />
        </svg>
      </button>
    </div>
  )
}
