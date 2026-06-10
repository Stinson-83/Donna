// Single source of "who is using the app". One id flows through chat AND the
// cognition screens (beliefs/plan/memory), so everything is one person's mind.
//
// Modes:
//   demo  → the seeded showcase user (rich fixture data, great first impression)
//   user  → a claimed profile (a stable per-person id; their data builds over time)
//
// This is lightweight, client-owned identity (good for beta / single-user). Real
// secure auth (Clerk + backend JWT verification) is the Tier-2 upgrade and slots
// in by having claimProfile() come from the auth provider instead of localStorage.

const KEY = 'donna_identity'
const DEMO_ID = import.meta.env.VITE_COG_USER || 'demo-aarav'

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

export function hasIdentity() {
  return !!read()
}

export function getIdentity() {
  return read()
}

export function getUserId() {
  return read()?.id || DEMO_ID
}

export function getName() {
  return read()?.name || null
}

export function isDemo() {
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
  write({ id: DEMO_ID, name: 'aarav', mode: 'demo' })
}

export function signOut() {
  localStorage.removeItem(KEY)
}
