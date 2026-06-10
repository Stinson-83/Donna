import { useState } from 'react'
import { postJournal, postVoice } from '../cognition.js'

// A quiet sheet for leaving a thought with Donna — journal / quick note / voice
// transcript. It writes straight into the cognition layer (same model the
// Beliefs / Memory / Plan screens read), then gets out of the way.
const COPY = {
  journal: { title: 'a journal entry', hint: 'what happened, how it sat with you', send: postJournal },
  capture: { title: 'something quick', hint: 'a thought before it slips', send: postJournal },
  voice: { title: 'a voice note', hint: 'speak, then drop the transcript here', send: postVoice },
}

export default function Capture({ kind, onClose }) {
  const meta = COPY[kind] || COPY.capture
  const [text, setText] = useState('')
  const [state, setState] = useState('idle') // idle | saving | done

  async function save() {
    const body = text.trim()
    if (!body || state === 'saving') return
    setState('saving')
    try {
      await meta.send(body)
      setState('done')
      setTimeout(onClose, 900)
    } catch {
      setState('idle') // let them retry; the thought stays in the box
    }
  }

  return (
    <div className="absolute inset-0 z-40 flex flex-col justify-end bg-ink/20 backdrop-blur-sm" onClick={onClose}>
      <div
        className="reveal rounded-t-3xl border-t border-line bg-surface px-7 pb-9 pt-7"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mx-auto mb-5 h-1 w-9 rounded-full" style={{ background: 'rgb(var(--line))' }} />

        {state === 'done' ? (
          <p className="py-8 text-center font-serif text-[22px] lowercase text-ink">noted. it's part of how i see you now.</p>
        ) : (
          <>
            <div className="label">{meta.title}</div>
            <textarea
              autoFocus
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={meta.hint}
              rows={4}
              className="mt-3 w-full resize-none bg-transparent text-[17px] leading-relaxed lowercase text-ink placeholder:text-soft/50 focus:outline-none"
            />
            <div className="mt-4 flex items-center justify-between">
              <button onClick={onClose} className="text-[13px] lowercase text-soft hover:text-ink">
                not now
              </button>
              <button
                onClick={save}
                disabled={!text.trim() || state === 'saving'}
                className="rounded-full bg-rust px-5 py-2.5 text-[14px] lowercase text-white transition disabled:opacity-40"
              >
                {state === 'saving' ? 'saving…' : 'leave with donna'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
