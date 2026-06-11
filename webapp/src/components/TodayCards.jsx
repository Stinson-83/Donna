import { useEffect, useState } from 'react'
import Card from './Card.jsx'
import { actCard, getCards, getWatches } from '../cards.js'

// The actionable surface on Plan: the cards Donna needs you on right now, plus
// the 'watching' list. Taps resolve through the backend and refetch.
export default function TodayCards() {
  const [cards, setCards] = useState(null)
  const [watching, setWatching] = useState([])
  const [acting, setActing] = useState(null)

  async function load() {
    try {
      const [cs, ws] = await Promise.all([getCards(), getWatches()])
      setCards(cs.cards || [])
      setWatching(ws.watching || [])
    } catch {
      setCards([]) // fail soft — the rest of Plan still renders
    }
  }
  useEffect(() => { load() }, [])

  async function onAct(cardId, actionId) {
    setActing(cardId)
    try {
      const res = await actCard(cardId, actionId)
      if (Array.isArray(res.cards)) setCards(res.cards)
      else setCards((cs) => (cs || []).filter((c) => c.card_id !== cardId))
    } catch {
      /* leave the card; a toast would go here */
    } finally {
      setActing(null)
    }
  }

  if (cards == null) return null
  if (cards.length === 0 && watching.length === 0) return null

  return (
    <div className="px-7 pt-14">
      {cards.length > 0 && (
        <div className="space-y-4">
          <div className="label">for you now</div>
          {cards.map((card) => (
            <Card
              key={card.card_id}
              card={card}
              acting={acting === card.card_id}
              onAct={(actionId) => onAct(card.card_id, actionId)}
            />
          ))}
        </div>
      )}

      {watching.length > 0 && (
        <div className="mt-9">
          <div className="label mb-3">she's watching · {watching.length}</div>
          <div className="space-y-2.5">
            {watching.map((w) => (
              <div key={w.id} className="flex items-baseline justify-between">
                <span className="flex items-center gap-2.5 text-[15px] lowercase text-ink">
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: w.type === 'reply' ? 'rgb(var(--rust))' : 'rgb(var(--soft))' }}
                  />
                  {w.title}
                </span>
                <span className="text-[11px] lowercase text-soft">{w.type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
