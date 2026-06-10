import { useState } from 'react'
import Reveal from '../components/Reveal.jsx'
import CausalChain from '../components/CausalChain.jsx'
import Sparkline from '../components/Sparkline.jsx'
import { BELIEFS, OPEN_QUESTIONS, REVISIONS } from '../data/mockData.js'

function Field({ label, children }) {
  return (
    <div className="mt-4">
      <div className="label">{label}</div>
      <div className="mt-1.5 text-[14px] leading-relaxed lowercase text-ink/85">{children}</div>
    </div>
  )
}

function WhyIThinkThis({ b }) {
  return (
    <div className="mt-5 border-l border-line pl-5">
      <Field label="evidence">{b.evidence.join('   ·   ')}</Field>
      {b.counter && (
        <Field label="counter-evidence">
          <span className="text-soft">{b.counter.join('   ·   ')}</span>
        </Field>
      )}
      <Field label="confidence over time">
        <span className="tabular-nums">{b.history.join('%  →  ')}%</span>
      </Field>
      <Field label="last strengthened by">{b.strengthenedBy}</Field>
      <Field label="reasoning">
        <span className="font-serif text-[16px] text-ink">{b.reasoning}</span>
      </Field>
      {b.chain && <CausalChain label="why this matters" steps={b.chain} className="mt-5" />}
    </div>
  )
}

export default function BeliefsPage() {
  const [open, setOpen] = useState(null)

  return (
    <div className="scroll flex h-full flex-col overflow-y-auto">
      <div className="px-7 pb-28 pt-14">
        <Reveal delay={0}>
          <div className="label">what donna thinks is true</div>
          <h1 className="mt-3 font-serif text-[30px] leading-[1.1] lowercase text-ink">
            things donna currently believes
          </h1>
        </Reveal>

        <div className="mt-14">
          {BELIEFS.map((b, i) => {
            const isOpen = open === b.id
            return (
              <Reveal key={b.id} delay={120 + i * 100}>
                {i > 0 && <div className="hairline my-10" />}

                <div className="flex items-baseline gap-3">
                  <span className="font-serif text-[42px] leading-none tabular-nums text-ink">{b.confidence}%</span>
                  {b.up && b.delta && (
                    <span className="flex items-center gap-1.5 text-[12px] lowercase text-soft">
                      <span className="h-1 w-1 rounded-full" style={{ background: 'rgb(var(--rust))' }} />
                      {b.delta} · {b.strengthened}
                    </span>
                  )}
                </div>

                <Sparkline values={b.history} className="mt-2.5" />

                <p className="mt-3 font-serif text-[24px] leading-snug text-ink">{b.statement}</p>

                {/* belief → behavior */}
                <p className="mt-3 text-[14px] leading-snug lowercase text-ink/80">
                  <span style={{ color: 'rgb(var(--rust))' }}>→ </span>
                  {b.consequence}
                </p>

                <button
                  onClick={() => setOpen(isOpen ? null : b.id)}
                  className="mt-4 text-[12px] lowercase tracking-wide text-soft underline-offset-4 hover:text-ink hover:underline"
                >
                  {isOpen ? 'hide reasoning' : 'why i think this'}
                </button>

                {isOpen && (
                  <div className="fade-in">
                    <WhyIThinkThis b={b} />
                  </div>
                )}
              </Reveal>
            )
          })}
        </div>

        {/* things i'm still figuring out — beliefs not yet earned */}
        <Reveal delay={120}>
          <div className="hairline my-12" />
          <div className="label">where my evidence is split</div>
          <h2 className="mt-3 font-serif text-[24px] lowercase text-ink">things i'm still figuring out</h2>

          <div className="mt-8 space-y-10">
            {OPEN_QUESTIONS.map((q) => (
              <div key={q.id}>
                <span className="font-serif text-[34px] leading-none tabular-nums text-ink">{q.confidence}%</span>
                <p className="mt-2.5 font-serif text-[22px] leading-snug text-ink">{q.question}</p>
                <p className="mt-2.5 text-[13px] lowercase text-soft">{q.status}</p>
                {q.leaning && <p className="mt-1 text-[13px] lowercase text-soft/80">{q.leaning}</p>}
              </div>
            ))}
          </div>

          <p className="mt-9 text-[13px] lowercase leading-relaxed text-soft">
            when one of these resolves, it becomes a belief. when a belief stops holding, it comes back here.
          </p>
        </Reveal>

        {/* i changed my mind */}
        <Reveal delay={120}>
          <div className="hairline my-12" />
          <div className="label">how my mind has changed</div>
          <h2 className="mt-3 font-serif text-[24px] lowercase text-ink">i changed my mind</h2>

          <div className="mt-8 space-y-10">
            {REVISIONS.map((r) => (
              <div key={r.id}>
                <div className="label">i used to think</div>
                <p className="mt-1.5 text-[17px] lowercase text-soft">
                  {r.from.statement} · {r.from.conf}%
                </p>
                <div
                  className="my-2.5 ml-[2px] h-5 w-px origin-top"
                  style={{ background: 'rgb(var(--soft))', opacity: 0.45 }}
                />
                <div className="label">now</div>
                <p className="mt-1.5 font-serif text-[21px] leading-snug text-ink">
                  {r.to.statement} <span className="text-[15px] text-soft">· {r.to.conf}%</span>
                </p>
                <p className="mt-3 text-[13px] leading-relaxed lowercase text-soft">because {r.why}</p>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </div>
  )
}
