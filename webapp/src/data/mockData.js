// Single source of demo content. One consistent narrative across every page:
// aarav, a founder building poke, a sequoia term sheet to close before a move to
// waterloo, cofounder raghav, brother aniroodh, pitch nerves, thin sleep, a few
// open loops. Swap these for real API data when the backend is on.

export const PLAN = {
  greeting: 'morning, aarav',
  date: 'tuesday · june 10',
  thesis: 'today is about the sequoia term sheet.',
  thesisCoda: 'everything else can wait.',
  because: ['the term sheet', 'the raise', 'investor conversations', 'the waterloo move'],
  decision: {
    considered: ['the data room', 'roadmap planning', 'hiring'],
    chose: 'the sequoia close',
    because: 'it gates the move and three decisions after it; the rest can wait a day.',
  },
  nudgeBelief: 'sleep predicts your stress better than workload',
  hero: {
    register: 'confrontation',
    title: 'the deck, final pass',
    body: '4 hours till the sequoia call. the market-size slide is still the weak point — that\'s the one to fix first.',
  },
  openLoops: [
    { id: 1, text: 'reply to the sequoia partner', meta: 'open 3 days' },
    { id: 2, text: 'send the data room', meta: 'due friday' },
    { id: 3, text: 'call mom', meta: 'open 1 week' },
  ],
  calendar: [
    { time: '11:00', title: '1:1 with raghav', tone: 'normal' },
    { time: '14:00', title: 'deep work — deck', tone: 'normal' },
    { time: '18:00', title: 'sequoia call', tone: 'peak' },
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

// AREAS — the index of what Donna KNOWS about you, by domain. Not messages:
// distilled knowledge that accrues over time. (History is the transcript; this
// is what she's learned from it.)
export const MEMORY_SECTIONS = [
  { key: 'work', title: 'work', count: 14, summary: 'building poke. raising a pre-seed from sequoia. cofounder raghav.' },
  { key: 'people', title: 'people', count: 11, summary: 'raghav (cofounder), aniroodh (brother), priya, mom — sunday calls.' },
  { key: 'the move', title: 'the move', count: 6, summary: 'relocating to waterloo in aug. permit + housing in motion.' },
  { key: 'money', title: 'money', count: 8, summary: 'hdfc auto-pays; keeps a thin buffer until the round closes.' },
  { key: 'health', title: 'health', count: 5, summary: 'sleep slips under deadlines. runs to reset.' },
  { key: 'patterns', title: 'patterns', count: 9, summary: 'deep work before noon. overprepares when the story feels weak.' },
]

// RECENT — the latest EVIDENCE she's filed. Each is a durable thing she learned
// (with a confidence and the belief it supports), not a line of chat. This is the
// difference from History: History scrolls; these compound into the constellation.
export const MEMORY_RECENT = [
  {
    id: 'm1',
    summary: "sequoia's term sheet is the one to close before the waterloo move.",
    confidence: 'high',
    when: '2 days ago',
    source: 'WhatsApp',
    supports: ["you won't relocate with the round still open", 'you avoid outreach when the story feels weak'],
  },
  {
    id: 'm2',
    summary: 'cofounder is raghav; you disagree on pricing but settle it fast.',
    confidence: 'high',
    when: '1 week ago',
    source: 'Donna App',
    supports: ['you trust raghav on product, push back on pricing'],
  },
  {
    id: 'm3',
    summary: 'sleep drops to ~6h the week before any pitch.',
    confidence: 'medium',
    when: '2 weeks ago',
    source: 'Observed',
    supports: ['sleep predicts your stress better than workload'],
  },
  {
    id: 'm4',
    summary: 'aniroodh lands at changi on the 28th; you always do the airport run yourself.',
    confidence: 'high',
    when: '3 days ago',
    source: 'WhatsApp',
    supports: ['you keep family time even mid-sprint'],
  },
  {
    id: 'm5',
    summary: 'deep work lands before noon; you keep meetings to the afternoon.',
    confidence: 'high',
    when: '4 days ago',
    source: 'Journal',
    supports: ['your best work happens before noon'],
  },
]

// Simple positioned graph (percent coords) for the relationship visualization.
export const MEMORY_GRAPH = {
  nodes: [
    { id: 'aarav', label: 'you', x: 50, y: 50, hub: true },
    { id: 'poke', label: 'poke', x: 22, y: 28 },
    { id: 'sequoia', label: 'sequoia', x: 78, y: 26 },
    { id: 'raghav', label: 'raghav', x: 20, y: 72 },
    { id: 'aniroodh', label: 'aniroodh', x: 80, y: 70 },
    { id: 'sleep', label: 'sleep', x: 50, y: 86 },
    { id: 'pitch', label: 'pitch nerves', x: 52, y: 16 },
  ],
  edges: [
    ['aarav', 'poke'], ['aarav', 'sequoia'], ['aarav', 'raghav'],
    ['aarav', 'aniroodh'], ['aarav', 'sleep'], ['aarav', 'pitch'],
    ['poke', 'raghav'], ['sequoia', 'pitch'], ['pitch', 'sleep'],
  ],
}

// What Donna currently believes is true — formed from observations over time.
// Each belief carries a consequence (it changed a recommendation), an explainer
// (why i think this), a confidence history, and the memories it rests on.
export const BELIEFS = [
  {
    id: 'mornings',
    confidence: 92,
    delta: '+3',
    up: true,
    strengthened: '2 days ago',
    statement: 'your best work happens before noon.',
    consequence: 'i scheduled the deck rewrite into your 9–12 block, not the afternoon.',
    evidence: ['38 deep-work sessions before noon', 'calendar history', 'focus patterns'],
    counter: ['2 strong evening sessions during launch week'],
    history: [64, 78, 85, 92],
    strengthenedBy: 'another 3-hour morning focus block, zero context-switches.',
    reasoning: 'output quality clusters before noon far more tightly than it does by total hours worked.',
    related: ['focus', 'mornings'],
  },
  {
    id: 'sleep',
    confidence: 89,
    delta: '+2',
    up: true,
    strengthened: 'today',
    statement: 'sleep predicts your stress better than workload.',
    consequence: 'i prioritized sleep recovery in today’s plan and pushed the 11pm wind-down.',
    evidence: ['6 weeks of sleep logs', 'stress markers in chat', '3 milestone weeks'],
    counter: ['one calm week on 5h sleep'],
    history: [71, 80, 84, 89],
    strengthenedBy: 'stress rose ~40h after sleep dropped — again.',
    reasoning: 'across milestones, low sleep precedes stress more reliably than high workload does.',
    related: ['sleep', 'stress', 'the raise'],
    chain: ['sleep', 'stress', 'pitch performance'],
  },
  {
    id: 'overprepare',
    confidence: 84,
    strengthened: '5 days ago',
    statement: "you overprepare when you're uncertain.",
    consequence: 'i stopped suggesting more deck edits and pushed you toward the story instead.',
    evidence: ['investor meetings', 'product launches', 'pitch reviews'],
    counter: ['the seed deck you shipped in one pass'],
    history: [70, 76, 82, 84],
    strengthenedBy: 'a fourth deck rewrite before the sequoia call.',
    reasoning: 'rework spikes when the underlying decision feels unresolved, not when stakes are simply high.',
    related: ['pitch nerves', 'sequoia'],
  },
  {
    id: 'raghav',
    confidence: 81,
    strengthened: '1 week ago',
    statement: 'you trust raghav on product, but push back on pricing.',
    consequence: 'i flagged the pricing slide for raghav before the call, not for you.',
    evidence: ['4 pricing debates', 'product calls you ceded to him'],
    counter: ['one pricing call you held against him'],
    history: [68, 74, 79, 81],
    strengthenedBy: 'you deferred to him on the enterprise tier last week.',
    reasoning: 'on product your final calls track his; on pricing you hold your own line.',
    related: ['raghav', 'poke'],
  },
  {
    id: 'outreach',
    confidence: 82,
    delta: '+1',
    up: true,
    strengthened: 'yesterday',
    statement: 'you avoid founder outreach when the story feels weak.',
    consequence: 'i held back the “send the investor email” nudge until the narrative is tighter.',
    evidence: ['delayed intros', 'postponed investor emails', 'recruiting outreach gaps'],
    counter: ['cold outreach you sent the week the demo landed'],
    history: [71, 75, 79, 82],
    strengthenedBy: 'the postponed sequoia intro while the deck still felt off.',
    reasoning: 'outreach stalls track narrative confidence, not your comfort with reaching out.',
    related: ['sequoia', 'the raise'],
  },
]

// What Donna does NOT yet believe — competing hypotheses with split evidence.
// When one resolves, it graduates into a belief. This is the learning frontier.
export const OPEN_QUESTIONS = [
  {
    id: 'q1',
    confidence: 61,
    question: 'does your stress come from the pitches, or from the lost sleep?',
    status: 'evidence supports both — they move together.',
    leaning: 'leaning sleep, but i can\'t separate them yet.',
  },
  {
    id: 'q2',
    confidence: 58,
    question: 'are the investor delays about outreach avoidance, or weak positioning?',
    status: 'need more evidence.',
    leaning: 'i suspect positioning. not sure.',
  },
  {
    id: 'q3',
    confidence: 54,
    question: 'does raghav improve your decision quality, or just your confidence?',
    status: 'still uncertain.',
    leaning: 'too early to call.',
  },
]

// Beliefs Donna revised — proof she learns, not just stores.
export const REVISIONS = [
  {
    id: 'outreach',
    from: { statement: 'you dislike outreach', conf: 71 },
    to: { statement: 'you avoid outreach when the narrative feels weak', conf: 82 },
    why: 'found repeated evidence across fundraising and recruiting — the trigger is a weak story, not outreach itself.',
  },
  {
    id: 'mornings',
    from: { statement: "you're simply a morning person", conf: 64 },
    to: { statement: 'your best work happens before noon', conf: 92 },
    why: '38 deep-work sessions clustered before noon; it’s about output, not preference.',
  },
]

// Pre-loaded chat thread showing cross-surface memory + source labels.
export const CHAT_HISTORY = [
  { from: 'donna', source: 'WhatsApp', item: { type: 'text', text: 'we were on your sequoia deck yesterday — the market-size slide.' } },
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
