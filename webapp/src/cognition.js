// Cognition API client — the four screens read their data from here, keyed on
// the CURRENT identity (the same id chat uses), so chat + beliefs + memory are
// one person's mind. Each getter throws on failure so callers can fall back.
import { getUserId } from './identity.js'
import { apiGet, apiPost } from './api.js'

async function get(path) {
  return apiGet(`/cognition${path}`)
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
  return apiPost(`/cognition${path}`, { user: getUserId(), ...body })
}

export const postJournal = (text) => post('/journal', { text })
export const postVoice = (text) => post('/voice', { text })
export const sendFeedback = (beliefId, signal) =>
  post('/feedback', { belief_id: beliefId, signal })
