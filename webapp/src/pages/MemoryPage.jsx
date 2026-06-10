import Reveal from '../components/Reveal.jsx'
import MemoryConstellation from '../components/MemoryConstellation.jsx'
import useRemote from '../components/useRemote.js'
import { getMemory } from '../cognition.js'
import { isDemo } from '../identity.js'
import { MEMORY_RECENT, MEMORY_SECTIONS } from '../data/mockData.js'

function Confidence({ level }) {
  const n = level === 'high' ? 3 : level === 'medium' ? 2 : 1
  return (
    <span className="inline-flex items-center gap-1 align-middle">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-[5px] w-[5px] rounded-full"
          style={{ background: i < n ? 'rgb(var(--soft))' : 'rgb(var(--line))' }}
        />
      ))}
    </span>
  )
}

export default function MemoryPage() {
  const demo = isDemo()
  const recent = useRemote(getMemory, demo ? MEMORY_RECENT : [])
  const hasMemories = recent.length > 0

  return (
    <div className="scroll flex h-full flex-col overflow-y-auto">
      <div className="px-7 pb-28 pt-12">
        <Reveal delay={0}>
          <div className="label">what donna knows</div>
          <h1 className="mt-3 font-serif text-[34px] lowercase text-ink">memory</h1>
        </Reveal>

        {!demo && !hasMemories && (
          <p className="mt-6 text-[15px] leading-relaxed lowercase text-soft">
            nothing here yet. everything you tell me — chat, journal, a voice note —
            lands here as evidence. it's what my beliefs are built from.
          </p>
        )}

        {/* the constellation — the hero (only once there's something to map) */}
        {hasMemories && (
          <Reveal delay={150} className="fade-in mt-6">
            <MemoryConstellation />
          </Reveal>
        )}

        {/* recent memories — editorial, no boxes */}
        {hasMemories && (
        <Reveal delay={300} className="mt-10">
          <div className="label mb-6">recent</div>
          <div>
            {recent.map((m, i) => (
              <div key={m.id}>
                {i > 0 && <div className="hairline my-7" />}
                <p className="font-serif text-[20px] leading-snug text-ink">{m.summary}</p>
                <div className="mt-3 flex items-center gap-2.5 text-[11px] lowercase text-soft">
                  <Confidence level={m.confidence} />
                  <span>·</span>
                  <span>{m.when}</span>
                  <span>·</span>
                  <span>via {m.source.toLowerCase()}</span>
                </div>
                {m.supports?.length > 0 && (
                  <div className="mt-3">
                    <span className="label">supports</span>
                    <div className="mt-1 text-[13px] lowercase leading-snug text-ink/80">
                      {m.supports.join('   ·   ')}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Reveal>
        )}

        {/* areas — a quiet index (demo only; the real index builds with use) */}
        {demo && (
        <Reveal delay={420} className="mt-14">
          <div className="label mb-5">areas</div>
          <div>
            {MEMORY_SECTIONS.map((s, i) => (
              <div key={s.key}>
                {i > 0 && <div className="hairline" />}
                <div className="py-3.5">
                  <div className="flex items-baseline justify-between">
                    <span className="text-[16px] lowercase text-ink">{s.title}</span>
                    <span className="text-[11px] tabular-nums text-soft">{s.count}</span>
                  </div>
                  <p className="mt-0.5 text-[13px] leading-snug lowercase text-soft">{s.summary}</p>
                </div>
              </div>
            ))}
          </div>
        </Reveal>
        )}
      </div>
    </div>
  )
}
