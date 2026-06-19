// Matt Wilson fixtures — NYC Goldman VP. The single source of every card in the
// 73-second cut (see DEMO_VIDEO_FINAL_DESIGN). Hardcoded on purpose. Throwaway.
//
// Cards use the real DonnaCard block vocabulary (components/Card.jsx).

export const card = {
  // S3 — the work-vs-family conflict, surfaced from gmail (dark, needs-eye)
  conflict: {
    version: 1, card_id: 'c_conflict', intent: 'heads_up', theme: 'dark',
    blocks: [
      { type: 'header', label: 'needs your eye', ref: 'conflict' },
      { type: 'body', text: '**goldman offsite** · dec 18-21 · aspen' },
      { type: 'body', text: "**emily's wedding** · dec 20+ · los angeles" },
      { type: 'key_values', rows: [
        { k: 'Overlap', v: 'dec 20, 21' },
        { k: 'Resolve', v: 'by tomorrow' },
      ] },
      { type: 'actions', actions: [
        { label: 'split it', action_id: 'a_split', style: 'primary' },
        { label: 'decide later', action_id: 'a_later', style: 'secondary' },
      ] },
      { type: 'footer', text: 'flagged from gmail', right: 'gmail' },
    ],
  },

  // dashboard — the Boka attention card (light, one CTA)
  boka: {
    version: 1, card_id: 'c_boka', intent: 'heads_up', theme: 'light',
    blocks: [
      { type: 'header', label: 'mom’s birthday', ref: 'in 8 days' },
      { type: 'body', text: 'boka has a **7:30 table** on the 28th. her favorite. should i book?' },
      { type: 'actions', actions: [{ label: 'book it', action_id: 'a_book', style: 'primary' }] },
      { type: 'footer', text: 'she’s been scouting this for weeks', right: 'opentable' },
    ],
  },

  // dashboard — a passive price tracker (light)
  chiTracker: {
    version: 1, card_id: 'c_chi', intent: 'tracker', theme: 'light',
    blocks: [
      { type: 'header', label: 'tracking', ref: 'checked hourly' },
      { type: 'body', text: 'EWR → ORD · thanksgiving · you wanted under **$200**' },
      { type: 'graph', points: [430, 418, 402, 389, 372, 356, 348, 332, 318, 305, 298, 290], target: 270, current_label: '$290', target_label: 'buy under $200' },
      { type: 'footer', text: '2 days left to decide', right: 'she’ll grab it when it drops' },
    ],
  },

  // S4 — out the door, three real rides, your standing preference starred (dark)
  cab: {
    version: 1, card_id: 'c_cab', intent: 'options', theme: 'dark',
    blocks: [
      { type: 'header', label: 'out the door', ref: 'ride · 8pm' },
      { type: 'body', text: 'via carota · marcus + diana' },
      { type: 'body', text: 'tunnel route · arrive 7:52' },
      { type: 'key_values', rows: [
        { k: 'uber black · 3 min', v: '$52  ★' },
        { k: 'lyft lux · 6 min', v: '$48' },
        { k: 'uber x · 2 min', v: '$24' },
      ] },
      { type: 'footer', text: '★ your standing preference', right: 'pulled from calendar' },
    ],
  },
}

// ── the dashboard fixture (S1.5) — everything she's holding for Matt ──────────
export const dash = {
  cards: [card.boka, card.chiTracker],
  watchbar: [
    { kind: 'card', ref_id: 'c_boka', title: 'mom’s birthday · boka', note: 'book it', priority: 92, tier: 'high' },
    { kind: 'task', ref_id: 't_thx', title: 'thanksgiving tickets', note: '2 days left', priority: 88, tier: 'critical' },
    { kind: 'watch', ref_id: 'w_chi', title: 'chicago flights under $200', note: 'web', priority: 70, tier: 'medium' },
    { kind: 'task', ref_id: 't_lease', title: 'apartment lease', note: 'by dec 31', priority: 60, tier: 'medium' },
  ],
  watching: [
    { id: 'w1', type: 'web', title: 'chicago flights under $200' },
    { id: 'w2', type: 'reply', title: 'lighthouse client signoff' },
    { id: 'w3', type: 'web', title: 'apartment lease terms' },
    { id: 'w4', type: 'reply', title: 'marcus · promotion follow-up' },
  ],
  today: {
    date: 'Thu · Nov 20', holding: 24,
    calendar: [
      { time: '8:30am', title: 'lighthouse standup', note: '' },
      { time: '10:00am', title: 'stripe treasury pitch', note: 'the big one · deck ready' },
      { time: '12:30pm', title: 'sant ambroeus', note: 'mike + daniel' },
      { time: '2:00pm', title: 'marcus', note: 'promotion' },
      { time: '4:30pm', title: 'sarah + david', note: 'stripe team' },
      { time: '6:30pm', title: 'equinox tribeca', note: '' },
      { time: '8:30pm', title: 'employees only', note: '' },
    ],
    trackers: [
      { label: 'calories', value: '0', sub: '/ 2,200' },
      { label: 'sleep', value: '5h 38m', sub: 'last night' },
      { label: 'gym', value: '3 / 5', sub: 'this week' },
      { label: 'spend', value: '$5,420', sub: 'this month' },
    ],
    scheduled: [
      { title: 'book thanksgiving tickets', when: '2 days left', urgent: true },
      { title: 'apartment lease · respond', when: 'by dec 31' },
      { title: 'mom’s birthday gift', when: 'nov 28' },
      { title: 'Q3 tax filing · cpa chasing', when: 'this week' },
      { title: 'pay landlord · dec rent', when: 'auto' },
    ],
  },
  library: { people: 42, documents: 17, trackers: 6, todos: 9, connected: 14 },
}
