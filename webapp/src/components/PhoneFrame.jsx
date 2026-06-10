import MemoryThreads from './MemoryThreads.jsx'

// Device frame on desktop, full-bleed on mobile. Carries the theme class and a
// faint, ever-present layer of memory threads so Donna's signature is felt on
// every screen.
export default function PhoneFrame({ night, children }) {
  return (
    <div className={`${night ? 'night' : ''} flex min-h-screen items-center justify-center p-0 sm:p-6`}>
      <div className="relative flex h-screen w-full flex-col overflow-hidden bg-bg sm:h-[800px] sm:w-[390px] sm:rounded-[46px] sm:border-[11px] sm:border-ink/90 sm:shadow-[0_40px_90px_-30px_rgba(25,24,22,0.5)]">
        <div className="absolute left-1/2 top-0 z-30 hidden h-6 w-32 -translate-x-1/2 rounded-b-2xl bg-ink/90 sm:block" />
        <MemoryThreads className="absolute inset-0 z-0 h-full w-full" opacity={0.1} />
        <div className="relative z-10 flex flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  )
}
