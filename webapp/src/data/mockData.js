// Single source of demo content. One consistent narrative across all four pages:
// a founder building Donna, an Antler/YC review tonight, pitch nerves, thin
// sleep, a few open loops. Swap these for real API data when the backend is on.

export const PLAN = {
  greeting: 'morning, aarav',
  date: 'tuesday · june 10',
  thesis: 'today is about the antler deck.',
  thesisCoda: 'everything else can wait.',
  because: ['the deck', 'review confidence', 'investor conversations', 'the raise'],
  hero: {
    register: 'confrontation',
    title: 'the deck, final pass',
    body: '4 hours till the 6pm review. the market-size slide is still the weak point — that\'s the one to fix first.',
  },
  openLoops: [
    { id: 1, text: 'reply to luca', meta: 'open 3 days' },
    { id: 2, text: 'antler intro form', meta: 'due friday' },
    { id: 3, text: 'call mom', meta: 'open 1 week' },
  ],
  calendar: [
    { time: '11:00', title: '1:1 with priya', tone: 'normal' },
    { time: '14:00', title: 'deep work — deck', tone: 'normal' },
    { time: '18:00', title: 'antler review', tone: 'peak' },
  ],
  trackers: [
    { label: 'sleep', value: '6.2h', tone: 'low' },
    { label: 'focus', value: '3.5h', tone: 'good' },
    { label: 'spend', value: '$240', tone: 'mid' },
    { label: 'mood', value: 'tense', tone: 'low' },
  ],
  nudge: 'you pitch better rested. block the night — wind down by 11.',
  whisper: 'you were nervous before the last pitch too. it went fine.',
}

export const MEMORY_SECTIONS = [
  { key: 'career', title: 'career', count: 12, summary: 'founder, building donna. ex-stripe (payments, 3 yrs).' },
  { key: 'projects', title: 'projects', count: 7, summary: 'donna (active). antler SG batch. a paused side app.' },
  { key: 'relationships', title: 'relationships', count: 9, summary: 'priya (cofounder), luca (mentor), mom — weekly calls.' },
  { key: 'health', title: 'health', count: 5, summary: 'sleep runs thin under deadlines. runs to reset.' },
  { key: 'goals', title: 'goals', count: 6, summary: 'raise a pre-seed. ship donna v1. sleep 7h+.' },
  { key: 'preferences', title: 'preferences', count: 8, summary: 'blunt over polite. lowercase. mornings for deep work.' },
]

export const MEMORY_RECENT = [
  {
    id: 'm1',
    summary: 'preparing for the antler review on june 10; deck market-size slide is the weak point.',
    confidence: 'high',
    when: '2 days ago',
    source: 'WhatsApp',
    related: ['the antler SG batch', 'pitch nerves pattern'],
  },
  {
    id: 'm2',
    summary: 'cofounder is priya; they disagree on pricing but resolve fast.',
    confidence: 'high',
    when: '1 week ago',
    source: 'Donna App',
    related: ['donna (project)', 'pricing debate'],
  },
  {
    id: 'm3',
    summary: 'sleep drops to ~6h the week before any big milestone.',
    confidence: 'medium',
    when: '2 weeks ago',
    source: 'Observed',
    related: ['pitch nerves pattern', 'health'],
  },
  {
    id: 'm4',
    summary: 'owes luca a reply since the intro to the antler partner.',
    confidence: 'high',
    when: '3 days ago',
    source: 'WhatsApp',
    related: ['luca (mentor)', 'open loops'],
  },
]

// Simple positioned graph (percent coords) for the relationship visualization.
export const MEMORY_GRAPH = {
  nodes: [
    { id: 'aarav', label: 'you', x: 50, y: 50, hub: true },
    { id: 'donna', label: 'donna', x: 22, y: 28 },
    { id: 'antler', label: 'antler', x: 78, y: 26 },
    { id: 'priya', label: 'priya', x: 20, y: 72 },
    { id: 'luca', label: 'luca', x: 80, y: 70 },
    { id: 'sleep', label: 'sleep', x: 50, y: 86 },
    { id: 'pitch', label: 'pitch nerves', x: 52, y: 16 },
  ],
  edges: [
    ['aarav', 'donna'], ['aarav', 'antler'], ['aarav', 'priya'],
    ['aarav', 'luca'], ['aarav', 'sleep'], ['aarav', 'pitch'],
    ['donna', 'priya'], ['antler', 'pitch'], ['antler', 'luca'],
    ['pitch', 'sleep'],
  ],
}

// What Donna currently believes is true — formed from observations over time.
// Confidence evolves; evidence accumulates. This is the product.
export const BELIEFS = [
  {
    id: 'mornings',
    confidence: 92,
    delta: '+3',
    up: true,
    strengthened: '2 days ago',
    statement: 'your best work happens before noon.',
    basis: ['38 deep-work sessions', 'calendar history', 'focus patterns'],
    related: ['focus', 'mornings'],
  },
  {
    id: 'sleep',
    confidence: 89,
    delta: '+2',
    up: true,
    strengthened: 'today',
    statement: 'sleep predicts your stress better than workload.',
    basis: ['6 weeks of sleep logs', 'stress markers in chat'],
    related: ['sleep', 'stress', 'the review'],
    chain: ['sleep', 'stress', 'review performance'],
  },
  {
    id: 'overprepare',
    confidence: 84,
    strengthened: '5 days ago',
    statement: "you overprepare when you're uncertain.",
    basis: ['investor meetings', 'product launches', 'pitch reviews'],
    related: ['pitch nerves', 'antler'],
  },
  {
    id: 'priya',
    confidence: 81,
    strengthened: '1 week ago',
    statement: "you trust priya's judgement more than your own on pricing.",
    basis: ['4 pricing debates', 'past decisions reversed'],
    related: ['priya', 'donna'],
  },
  {
    id: 'outreach',
    confidence: 74,
    delta: '+1',
    up: true,
    strengthened: 'yesterday',
    statement: 'you avoid founder outreach when the story feels weak.',
    basis: ['delayed intros', 'postponed investor emails'],
    related: ['antler', 'the raise'],
  },
]

// Pre-loaded chat thread showing cross-surface memory + source labels.
export const CHAT_HISTORY = [
  { from: 'donna', source: 'WhatsApp', item: { type: 'text', text: 'we were on your antler deck yesterday — the market-size slide.' } },
  { from: 'user', item: { type: 'text', text: 'yeah it still feels flat' } },
  {
    from: 'donna',
    item: {
      type: 'memory',
      text: 'i remembered something.\n\nyou felt the same before your last pitch. then you led with the user story instead of the numbers, and the room leaned in.',
    },
  },
  { from: 'donna', item: { type: 'text', text: 'open with the user, not the TAM. the number means more once they care.' } },
]
