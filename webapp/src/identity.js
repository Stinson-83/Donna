// Single source of "who is using the app". One id flows through chat AND the
// cognition screens (beliefs/plan/memory), so everything is one person's mind.
//
// Modes:
//   demo    → the seeded showcase user (rich fixture data, great first impression)
//   user    → a claimed profile (a stable per-person id; data builds over time)
//   session → authed via a magic link Donna sent in WhatsApp (a real backend
//             session token; the id is the server-resolved user_id)
//
// Auth: when the dashboard is opened from Donna's "open your dashboard" link, the
// magic token rides the URL fragment (#t=). bootstrapFromMagicLink() exchanges it
// for a session token (POST /auth/exchange) and stores it; authHeaders() then puts
// it on every request as `Authorization: Bearer`. The backend prefers the Bearer
// session and falls back to ?user= until require_auth is enabled.

const KEY = 'donna_identity'
const SESSION_KEY = 'donna_session'
const DEMO_ID = import.meta.env.VITE_COG_USER || 'demo-aarav'
// Read directly from env (not from api.js) so this module has no import cycle.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || 'null')
  } catch {
    return null
  }
}

function write(v) {
  localStorage.setItem(KEY, JSON.stringify(v))
}

// ── Session token (set by the magic-link exchange) ─────────────────────────

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null')
  } catch {
    return null
  }
}

export function getSessionToken() {
  return getSession()?.token || null
}

function setSession(s) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(s))
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY)
}

// Attach to every backend request: the Bearer session wins server-side; ?user=
// (added by api.js) stays as the back-compat fallback.
export function authHeaders() {
  const t = getSessionToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

// On load: if Donna's link left a magic token in the URL fragment, trade it for a
// session and strip it from the URL. No-op (returns the existing identity) when
// there's no token. Safe to await before render.
export async function bootstrapFromMagicLink() {
  const hash = window.location.hash || ''
  const m = hash.match(/[#&]t=([^&]+)/)
  if (!m) return getIdentity()
  const token = decodeURIComponent(m[1])
  // Strip the token from the URL bar / history immediately.
  try {
    history.replaceState(null, '', window.location.pathname + window.location.search)
  } catch {
    /* ignore */
  }
  try {
    const res = await fetch(`${API_BASE}/auth/exchange`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ magic: token }),
    })
    if (!res.ok) return getIdentity()
    const data = await res.json()
    setSession({ token: data.session_token, user_id: data.user_id, name: data.name || null })
    write({ id: data.user_id, name: data.name || 'you', mode: 'session', created: Date.now() })
  } catch {
    /* network failure — fall back to whatever identity exists */
  }
  return getIdentity()
}

// ── Identity ───────────────────────────────────────────────────────────────

export function hasIdentity() {
  return !!read() || !!getSession()
}

export function getIdentity() {
  return read()
}

export function getUserId() {
  // A live session's server-resolved id wins, then a claimed/demo identity.
  return getSession()?.user_id || read()?.id || DEMO_ID
}

export function getName() {
  return getSession()?.name || read()?.name || null
}

export function isDemo() {
  if (getSession()) return false
  const i = read()
  return !i || i.mode === 'demo'
}

function slugify(name) {
  const base = (name || 'you').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 18) || 'you'
  return `${base}-${Math.random().toString(36).slice(2, 7)}`
}

export function claimProfile(name, email) {
  const id = slugify(name)
  write({ id, name: name || 'you', email: email || null, mode: 'user', created: Date.now() })
  return id
}

export function useDemo() {
  clearSession()
  write({ id: DEMO_ID, name: 'aarav', mode: 'demo' })
}

export function signOut() {
  localStorage.removeItem(KEY)
  clearSession()
}
