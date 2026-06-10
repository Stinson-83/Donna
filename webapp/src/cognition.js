// Cognition API client — the four screens read their data from here. The demo
// user 'demo-aarav' is the seeded cognitive model (run: python -m
// backend.cognition.seed). Each getter throws on failure so callers can fall
// back to the bundled fixture and keep working offline.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const USER = import.meta.env.VITE_COG_USER || 'demo-aarav'

async function get(path) {
  const res = await fetch(`${API_BASE}/cognition${path}?user=${encodeURIComponent(USER)}`)
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
