// Offline mock so the UI runs with NO backend, NO Anthropic key, NO Postgres.
// Returns the same { user_id, reply: [bubbles] } shape as the real /chat, so
// when you wire the backend you only flip VITE_MOCK=0 — nothing else changes.

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function scriptedReply(message) {
  const m = message.toLowerCase()

  if (/(antler|deck|pitch|yc|slide|market)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.9 },
      {
        type: 'memory',
        text: "before i answer, something stands out.\n\ni might be wrong, but this is the fourth time you've raised the market-size slide. my current read: it's not the slide — it's that the story underneath it isn't settled yet.",
      },
      { type: 'thread', chain: ['the deck', 'the story', 'investor confidence'] },
      { type: 'text', text: 'fix the story and the slide tends to stop bothering you. want to work the opening?' },
    ]
  }
  if (/(outreach|reach out|email|behind|avoid|procrastin|uncertain)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.9 },
      {
        type: 'pattern_notice',
        intro: '3 related events this week:',
        events: ['delayed outreach', 'rewrote the deck twice', 'postponed the investor email'],
        explanation: 'my best guess is uncertainty about positioning — though i don\'t have enough data to be sure.',
      },
      { type: 'text', text: 'name the positioning out loud and the rest tends to move. want to try it now?' },
    ]
  }
  if (/(sleep|tired|exhaust|stress|anxious|nervous|overwhelm)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.9 },
      {
        type: 'memory',
        text: 'current hypothesis: your sleep dropped before the stress did, so this reads more like the review than the workload.\n\ni might be wrong, though — the two move together, so the evidence is mixed.',
      },
      { type: 'thread', chain: ['sleep', 'stress', 'the review'] },
      {
        type: 'open_question',
        question: 'is the stress from the reviews, or from the lost sleep?',
        status: 'evidence supports both. leaning sleep, ~61%.',
      },
      { type: 'text', text: 'either way, protecting tonight helps. 11pm.' },
    ]
  }
  if (/(last time|you said|remember|before|3 weeks|recurring)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.8 },
      {
        type: 'memory',
        text: 'this feels familiar.\n\nbefore your last pitch you doubted the same slide, then led with the user story and it landed.',
      },
      {
        type: 'belief_update',
        statement: "you overprepare when you're uncertain",
        from: 82,
        to: 84,
        reason: 'this is the fourth deck rewrite before a review.',
      },
      { type: 'text', text: "trust the story. you've done this before." },
    ]
  }

  if (/(but |disagree|don't think|dont think|not the|it's fine|its fine|nah|no it)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.8 },
      {
        type: 'memory',
        text: "i hear you. but you've come back to the deck three times this week.\n\ni don't think it's the slide. i think the story underneath it isn't settled yet.",
      },
      { type: 'text', text: 'humor me — say the one sentence the whole deck is trying to prove.' },
    ]
  }

  if (/(spend|spent|money|cost|budget|expense)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.8 },
      { type: 'text', text: "about $240 this week. coffee's creeping up — $38 of it alone." },
      { type: 'text', text: 'want the breakdown or just the headline?' },
      {
        type: 'cta',
        text: 'pick one',
        buttons: [
          { id: 'b', title: 'breakdown' },
          { id: 'h', title: 'just headline' },
        ],
      },
    ]
  }
  if (/(forget|forgetting|pending|loose|loop|todo|owe)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.7 },
      { type: 'text', text: "three things open: reply to luca, the antler form (due fri), and you said you'd call your mom." },
      { type: 'text', text: 'the antler form is the only one with a deadline. start there?' },
    ]
  }
  if (/(nervous|anxious|scared|stress|panic|overwhelm|worried)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.9 },
      { type: 'text', text: 'yeah, the night before always feels like this. you were the same before the last pitch and it went fine.' },
      { type: 'text', text: "what's the part you're least sure about — the deck or the talking?" },
    ]
  }
  if (/(remind|remember to|ping me)/.test(m)) {
    return [
      { type: 'delay', seconds: 0.6 },
      { type: 'text', text: "done. i'll nudge you tomorrow morning." },
    ]
  }
  if (/^(hi|hey|hello|yo|sup)\b/.test(m)) {
    return [
      { type: 'delay', seconds: 0.5 },
      { type: 'text', text: "hey. what's on your mind?" },
    ]
  }
  return [
    { type: 'delay', seconds: 0.7 },
    { type: 'text', text: "noted." },
    { type: 'text', text: "heads up: i'm in demo mode right now (scripted). add an anthropic key + run the backend and this becomes the real me." },
  ]
}

export async function mockChat(message, user) {
  await sleep(220)
  return { user_id: user || 'mock-user', reply: scriptedReply(message) }
}
