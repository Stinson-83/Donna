// Cards + watches API client. Mirrors api.js conventions: API_BASE, the `?user=`
// param, and a MOCK fallback so `npm run dev` shows the surface with no backend.
import { API_BASE, MOCK } from './api.js'
import { getUserId } from './identity.js'

// ── MOCK fixtures (same shape as the real endpoints) ─────────────────────
const MOCK_CARDS = [
  {
    version: 1,
    card_id: 'c_m2_sequoia',
    intent: 'heads_up',
    theme: 'dark',
    blocks: [
      { type: 'header', label: 'needs your eye', ref: 'Sequoia · term sheet' },
      { type: 'body', text: 'sequoia replied to your thread. they want an answer by **EOD**, and the term sheet expires **tomorrow noon**.' },
      { type: 'key_values', rows: [{ k: 'From', v: 'partner @ sequoia' }, { k: 'Thread', v: 'Series A term sheet' }] },
      { type: 'actions', actions: [
        { label: 'Draft a reply', action_id: 'a_draft_reply_sequoia', style: 'primary' },
        { label: 'Not now', action_id: 'a_dismiss', style: 'secondary' },
      ] },
      { type: 'footer', text: 'flagged from gmail · 8:42 AM', right: 'gmail' },
    ],
  },
  {
    version: 1,
    card_id: 'c_aws',
    intent: 'approval',
    theme: 'dark',
    blocks: [
      { type: 'header', label: 'needs your approval', ref: 'HDFC · auto-pay' },
      { type: 'body', text: 'aws **47,200** auto-debits in 4 days, your current is **4,200** short.' },
      { type: 'delta', from: '43,000', to: '48,000', from_caption: 'now', to_caption: 'after', kind: 'money' },
      { type: 'actions', actions: [
        { label: 'Transfer 5,000', action_id: 'a_transfer', style: 'primary' },
        { label: 'Not now', action_id: 'a_dismiss', style: 'secondary' },
      ] },
      { type: 'footer', text: "won't move anything until you tap" },
    ],
  },
  {
    version: 1,
    card_id: 'c_flight',
    intent: 'tracker',
    theme: 'light',
    blocks: [
      { type: 'header', label: 'tracking', ref: 'checked hourly' },
      { type: 'body', text: 'SIN → YYZ · one-way, Aug 28 · for the waterloo move' },
      { type: 'graph', points: [930, 921, 905, 896, 888, 871, 864, 851, 843, 836, 829, 818], target: 780, current_label: 'S$818', target_label: 'buy under S$780' },
      { type: 'footer', text: '30 days · dashed line is your target', right: "she'll buy when it crosses" },
    ],
  },
]

const MOCK_WATCHES = [
  { id: 'w1', type: 'reply', title: 'sequoia partner reply', subject: 'sequoia', importance: 90, deadline: null },
  { id: 'w2', type: 'web', title: 'tokyo flights below ₹38k', subject: 'tokyo flight prices', importance: 70, deadline: null },
  { id: 'w3', type: 'web', title: 'poke launch updates', subject: 'poke launch', importance: 50, deadline: null },
]

// ── API ──────────────────────────────────────────────────────────────────
export async function getCards(user = getUserId()) {
  if (MOCK) return { cards: MOCK_CARDS }
  const res = await fetch(`${API_BASE}/cards?user=${encodeURIComponent(user)}`)
  if (!res.ok) throw new Error(`cards failed: ${res.status}`)
  return res.json()
}

export async function actCard(cardId, actionId, user = getUserId()) {
  if (MOCK) {
    return { status: 'ok', cards: MOCK_CARDS.filter((c) => c.card_id !== cardId) }
  }
  const res = await fetch(`${API_BASE}/cards/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user, card_id: cardId, action_id: actionId }),
  })
  if (!res.ok) throw new Error(`card action failed: ${res.status}`)
  return res.json()
}

export async function getWatches(user = getUserId()) {
  if (MOCK) return { watching: MOCK_WATCHES }
  const res = await fetch(`${API_BASE}/watches?user=${encodeURIComponent(user)}`)
  if (!res.ok) throw new Error(`watches failed: ${res.status}`)
  return res.json()
}

const MOCK_TODAY = {
  date: 'Thu 11 Jun',
  holding: 23,
  calendar: [
    { time: '10:00', title: 'CS2040S grading', note: '' },
    { time: '3:00', title: 'Demo with Raghav', note: 'he confirmed at 2:30 · link ready' },
    { time: '8:45', title: 'Pickup · Aniroodh, Changi T3', note: 'pending your approval above' },
  ],
}

export async function getToday(user = getUserId()) {
  if (MOCK) return MOCK_TODAY
  const res = await fetch(`${API_BASE}/today?user=${encodeURIComponent(user)}`)
  if (!res.ok) throw new Error(`today failed: ${res.status}`)
  return res.json()
}

const MOCK_HISTORY = [
  { from: 'user', text: 'remind raghav about the demo at 3', surface: 'whatsapp', time: '7:42 AM', date: 'Thu 11 Jun', proactive: false },
  { from: 'donna', text: "done. i'll nudge him at 2:30 and tell you if he doesn't confirm.", surface: 'whatsapp', time: '7:42 AM', date: 'Thu 11 Jun', proactive: false },
  { from: 'donna', text: 'your **SQ516** landing moved to 9:40 PM. the pickup with aniroodh still says 6:30, so he\'d be waiting almost three hours.', surface: 'app', time: '8:42 AM', date: 'Thu 11 Jun', proactive: true },
  { from: 'user', text: 'move it and tell him', surface: 'app', time: '8:44 AM', date: 'Thu 11 Jun', proactive: false },
  { from: 'donna', text: 'balance is **S$31,240**, clears the requirement with room. filed a copy to your permit folder.', surface: 'whatsapp', time: '5:52 PM', date: 'Thu 11 Jun', proactive: false },
]

export async function getHistory(user = getUserId()) {
  if (MOCK) return { messages: MOCK_HISTORY }
  const res = await fetch(`${API_BASE}/history?user=${encodeURIComponent(user)}`)
  if (!res.ok) throw new Error(`history failed: ${res.status}`)
  return res.json()
}

export async function runOnboarding(user = getUserId()) {
  if (MOCK) return { status: 'complete', events: 0, relationships: 0 }
  const res = await fetch(`${API_BASE}/onboarding/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user }),
  })
  if (!res.ok) throw new Error(`onboarding failed: ${res.status}`)
  return res.json()
}

// Start an OAuth connection (real Composio). Returns { url } to open; on
// completion the backend webhook auto-runs the backfill.
export async function connectAccount(provider = 'googlecalendar', user = getUserId()) {
  if (MOCK) return { ok: true, url: null, provider, mock: true }
  const res = await fetch(`${API_BASE}/onboarding/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user, provider }),
  })
  if (!res.ok) throw new Error(`connect failed: ${res.status}`)
  return res.json()
}

export async function getOnboardingStatus(user = getUserId()) {
  if (MOCK) return { complete: true, relationships: 3, calendar_events: 6 }
  const res = await fetch(`${API_BASE}/onboarding/status?user=${encodeURIComponent(user)}`)
  if (!res.ok) throw new Error(`status failed: ${res.status}`)
  return res.json()
}

// Library drawer counts: people, documents, trackers, todos, connected.
export async function getLibrary(user = getUserId()) {
  if (MOCK) return { people: 31, documents: 38, trackers: 7, todos: 5, connected: 3 }
  const res = await fetch(`${API_BASE}/library?user=${encodeURIComponent(user)}`)
  if (!res.ok) throw new Error(`library failed: ${res.status}`)
  return res.json()
}

// Which surface Donna reaches you on: 'auto' | 'app' | 'whatsapp'.
export async function getSettings(user = getUserId()) {
  if (MOCK) return { notify_channel: 'auto' }
  const res = await fetch(`${API_BASE}/settings?user=${encodeURIComponent(user)}`)
  if (!res.ok) throw new Error(`settings failed: ${res.status}`)
  return res.json()
}

export async function setNotifyChannel(channel, user = getUserId()) {
  if (MOCK) return { notify_channel: channel }
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user, notify_channel: channel }),
  })
  if (!res.ok) throw new Error(`settings failed: ${res.status}`)
  return res.json()
}
