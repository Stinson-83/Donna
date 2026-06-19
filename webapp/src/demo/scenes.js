// The scene registry — Matt Wilson's day, the 73-second cut. Each conversation is
// ONE continuous clip the Live (or WhatsApp) surface plays out; the recorder films
// it frame-by-frame. The closer (S7) is built natively in Remotion, not here.
// Source of truth: DEMO_VIDEO_FINAL_DESIGN. Donna voice: lowercase, no em dashes.
import * as D from './data.js'

const t = (text) => ({ type: 'text', text })
const c = (card) => ({ type: 'card', card })
const donna = (item) => ({ from: 'donna', item })
const user = (text) => ({ from: 'user', item: t(text) })
const voice = (text, dur = '0:03') => ({ from: 'user', item: { type: 'voice', text, dur } })

// WhatsApp history helpers (seeded, shown instantly above today's exchange)
const wDiv = (label) => ({ divider: label })
const wText = (from, text, ts) => ({ from, item: { type: 'text', text }, ts })
const wLink = (from, title, domain, caption, ts) => ({ from, item: { type: 'link', title, domain, caption }, ts })
const wPdf = (from, name, meta, caption, ts) => ({ from, item: { type: 'pdf', name, meta, caption }, ts })

// the running WhatsApp thread before today — Tue/Wed, from Matt's locked profile
const whatsappHistory = [
  wDiv('TUESDAY · NOV 18'),
  wLink('user', 'The Agent-Native Stack · Ben Thompson', 'stratechery.com', 'wanna read this when i get time', '11:32am'),
  wText('donna', 'saved. you have a 2-hour window tomorrow morning before lighthouse standup. queue it for then?', '11:33am'),
  wText('donna', 'chicago flights for thanksgiving still above $290. you wanted below 200. wait or book?', '9:14pm'),
  wText('user', 'watch one more week', '9:15pm'),
  wDiv('WEDNESDAY · NOV 19'),
  wPdf('user', 'nyu_matt_2025.pdf', '4.2 MB · 12 pages', "here's my annual checkup report", '8:22am'),
  wText('donna', 'saved. cholesterol up 178 to 196 since march. vitamin D dropped 21 to 19. both heading the wrong way. want me to schedule a follow-up with dr. cohen?', '8:24am'),
  wText('user', 'back from equinox', '6:45pm'),
  wText('donna', 'logged. 3 of 5 this week.', '6:45pm'),
]

export const SCENES = [
  // S1 · 6:42am — morning brief. she texts first. pure text.
  { id: 'brief', n: 1, at: '6:42am', surface: 'live', tab: 'live', play: true, beat: 'morning brief', chatThread: [
    donna(t('heavy day. stripe at 10, marcus at 2.')),
    donna(t('raining. grab the umbrella.')),
    donna(t('kimberly-clark + kenvue: $48b deal. huggies + tylenol under one roof now.')),
    donna(t('chicago flights still $290. 2 days left.')),
    donna(t('eat before the pitch.')),
  ] },

  // S1.5 · 7:05am — the dashboard. everything she's holding. scroll + open menu.
  { id: 'dashboard', n: 2, at: '7:05am', surface: 'dashboard', tab: 'dashboard', dash: true, beat: "what she's holding", data: D.dash },

  // S2 · 12:25pm — lunch check-in. voice reply, gentle accountability.
  { id: 'lunch', n: 3, at: '12:25pm', surface: 'live', tab: 'live', play: true, beat: 'lunch check-in', chatThread: [
    donna(t('lunch in 5 with mike + daniel. what are you getting?')),
    voice('carbonara, side salad.', '0:02'),
    donna(t('logged. 960 cal.')),
    donna(t('4th carbonara this week. you said no carbs through thursday.')),
  ] },

  // S3 · 2:18pm — offsite vs wedding. one dark card, one tap, three actions.
  { id: 'email', n: 3, at: '2:18pm', surface: 'live', tab: 'live', play: true, beat: 'offsite vs wedding', chatThread: [
    donna(t('offsite confirmed dec 18-21. hits emily’s wedding on the 20th.')),
    donna(c(D.card.conflict)),
    user('split it'),
    donna(t('sent. email to rachel, leaving dec 20 evening.')),
    donna(t('flight rerouted aspen to lax, dec 20. emily’s rsvp updated.')),
  ] },

  // S4 · 7:32pm — the landmine save, on WhatsApp (the Meta moat). shows the running
  // history with donna (Tue/Wed) then today's exchange plays out.
  { id: 'whatsapp', n: 4, at: '7:32 PM', surface: 'whatsapp', play: true, beat: 'whatsapp · landmine save', history: whatsappHistory, chatThread: [
    user("fuck, what was marcus’s wife’s name again"),
    donna(t('diana. she runs an arts foundation at columbia.')),
    donna(t("don’t bring up lighthouse. marcus said she walked out last time it came up at dinner.")),
    user("you’re a lifesaver"),
    donna(t("go get ’em.")),
  ] },

  // S5 · 8:15pm — cab booking. decode ambiguity, three rides, your preference.
  { id: 'cab', n: 5, at: '8:15pm', surface: 'live', tab: 'live', play: true, beat: 'cab · three options', chatThread: [
    voice('donna i need to get to dinner', '0:02'),
    donna(t("via carota at 8pm with marcus + diana. tunnel, rangers game’s blocking the bridge. you’ll be at the door 7:52, 8 min ahead like marcus prefers. pick:")),
    donna(c(D.card.cab)),
    user('uber black'),
    donna(t('locked. akhil, plate H8J 4321. white tesla, 3 min out.')),
  ] },

  // S6 · 10:47pm — visa prep. the banger. pure text, total agency.
  { id: 'visa', n: 6, at: '10:47pm', surface: 'live', tab: 'live', play: true, beat: 'visa prep', chatThread: [
    donna(t('your swiss visa appointment is in 2 days.')),
    donna(t('i pulled everything. passport, photos, employment letter, bank statements (chase + schwab, 3 months), hotel + flight, travel insurance.')),
    donna(t('drafted the no-objection letter. marcus signs it in the morning.')),
    donna(t('all sent to your inbox. fedex on west 16th is open till midnight, 3 min walk. print them on your way out.')),
    donna(t('you’ll be ready.')),
  ] },

  // S7 · closer — built natively in Remotion (typography on paper). not captured.
]

export const SCENE_BY_ID = Object.fromEntries(SCENES.map((s) => [s.id, s]))
