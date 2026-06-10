import { useState } from 'react'

export default function Composer({ onSend, disabled }) {
  const [text, setText] = useState('')

  function submit(e) {
    e.preventDefault()
    const t = text.trim()
    if (!t || disabled) return
    onSend(t)
    setText('')
  }

  return (
    <form onSubmit={submit} className="flex items-center gap-3 px-5 py-3">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="tell donna…"
        className="flex-1 border-b border-line bg-transparent pb-1.5 text-[16px] text-ink placeholder:text-soft/60 focus:border-ink/30 focus:outline-none"
        autoComplete="off"
      />
      <button
        type="submit"
        disabled={disabled}
        aria-label="send"
        className="grid h-9 w-9 shrink-0 place-items-center rounded-full transition disabled:opacity-30"
        style={{ color: 'rgb(var(--rust))' }}
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
    </form>
  )
}
