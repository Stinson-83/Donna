import Reveal from '../components/Reveal.jsx'
import CausalChain from '../components/CausalChain.jsx'
import useRemote from '../components/useRemote.js'
import { getPlan } from '../cognition.js'
import { isDemo } from '../identity.js'
import { PLAN } from '../data/mockData.js'

export default function PlanPage() {
  // Demo user opens to a fully-formed day. A real person hasn't given Donna
  // enough yet — she says so plainly instead of faking a plan.
  const p = useRemote(getPlan, isDemo() ? PLAN : null)

  if (!p || !p.calendar?.length) {
    return (
      <div className="flex h-full flex-col justify-center px-7 pb-16">
        <div className="label">your day</div>
        <h1 className="mt-3 font-serif text-[32px] leading-[1.1] lowercase text-ink">
          i don't have a plan for you yet.
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed lowercase text-soft">
          tell me what's on your plate — a few messages or a journal entry — and
          i'll start shaping your days and noticing what matters.
        </p>
      </div>
    )
  }

  const peak = p.calendar.find((e) => e.tone === 'peak') || p.calendar[p.calendar.length - 1]

  return (
    <div className="scroll flex h-full flex-col overflow-y-auto">
      {/* ── First viewport: only date, thesis, the one thing ── */}
      <section className="flex min-h-full flex-col px-7 pb-10 pt-14">
        <Reveal delay={0}>
          <div className="label">{p.date}</div>
        </Reveal>

        {/* thesis — monumental, the headline of the day */}
        <Reveal delay={120} className="flex flex-1 flex-col justify-center py-8">
          <h1 className="font-serif text-[48px] leading-[1.02] tracking-tight text-ink">
            {p.thesis}
          </h1>
          <h1 className="mt-3 font-serif text-[48px] leading-[1.02] tracking-tight text-soft">
            {p.thesisCoda}
          </h1>
        </Reveal>

        {/* the one event that matters today — and why */}
        <Reveal delay={320}>
          <div className="flex items-baseline gap-3">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: 'rgb(var(--rust))' }} />
            <span className="label !tracking-[0.1em]">{peak.time}</span>
          </div>
          <div className="mt-1 font-serif text-[26px] lowercase text-ink">{peak.title}</div>
          <CausalChain label="because" steps={p.because} className="mt-6" />
        </Reveal>
      </section>

      {/* ── Below the fold ── */}
      <section className="px-7 pb-28">
        {/* how donna decided — she made a choice, not a list */}
        <Reveal delay={0}>
          <div className="label mb-4">how i chose today</div>
          <div className="text-[13px] lowercase text-soft">i considered</div>
          <ul className="mt-1.5 space-y-1">
            {p.decision.considered.map((c) => (
              <li key={c} className="text-[15px] lowercase text-ink/80">— {c}</li>
            ))}
          </ul>
          <div className="mt-4 text-[13px] lowercase text-soft">i chose</div>
          <p className="mt-1 font-serif text-[22px] lowercase text-ink">{p.decision.chose}</p>
          <p className="mt-2 text-[14px] leading-snug lowercase text-soft">because {p.decision.because}</p>
        </Reveal>

        <Reveal delay={0} className="mt-16">
          <div className="label mb-5">today's shape</div>
          <div className="space-y-7 border-l border-line pl-5">
            {p.calendar.map((e, i) => (
              <div key={i} className="relative">
                {e.tone === 'peak' && (
                  <span
                    className="absolute -left-[23px] top-2 h-1.5 w-1.5 rounded-full"
                    style={{ background: 'rgb(var(--rust))' }}
                  />
                )}
                <div className="label !tracking-[0.1em]">{e.time}</div>
                <div className={`mt-0.5 font-serif text-2xl lowercase ${e.tone === 'peak' ? 'text-ink' : 'text-ink/85'}`}>
                  {e.title}
                </div>
              </div>
            ))}
          </div>
        </Reveal>

        <div className="mt-16">
          <div className="label mb-4">open loops</div>
          {p.openLoops.map((l, i) => (
            <div key={l.id}>
              {i > 0 && <div className="hairline" />}
              <div className="flex items-baseline justify-between py-3.5">
                <span className="text-[17px] lowercase text-ink">{l.text}</span>
                <span className="text-[12px] lowercase text-soft">{l.meta}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-16">
          <p className="font-serif text-[22px] leading-snug text-ink/90">{p.nudge}</p>
          <p className="mt-2.5 text-[12px] lowercase tracking-wide text-soft">
            from a belief&nbsp;&nbsp;·&nbsp;&nbsp;{p.nudgeBelief}
          </p>
        </div>

        <p className="mt-20 font-serif text-[20px] italic leading-relaxed text-soft">{p.whisper}</p>
      </section>
    </div>
  )
}
