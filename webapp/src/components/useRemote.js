import { useEffect, useState } from 'react'

// Render the fallback (bundled fixture) instantly, then swap to live backend
// data when it arrives. If the backend is down, the fixture stays — the demo
// keeps working offline, but is driven by the real cognition layer when up.
export default function useRemote(fetcher, fallback) {
  const [data, setData] = useState(fallback)
  useEffect(() => {
    let alive = true
    fetcher()
      .then((d) => {
        if (!alive || d == null || d.empty) return
        if (Array.isArray(d) && d.length === 0) return
        setData(d)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return data
}
