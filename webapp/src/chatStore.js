// Persist the chat thread per identity. Pages remount when you switch tabs
// (each page replays its entrance animation), so ChatPage's local state would
// otherwise be wiped every time you leave Chat. We keep the thread in
// localStorage keyed by user id, so it survives navigation AND app restarts.
import { getUserId, isDemo } from './identity.js'
import { CHAT_HISTORY } from './data/mockData.js'

const key = (id) => `donna_chat_${id}`

export function loadThread() {
  const id = getUserId()
  try {
    const raw = localStorage.getItem(key(id))
    if (raw) return JSON.parse(raw)
  } catch {
    /* corrupt/full storage — fall through to the default */
  }
  // First open: the demo user seeds with the showcase thread; a real person
  // starts clean.
  return isDemo() ? CHAT_HISTORY : []
}

export function saveThread(messages) {
  try {
    localStorage.setItem(key(getUserId()), JSON.stringify(messages))
  } catch {
    /* ignore quota errors */
  }
}
