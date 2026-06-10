import { useState } from 'react'
import { claimProfile, useDemo } from '../identity.js'

// First-run gate. Either claim a profile (your own evolving model) or explore
// the seeded demo. Sets identity in localStorage, then calls onDone().
export default function Onboarding({ onDone }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')

  function claim(e) {
    e.preventDefault()
    if (!name.trim()) return
    claimProfile(name.trim(), email.trim() || null)
    onDone()
  }

  function demo() {
    useDemo()
    onDone()
  }

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
