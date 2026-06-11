import { useState } from 'react'
import { claimProfile, useDemo } from '../identity.js'
import { connectAccount, runOnboarding, setNotifyChannel } from '../cards.js'

// First-run gate. Step 1: claim a profile (or explore the demo). Step 2: connect
// Google so Donna can backfill the calendar + key relationships on day one.
// Sets identity in localStorage, then calls onDone().
export default function Onboarding({ onDone }) {
  const [step, setStep] = useState('profile') // profile | connect
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')

  function claim(e) {
    e.preventDefault()
    if (!name.trim()) return
    claimProfile(name.trim(), email.trim() || null)
    setStep('connect') // identity is set; let them connect before entering the app
  }

  function demo() {
    useDemo()
    onDone()
  }

  if (step === 'connect') return <ConnectStep name={name} onDone={onDone} />

  return (
    <div className="flex h-full flex-col justify-center px-8 pb-16 pt-14">
      <div className="reveal">
        <div className="grid h-16 w-16 place-items-center rounded-3xl bg-rust text-2xl font-semibold lowercase text-white shadow-bubble">
          d
        </div>
        <h1 className="mt-7 font-serif text-[40px] leading-[1.05] lowercase text-ink">
          hi, i'm donna.
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed lowercase text-soft">
          your thinking partner. i remember what matters and form a view of your
          life over time. what should i call you?
        </p>
      </div>

      <form onSubmit={claim} className="reveal mt-9 space-y-4" style={{ animationDelay: '120ms' }}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="your name"
          autoFocus
          className="w-full border-b border-line bg-transparent pb-2 text-[18px] text-ink placeholder:text-soft/50 focus:border-rust/40 focus:outline-none"
        />
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email (optional)"
          type="email"
          className="w-full border-b border-line bg-transparent pb-2 text-[16px] text-ink placeholder:text-soft/50 focus:border-rust/40 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!name.trim()}
          className="mt-3 w-full rounded-full bg-rust py-3 text-[15px] lowercase text-white transition disabled:opacity-40"
        >
          start with donna
        </button>
      </form>

      <button
        onClick={demo}
        className="reveal mt-8 text-center text-[13px] lowercase tracking-wide text-soft underline-offset-4 hover:text-ink hover:underline"
        style={{ animationDelay: '240ms' }}
      >
        just exploring? see the demo
      </button>
    </div>
  )
}

const CHANNELS = [
  { key: 'auto', label: 'Either' },
  { key: 'app', label: 'App' },
  { key: 'whatsapp', label: 'WhatsApp' },
]

function ConnectStep({ name, onDone }) {
  const [state, setState] = useState('idle') // idle | connecting | connected | running
  const [channel, setChannel] = useState('auto')

  async function connect() {
    setState('connecting')
    try {
      const res = await connectAccount('googlecalendar')
      if (res?.url) window.open(res.url, '_blank', 'noopener')
      setState('connected')
    } catch {
      setState('idle')
    }
  }

  async function finish(backfill) {
    setState('running')
    try {
      await setNotifyChannel(channel)
    } catch {
      /* non-fatal */
    }
    try {
      if (backfill) await runOnboarding()
    } catch {
      /* backfill also runs server-side on the connect webhook — non-fatal */
    }
    onDone()
  }

  const connected = state === 'connected' || state === 'running'

  return (
    <div className="flex h-full flex-col justify-center px-8 pb-16 pt-14">
      <div className="reveal">
        <h1 className="font-serif text-[34px] leading-[1.08] lowercase text-ink">
          {name ? `nice to meet you, ${name.trim().toLowerCase()}.` : 'one more thing.'}
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed lowercase text-soft">
          connect your google so i can see your calendar and notice what matters.
          i only read — i never send or delete anything without you.
        </p>
      </div>

      <div className="reveal mt-9" style={{ animationDelay: '120ms' }}>
        {!connected ? (
          <button
            onClick={connect}
            disabled={state === 'connecting'}
            className="w-full rounded-full bg-rust py-3 text-[15px] lowercase text-white transition disabled:opacity-50"
          >
            {state === 'connecting' ? 'opening…' : 'connect google'}
          </button>
        ) : (
          <button
            onClick={() => finish(true)}
            disabled={state === 'running'}
            className="w-full rounded-full bg-rust py-3 text-[15px] lowercase text-white transition disabled:opacity-50"
          >
            {state === 'running' ? 'reading your calendar…' : "i've connected"}
          </button>
        )}
      </div>

      {/* how should she reach you */}
      <div className="reveal mt-7" style={{ animationDelay: '200ms' }}>
        <div className="label mb-2.5">reach me on</div>
        <div className="flex gap-2">
          {CHANNELS.map((c) => (
            <button
              key={c.key}
              type="button"
              onClick={() => setChannel(c.key)}
              className={`flex-1 rounded-full border py-2 text-[13.5px] transition ${
                channel === c.key ? 'border-rust bg-rust/10 font-semibold text-rust' : 'border-line text-soft'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => finish(false)}
        className="reveal mt-8 text-center text-[13px] lowercase tracking-wide text-soft underline-offset-4 hover:text-ink hover:underline"
        style={{ animationDelay: '240ms' }}
      >
        skip for now
      </button>
    </div>
  )
}
