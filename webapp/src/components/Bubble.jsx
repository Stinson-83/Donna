import LivingThread from './LivingThread.jsx'

// Chat is a conversation with context — not an LLM textbox.
//  · user   → a quiet right-aligned pill
//  · donna  → bubble-less text, like a person speaking
//  · memory → Donna recalling in her own first-person voice, set off by a
//             faint thread, not a system label
//  · thread → a living memory thread surfacing inline

// Donna remembering, in her own voice. No "YOU MENTIONED THIS" stamp.
const MEMORY_TYPES = new Set(['memory', 'memory_ref', 'context', 'pattern', 'open_loop'])

function Memory({ text }) {
  return (
    <div className="reveal mr-auto flex max-w-[88%] gap-3.5 py-1">
      <span className="mt-1 w-px shrink-0 self-stretch" style={{ background: 'rgb(var(--rust))', opacity: 0.38 }} />
      <p className="whitespace-pre-line font-serif text-[18px] leading-relaxed text-ink">{text}</p>
    </div>
  )
}

export default function Bubble({ item, from, onQuickReply }) {
  const mine = from === 'user'

  if (item.type === 'thread') {
    return <LivingThread chain={item.chain} className="mr-auto py-1.5" />
  }

  if (MEMORY_TYPES.has(item.type)) {
    return <Memory text={item.text} />
  }

  // Donna observing — three related events and a synthesized explanation.
  if (item.type === 'pattern_notice') {
    return (
      <div className="reveal mr-auto flex max-w-[88%] gap-3.5 py-1">
        <span className="mt-1 w-px shrink-0 self-stretch" style={{ background: 'rgb(var(--rust))', opacity: 0.38 }} />
        <div>
          <div className="label">pattern noticed</div>
          <p className="mt-2.5 font-serif text-[17px] leading-snug text-ink">{item.intro}</p>
          <ul className="mt-2 space-y-1">
            {item.events.map((e, i) => (
              <li key={i} className="text-[14px] lowercase text-soft">— {e}</li>
            ))}
          </ul>
          <div className="mt-3.5 label">possible explanation</div>
          <p className="mt-1.5 font-serif text-[18px] leading-snug text-ink">{item.explanation}</p>
        </div>
      </div>
    )
  }

  // Donna holding a question open — unresolved, soft accent (not rust).
  if (item.type === 'open_question') {
    return (
      <div className="reveal mr-auto flex max-w-[88%] gap-3.5 py-1">
        <span className="mt-1 w-px shrink-0 self-stretch" style={{ background: 'rgb(var(--soft))', opacity: 0.45 }} />
        <div>
          <div className="label">still figuring out</div>
          <p className="mt-2.5 font-serif text-[18px] leading-snug text-ink">{item.question}</p>
          <p className="mt-2 text-[13px] lowercase text-soft">{item.status}</p>
        </div>
      </div>
    )
  }

  // Donna's model of you, changing in real time.
  if (item.type === 'belief_update') {
    return (
      <div className="reveal mr-auto flex max-w-[88%] gap-3.5 py-1">
        <span className="mt-1 w-px shrink-0 self-stretch" style={{ background: 'rgb(var(--rust))', opacity: 0.38 }} />
        <div>
          <div className="label">belief updated</div>
          <p className="mt-2.5 font-serif text-[18px] leading-snug text-ink">{item.statement}</p>
          <div className="mt-2 flex items-center gap-2 text-[15px] tabular-nums">
            <span className="text-soft">{item.from}%</span>
            <span className="text-soft">→</span>
            <span style={{ color: 'rgb(var(--rust))' }}>{item.to}%</span>
          </div>
          <p className="mt-2.5 text-[13px] lowercase text-soft">because {item.reason}</p>
        </div>
      </div>
    )
  }

  if (mine) {
    return (
      <div className="reveal ml-auto max-w-[78%] rounded-2xl rounded-br-md border border-line bg-surface px-4 py-2.5 text-[15px] leading-snug text-ink">
        {item.text}
      </div>
    )
  }

  if (item.type === 'text') {
    return (
      <p className="reveal mr-auto max-w-[84%] text-[16px] leading-relaxed text-ink">{item.text}</p>
    )
  }

  if (item.type === 'cta') {
    return (
      <div className="reveal mr-auto max-w-[84%]">
        <p className="text-[16px] leading-relaxed text-ink">{item.text}</p>
        <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-1.5">
          {item.buttons.map((b) => (
            <button
              key={b.id}
              onClick={() => onQuickReply(b.title)}
              className="text-[14px] lowercase text-soft underline-offset-4 transition hover:text-ink hover:underline"
            >
              {b.title}
            </button>
          ))}
        </div>
      </div>
    )
  }

  if (item.type === 'cta_url') {
    return (
      <div className="reveal mr-auto max-w-[84%]">
        <p className="text-[16px] leading-relaxed text-ink">{item.text}</p>
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="mt-1.5 inline-block text-[14px] lowercase underline underline-offset-4"
          style={{ color: 'rgb(var(--rust))' }}
        >
          {item.display_text}
        </a>
      </div>
    )
  }

  if (item.type === 'list') {
    return (
      <div className="reveal mr-auto max-w-[88%]">
        <p className="text-[16px] leading-relaxed text-ink">{item.text}</p>
        <div className="mt-2">
          {item.sections.flatMap((s) => s.rows).map((r, i) => (
            <div key={r.id}>
              {i > 0 && <div className="hairline" />}
              <button
                onClick={() => onQuickReply(r.title)}
                className="block w-full py-2.5 text-left text-[15px] lowercase text-ink/90 transition hover:text-ink"
              >
                {r.title}
              </button>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (item.type === 'image') {
    return (
      <div className="reveal mr-auto max-w-[80%]">
        <img src={item.url} alt={item.caption || ''} className="rounded-2xl" loading="lazy" />
        {item.caption && <p className="mt-1.5 text-[13px] lowercase text-soft">{item.caption}</p>}
      </div>
    )
  }

  if (item.type === 'audio') {
    return (
      <div className="reveal mr-auto max-w-[80%]">
        <audio controls src={item.url} className="w-full" />
      </div>
    )
  }

  return null
}
