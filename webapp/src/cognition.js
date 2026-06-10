// Cognition API client — the four screens read their data from here, keyed on
// the CURRENT identity (the same id chat uses), so chat + beliefs + memory are
// one person's mind. Each getter throws on failure so callers can fall back.
import { getUserId } from './identity.js'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function get(path) {
  const res = await fetch(`${API_BASE}/cognition${path}?user=${encodeURIComponent(getUserId())}`)
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json()
}

export const getPlan = () => get('/plan')
export const getBeliefs = () => get('/beliefs')
export const getBelief = (id) => get(`/beliefs/${id}`)
export const getBeliefHistory = () => get('/belief-history')
export const getQuestions = () => get('/questions')
export const getMemory = () => get('/memory')
export const getGraph = () => get('/graph')
export const getOpenLoops = () => get('/open-loops')

// writes — leaving a thought feeds the same model the screens read.
async function post(path, body) {
  const res = await fetch(`${API_BASE}/cognition${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user: getUserId(), ...body }),
  })
  if (!res.ok) throw new Error(`${path} → ${res.status}`)
  return res.json()
}

export const postJournal = (text) => post('/journal', { text })
export const postVoice = (text) => post('/voice', { text })
export const sendFeedback = (beliefId, signal) =>
  post('/feedback', { belief_id: beliefId, signal })
