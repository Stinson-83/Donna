// Cards + watches API client. Mirrors api.js conventions: API_BASE, the `?user=`
// param, and a MOCK fallback so `npm run dev` shows the surface with no backend.
import { MOCK, apiGet, apiPost } from './api.js'
import { getUserId } from './identity.js'
import { activeFixture } from './demo/store.js'

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
  const f = activeFixture()
  if (f) return { cards: f.cards ?? [] }
  if (MOCK) return { cards: MOCK_CARDS }
  return apiGet('/cards')
}

export async function actCard(cardId, actionId, user = getUserId()) {
  if (MOCK) {
    return { status: 'ok', cards: MOCK_CARDS.filter((c) => c.card_id !== cardId) }
  }
  return apiPost('/cards/action', { user, card_id: cardId, action_id: actionId })
}

export async function getWatches(user = getUserId()) {
  const f = activeFixture()
  if (f) return { watching: f.watching ?? [] }
  if (MOCK) return { watching: MOCK_WATCHES }
  return apiGet('/watches')
}

// The Dynamic Watch Bar — one ranked "what matters now" across cards/watches/tasks.
const MOCK_WATCHBAR = [
  { kind: 'card', ref_id: 'c_aws', title: 'HDFC · auto-pay', note: 'needs you', priority: 96, tier: 'critical' },
  { kind: 'watch', ref_id: 'w1', title: 'sequoia partner reply', note: 'reply', priority: 90, tier: 'critical' },
  { kind: 'task', ref_id: 't1', title: 'renew passport', note: 'due tomorrow', priority: 78, tier: 'high' },
  { kind: 'watch', ref_id: 'w2', title: 'tokyo flights below ₹38k', note: 'web', priority: 62, tier: 'medium' },
  { kind: 'task', ref_id: 't2', title: "rsvp to priya's wedding", note: 'due in 4d', priority: 55, tier: 'medium' },
]

export async function getWatchbar(user = getUserId()) {
  const f = activeFixture()
  if (f) return { items: f.watchbar ?? [] }
  if (MOCK) return { items: MOCK_WATCHBAR }
  return apiGet('/watchbar')
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
  const f = activeFixture()
  if (f) return f.today ?? MOCK_TODAY
  if (MOCK) return MOCK_TODAY
  return apiGet('/today')
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
  return apiGet('/history')
}

export async function runOnboarding(user = getUserId()) {
  if (MOCK) return { status: 'complete', events: 0, relationships: 0 }
  return apiPost('/onboarding/run', { user })
}

// Start an OAuth connection (real Composio). Returns { url } to open; on
// completion the backend webhook auto-runs the backfill.
export async function connectAccount(provider = 'googlecalendar', user = getUserId()) {
  if (MOCK) return { ok: true, url: null, provider, mock: true }
  return apiPost('/onboarding/connect', { user, provider })
}

export async function getOnboardingStatus(user = getUserId()) {
  if (MOCK) return { complete: true, relationships: 3, calendar_events: 6 }
  return apiGet('/onboarding/status')
}

// Library drawer counts: people, documents, trackers, todos, connected.
export async function getLibrary(user = getUserId()) {
  const f = activeFixture()
  if (f?.library) return f.library
  if (MOCK) return { people: 31, documents: 38, trackers: 7, todos: 5, connected: 3 }
  return apiGet('/library')
}

// To-dos detail (admin tasks + open commitments), deadlined first.
const MOCK_TODOS = [
  { id: 'td1', content: 'renew passport', category: 'renewal', due: 'due in 3d', overdue: false },
  { id: 'td2', content: "rsvp to priya's wedding", category: 'rsvp', due: 'due tomorrow', overdue: false },
  { id: 'td3', content: 'reply to the landlord about the lease', category: null, due: null, overdue: false },
]

export async function getTodos(user = getUserId()) {
  if (MOCK) return { todos: MOCK_TODOS }
  return apiGet('/library/todos')
}

export async function doneTodo(id, user = getUserId()) {
  if (MOCK) return { ok: true }
  return apiPost('/library/todos/done', { user, id })
}

// Trackers detail (active watches incl. cadence + flight state).
const MOCK_TRACKERS = [
  { id: 'tr1', type: 'flight', title: 'flight SQ516', subject: 'SQ516:2026-08-25', importance: 80, note: 'delayed', next_check: null },
  { id: 'tr2', type: 'reply', title: 'sequoia partner reply', subject: 'sequoia', importance: 90, note: null, next_check: null },
  { id: 'tr3', type: 'web', title: 'arsenal', subject: 'arsenal', importance: 45, note: '12 results seen', next_check: null },
]

export async function getTrackers(user = getUserId()) {
  if (MOCK) return { trackers: MOCK_TRACKERS }
  return apiGet('/library/trackers')
}

export async function retireTracker(id, user = getUserId()) {
  if (MOCK) return { ok: true }
  return apiPost('/library/trackers/retire', { user, id })
}

// People detail (relationships from the living profile).
const MOCK_PEOPLE = [
  { name: 'Raghav', relation: 'co-founder', email: 'raghav@poke.dev', importance: 92, birthday: null, note: null },
  { name: 'Mom', relation: 'family', email: null, importance: 88, birthday: '06-20', note: 'likes lilies' },
  { name: 'A Partner', relation: null, email: 'partner@sequoia.com', importance: 80, birthday: null, note: 'prefers concise emails' },
]

export async function getPeople(user = getUserId()) {
  if (MOCK) return { people: MOCK_PEOPLE }
  return apiGet('/library/people')
}

// Documents detail.
const MOCK_DOCS = [
  { id: 'd1', filename: 'lease-agreement.pdf', mime: 'application/pdf', size: '240 KB', status: 'ready', source: 'whatsapp', added: 'yesterday' },
  { id: 'd2', filename: 'permit-balance.png', mime: 'image/png', size: '88 KB', status: 'ready', source: 'whatsapp', added: 'Aug 12' },
]

export async function getDocuments(user = getUserId()) {
  if (MOCK) return { documents: MOCK_DOCS }
  return apiGet('/library/documents')
}

// Connected accounts detail.
const MOCK_CONNECTED = [
  { provider: 'google', product: 'googlecalendar', status: 'connected', healthy: true, synced: 'today', error: null },
  { provider: 'google', product: 'gmail', status: 'connected', healthy: true, synced: 'today', error: null },
  { provider: 'composio', product: 'github', status: 'pending', healthy: false, synced: null, error: null },
]

export async function getConnected(user = getUserId()) {
  if (MOCK) return { connected: MOCK_CONNECTED }
  return apiGet('/library/connected')
}

// Which surface Donna reaches you on: 'auto' | 'app' | 'whatsapp'.
export async function getSettings(user = getUserId()) {
  if (MOCK) return { notify_channel: 'auto' }
  return apiGet('/settings')
}

export async function setNotifyChannel(channel, user = getUserId()) {
  if (MOCK) return { notify_channel: channel }
  return apiPost('/settings', { user, notify_channel: channel })
}
