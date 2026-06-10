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

export { API_BASE, MOCK }
