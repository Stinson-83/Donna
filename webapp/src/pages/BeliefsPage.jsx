import Reveal from '../components/Reveal.jsx'
import CausalChain from '../components/CausalChain.jsx'
import { BELIEFS } from '../data/mockData.js'

export default function BeliefsPage() {
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
          {BELIEFS.map((b, i) => (
            <Reveal key={b.id} delay={120 + i * 110}>
              {i > 0 && <div className="hairline my-10" />}

              <div className="flex items-baseline gap-3">
                <span className="font-serif text-[42px] leading-none tabular-nums text-ink">
                  {b.confidence}%
                </span>
                {b.up && b.delta && (
                  <span className="flex items-center gap-1.5 text-[12px] lowercase text-soft">
                    <span className="h-1 w-1 rounded-full" style={{ background: 'rgb(var(--rust))' }} />
                    {b.delta} · {b.strengthened}
                  </span>
                )}
              </div>

              <p className="mt-3 font-serif text-[24px] leading-snug text-ink">{b.statement}</p>

              <p className="mt-4 text-[13px] lowercase leading-relaxed text-soft">
                based on&nbsp;&nbsp;{b.basis.join('   ·   ')}
              </p>

              <div className="mt-1.5 flex flex-wrap gap-x-6 text-[12px] lowercase text-soft/75">
                {b.related && <span>memories&nbsp;&nbsp;{b.related.join('  ·  ')}</span>}
                {!b.up && <span>last strengthened {b.strengthened}</span>}
              </div>

              {b.chain && <CausalChain label="why this matters" steps={b.chain} className="mt-6" />}
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  )
}
