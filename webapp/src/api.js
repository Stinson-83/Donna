import { mockChat } from './mock.js'

// Backend base URL. Set VITE_API_BASE in .env for prod (Railway URL).
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// Mock mode runs the UI with no backend at all. It is ON by default so a fresh
// `npm run dev` works immediately; set VITE_MOCK=0 in .env once the backend is
// up to talk to the real brain.
const MOCK = import.meta.env.VITE_MOCK !== '0'

/**
 * Send one user message to Donna.
 * @returns {Promise<{user_id: string, reply: Array<object>}>}
 *   reply bubbles are discriminated on `type`:
 *   text | cta | cta_url | list | image | audio | delay
 */
export async function sendChat(message, user) {
  if (MOCK) return mockChat(message, user)
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, user }),
  })
  if (!res.ok) throw new Error(`chat failed: ${res.status}`)
  return res.json()
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const clamp = (n, lo, hi) => Math.max(lo, Math.min(n, hi))

function parseSSE(chunk) {
  let event = 'message'
  let data = ''
  for (const line of chunk.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) data += line.slice(5).trim()
  }
  if (!data) return null
  try {
    return { event, data: JSON.parse(data) }
  } catch {
    return null
  }
}

/**
 * Stream one message to Donna over SSE. Bubbles arrive progressively, with a
 * live `status` line reflecting what she's actually doing.
 * @param {object} handlers { onStatus(text), onBubble(bubble), onDone(userId), onError(err) }
 */
export async function streamChat(message, user, handlers = {}) {
  const { onStatus, onBubble, onDone, onError } = handlers
  if (MOCK) return mockStream(message, user, handlers)

  let res
  try {
    res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, user }),
    })
  } catch (e) {
    onError?.(e)
    return
  }
  if (!res.ok || !res.body) {
    onError?.(new Error(`stream failed: ${res.status}`))
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  let userId = user
  let done = false
  const finish = () => {
    if (done) return
    done = true
    onDone?.(userId)
  }
  try {
    for (;;) {
      const { value, done: streamDone } = await reader.read()
      if (streamDone) break
      buf += decoder.decode(value, { stream: true })
      let i
      while ((i = buf.indexOf('\n\n')) !== -1) {
        const ev = parseSSE(buf.slice(0, i))
        buf = buf.slice(i + 2)
        if (!ev) continue
        if (ev.event === 'status') onStatus?.(ev.data.text)
        else if (ev.event === 'bubble') onBubble?.(ev.data)
        else if (ev.event === 'done') {
          userId = ev.data.user_id || userId
          finish()
        }
      }
    }
  } catch (e) {
    if (!done) onError?.(e)
    return
  }
  finish()
}

// Mock streaming so the no-backend demo exercises the same handler path.
async function mockStream(message, user, { onStatus, onBubble, onDone }) {
  onStatus?.('thinking')
  const data = await mockChat(message, user)
  await sleep(500)
  for (const b of data.reply || []) {
    if (b.type === 'delay') {
      await sleep(clamp((b.seconds || 1) * 1000, 400, 3000))
      continue
    }
    const txt = b.text || b.caption || ''
    await sleep(clamp(300 + txt.length * 12, 300, 1200))
    onBubble?.(b)
  }
  onDone?.(data.user_id || user)
}

export { API_BASE, MOCK }
