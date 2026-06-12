/**
 * Donna — Playwright demo recorder.
 *
 * Records the 23-shot investor demo (DEMO_VIDEO_PLAN.md / demo_scenarios.yaml),
 * one .webm + keyframe .png per shot, in a phone viewport.
 *
 *   - APP shots (Dashboard, Live)      -> drive the real Donna webapp at $DEMO_URL.
 *   - WhatsApp / Dynamic-Island / title / end-card shots -> rendered as faithful
 *     HTML frames (those surfaces are not web pages).
 *
 * For the FULL live experience (the Live-tab consent + ride cards, the cross-surface
 * dashboard sync), run the webapp against the seeded live backend (VITE_MOCK=0),
 * load demo_seed.py, and fire triggers with `python demo_run.py --mode live` while
 * this records. With the default MOCK webapp you still get the app shell + the
 * rendered frames for every shot.
 *
 * Setup:
 *   npm i -D playwright typescript tsx
 *   npx playwright install chromium
 *   # start the webapp first:  (cd webapp && npm run dev)   ->  http://localhost:5173
 *   npx tsx playwright_demo_runner.ts                 # record all 23 shots
 *   npx tsx playwright_demo_runner.ts --only shot_6   # one shot
 *   DEMO_URL=http://localhost:5173 DEMO_OUT=recordings npx tsx playwright_demo_runner.ts
 */
import { chromium, Browser, BrowserContext, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.DEMO_URL || 'http://localhost:5173';
const OUT = process.env.DEMO_OUT || 'recordings';
const HEADLESS = process.env.DEMO_HEADED ? false : true;

// iPhone-ish portrait. Video + screenshots come out at this size.
const VP = { width: 393, height: 852 };
const DSF = 3;
const PAPER = '#F6F1EA';

// ── design-system frame (paper, rust, lowercase) for non-web surfaces ────────
const FRAME_CSS = `
  * { margin:0; padding:0; box-sizing:border-box; -webkit-font-smoothing:antialiased; }
  html,body { width:${VP.width}px; height:${VP.height}px; overflow:hidden;
    font-family:'Red Hat Text',-apple-system,system-ui,sans-serif; background:${PAPER}; color:#201A14; }
  .serif { font-family:'EB Garamond',Georgia,serif; }
  .stamp { position:absolute; top:18px; right:20px; font-family:Georgia,serif; font-style:italic; font-size:13px; color:#7B5544; }
  .wm { font-family:'EB Garamond',Georgia,serif; font-style:italic; color:#7B5544; }
`;

function pageHtml(body: string, extra = ''): string {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${FRAME_CSS}${extra}</style></head><body>${body}</body></html>`;
}

interface WaLine { from: 'donna' | 'user'; text: string }

function whatsappFrame(o: { at: string; lock?: boolean; lines: WaLine[]; ref?: string; body?: string; buttons?: string[] }): string {
  const css = `
    .wrap { padding:0 16px; }
    .lock { position:absolute; inset:0; display:flex; flex-direction:column; justify-content:center; padding:0 18px;
      background:linear-gradient(160deg,#efe8df,#e7ddd2); }
    .note { background:rgba(255,255,255,0.92); border-radius:22px; padding:16px 18px; box-shadow:0 8px 30px rgba(63,42,30,0.12); }
    .who { font-weight:700; font-size:13px; color:#7B5544; margin-bottom:6px; }
    .who span { float:right; font-weight:600; color:#9a8b7d; }
    .body { font-size:15px; line-height:1.45; }
    .head { padding:48px 16px 14px; }
    .head h1 { font-size:20px; font-weight:700; }
    .head .sub { font-size:12px; color:#9a8b7d; margin-top:2px; }
    .bub { max-width:80%; padding:11px 14px; border-radius:18px; font-size:15px; line-height:1.4; margin:8px 0; }
    .donna { background:#fff; border:1px solid #e3dbd1; border-bottom-left-radius:6px; }
    .user  { background:#C99A7E; color:#fff; margin-left:auto; border-bottom-right-radius:6px; }
    .card { background:#251D16; color:#F3EBE1; border-radius:20px; padding:18px; margin:12px 0; box-shadow:0 14px 40px rgba(32,22,14,0.3); }
    .card .label { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:#C99A7E; }
    .card .ref { float:right; font-size:12px; color:#bcae9f; }
    .card .ctext { font-size:15px; line-height:1.5; margin-top:10px; }
    .card b { color:#fff; }
    .btns { margin-top:14px; display:flex; flex-direction:column; gap:9px; }
    .btn { border:1px solid rgba(243,235,225,0.25); border-radius:999px; padding:11px; text-align:center; font-size:14px; }
    .btn.primary { background:#C99A7E; color:#2a1d14; border-color:transparent; font-weight:600; }
  `;
  const stamp = o.at ? `<div class="stamp">${o.at}</div>` : '';
  const card = o.body
    ? `<div class="card"><div class="label">needs your eye<span class="ref">${o.ref || ''}</span></div>
         <div class="ctext">${o.body}</div>
         ${o.buttons ? `<div class="btns">${o.buttons.map((b, i) => `<div class="btn ${i === 0 ? 'primary' : ''}">${b}</div>`).join('')}</div>` : ''}
       </div>`
    : '';
  if (o.lock) {
    const l = o.lines[0];
    return pageHtml(`${stamp}<div class="lock"><div class="note"><div class="who">donna <span>${o.at}</span></div><div class="body">${l.text}</div></div></div>`, css);
  }
  const bubbles = o.lines.map(l => `<div class="bub ${l.from}">${l.text}</div>`).join('');
  return pageHtml(`${stamp}<div class="head"><h1 class="serif">donna</h1><div class="sub">whatsapp</div></div><div class="wrap">${bubbles}${card}</div>`, css);
}

function islandFrame(o: { at: string; query?: string; card?: { ref: string; body: string }; collapsed?: string }): string {
  const css = `
    .ig { position:absolute; inset:0; background:#0b0b0b; color:#eee; padding-top:120px; }
    .ig .row { height:120px; border-bottom:1px solid #1c1c1c; margin:0 0 4px; background:linear-gradient(90deg,#161616,#1d1d1d); }
    .island { position:absolute; top:14px; left:50%; transform:translateX(-50%); background:#000; color:#fff;
      border-radius:26px; padding:14px 18px; width:${o.card ? '88%' : '180px'}; box-shadow:0 10px 30px rgba(0,0,0,0.5); }
    .island .label { font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:#C99A7E; }
    .island .ref { float:right; font-size:11px; color:#bbb; }
    .island .b { font-size:14px; line-height:1.5; margin-top:8px; }
    .wave { display:flex; gap:4px; align-items:center; justify-content:center; height:18px; }
    .wave i { width:3px; background:#C99A7E; border-radius:2px; }
    .q { font-size:13px; color:#ddd; text-align:center; margin-top:8px; }
    .ok { font-size:13px; color:#9fd9a8; text-align:center; }
  `;
  const rows = Array.from({ length: 8 }).map(() => '<div class="row"></div>').join('');
  let island = '<div class="wave">' + [6, 12, 9, 16, 8, 13, 7].map(h => `<i style="height:${h}px"></i>`).join('') + '</div>';
  if (o.query) island += `<div class="q">${o.query}</div>`;
  if (o.card) island = `<div class="label">from memory<span class="ref">${o.card.ref}</span></div><div class="b">${o.card.body}</div>`;
  if (o.collapsed) island = `<div class="ok">${o.collapsed}</div>`;
  const stamp = o.at ? `<div class="stamp" style="color:#C99A7E">${o.at}</div>` : '';
  return pageHtml(`<div class="ig">${rows}</div><div class="island">${island}</div>${stamp}`, css);
}

function titleFrame(line: string): string {
  return pageHtml(`<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:0 40px;text-align:center">
    <div class="wm" style="font-size:54px">donna</div>
    <div style="margin-top:24px;font-size:15px;line-height:1.6;color:#5b4d40">${line}</div></div>`);
}

function endFrame(): string {
  return pageHtml(`<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
    <div class="wm" style="font-size:60px">donna</div>
    <div style="margin-top:18px;font-size:16px;color:#7B5544" class="serif" >she texts first.</div></div>`);
}

// ── app drivers (the real webapp) ────────────────────────────────────────────
async function gotoApp(page: Page): Promise<void> {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  const demo = page.getByText(/see the demo/i);
  if (await demo.isVisible().catch(() => false)) { await demo.click(); await page.waitForTimeout(700); }
  await page.waitForTimeout(500);
}

async function openTab(page: Page, name: string): Promise<void> {
  await page.getByRole('button', { name, exact: true }).click().catch(() => {});
  await page.waitForTimeout(450);
}

async function slowScroll(page: Page): Promise<void> {
  for (let y = 0; y <= 520; y += 26) {
    await page.mouse.wheel(0, 26).catch(() => {});
    await page.waitForTimeout(110);
  }
}

// ── the 23 shots (mirrors demo_scenarios.yaml) ───────────────────────────────
interface Shot {
  id: string; title: string; at: string; durationMs: number;
  run?: (page: Page) => Promise<void>;   // APP shot: drive the live webapp
  html?: () => string;                   // FRAME shot: rendered surface
}

const SHOTS: Shot[] = [
  { id: 'shot_1', title: 'The hook', at: '', durationMs: 4000,
    html: () => titleFrame('imagine the best chief of staff in the world. now imagine she never sleeps, never forgets, and texts you first.') },

  { id: 'shot_2', title: 'Dashboard reveal', at: '7:30am', durationMs: 9000,
    run: async (page) => { await openTab(page, 'Dashboard'); await page.waitForTimeout(700); await slowScroll(page); } },

  { id: 'shot_3', title: 'The lock-screen ping', at: '8:42am', durationMs: 6000,
    html: () => whatsappFrame({ at: '8:42am', lock: true, lines: [{ from: 'donna', text: "heads up. sequoia partner replied to your thread. they want your answer by EOD. the term sheet expires tomorrow at noon." }] }) },

  { id: 'shot_4', title: 'Summary + reply options', at: '8:42am', durationMs: 8000,
    html: () => whatsappFrame({ at: '8:42am', lines: [], ref: 'Sequoia · term sheet', body: "sequoia replied. they want an answer by <b>EOD</b>, and the term sheet expires <b>tomorrow at noon</b>.", buttons: ['accept the terms', 'counter on valuation', 'ask for 48 more hours'] }) },

  { id: 'shot_5', title: 'The draft + send', at: '8:42am', durationMs: 4000,
    html: () => whatsappFrame({ at: '8:42am', lines: [{ from: 'user', text: 'counter on valuation' }, { from: 'donna', text: 'sent.' }] }) },

  { id: 'shot_6', title: 'The shortfall card', at: '10:15am', durationMs: 8000,
    html: () => whatsappFrame({ at: '10:15am', lines: [], ref: 'HDFC · auto-pay', body: "aws <b>47,200</b> auto-debits in 4 days. your hdfc current is <b>4,200</b> short. transfer ₹5,000 from savings now?", buttons: ['yes, transfer 5,000', 'pause auto-pay', 'remind me tomorrow'] }) },

  { id: 'shot_7', title: 'Transfer + keep watching', at: '10:15am', durationMs: 8000,
    html: () => whatsappFrame({ at: '10:15am', lines: [{ from: 'user', text: 'yes, transfer' }, { from: 'donna', text: "done. ₹5,000 moved. balance now ₹52,000. i'll keep watching the bill until it clears." }] }) },

  { id: 'shot_8', title: 'She asks first', at: '1:42pm', durationMs: 6000,
    html: () => whatsappFrame({ at: '1:42pm', lines: [{ from: 'donna', text: 'what did you have for lunch? updating your tracker.' }] }) },

  { id: 'shot_9', title: 'Logged + the honest line', at: '1:42pm', durationMs: 10000,
    html: () => whatsappFrame({ at: '1:42pm', lines: [{ from: 'donna', text: 'what did you have for lunch? updating your tracker.' }, { from: 'user', text: 'biryani and sweet lassi' }, { from: 'donna', text: "logged. ~1,840 cal so far. ~600 left for dinner. heads up — this is day 3 you've crossed your monday goal. want me to suggest a lighter dinner around 7?" }] }) },

  { id: 'shot_10', title: 'Long-press, mid-scroll', at: '2:30pm', durationMs: 5000,
    html: () => islandFrame({ at: '2:30pm' }) },

  { id: 'shot_11', title: 'The recall over Instagram', at: '2:30pm', durationMs: 9000,
    html: () => islandFrame({ at: '2:30pm', card: { ref: 'Lotus Thai · holland village', body: "aniroodh texted you last tuesday: 'the pad see ew, mira. you have to.' you said you'd take ishaan there saturday." } }) },

  { id: 'shot_12', title: 'Book it', at: '2:30pm', durationMs: 8000,
    html: () => islandFrame({ at: '2:30pm', collapsed: 'booked · 8pm saturday · 2 people · OpenTable' }) },

  { id: 'shot_13', title: 'The ask (Live tab)', at: '4:00pm', durationMs: 9000,
    run: async (page) => {
      await openTab(page, 'Live');
      const input = page.getByPlaceholder('Message');
      await input.click().catch(() => {});
      await input.type('book me a cab to changi t1 at 5:30am tomorrow.', { delay: 45 }).catch(() => {});
      await input.press('Enter').catch(() => {});
      await page.waitForTimeout(2000);
    } },

  { id: 'shot_14', title: 'Just-in-time consent', at: '4:00pm', durationMs: 7000,
    html: () => whatsappFrame({ at: '4:00pm', lines: [], ref: 'Grab', body: "donna will be able to book rides on your behalf and pay via your saved card.", buttons: ['allow', 'not now'] }) },

  { id: 'shot_15', title: 'Interactive ride cards', at: '4:00pm', durationMs: 9000,
    html: () => whatsappFrame({ at: '4:00pm', lines: [], ref: '5:30am tomorrow', body: "grab standard · $28 · arrives 5:12 — <b>recommended, matches your usual</b>", buttons: ['book standard'] }) },

  { id: 'shot_16', title: 'Execute + sync', at: '4:00pm', durationMs: 6000,
    run: async (page) => { await openTab(page, 'Dashboard'); await page.waitForTimeout(700); await slowScroll(page); } },

  { id: 'shot_17', title: 'Four memories collide', at: '6:15pm', durationMs: 10000,
    html: () => whatsappFrame({ at: '6:15pm', lines: [], ref: "mom's birthday · saturday", body: "mom's birthday is saturday. you have lotus thai at 8pm with ishaan. her favorites: lilies. fnp delivers by 10am. send <b>₹1,899</b> bouquet?", buttons: ['yes, send lilies', 'different flowers', "i'll handle it"] }) },

  { id: 'shot_18', title: 'Sent + the pattern', at: '6:15pm', durationMs: 8000,
    html: () => whatsappFrame({ at: '6:15pm', lines: [{ from: 'user', text: 'yes, send lilies' }, { from: 'donna', text: "done. ₹1,899. delivery saturday 9-10am. card note: 'happy birthday ma. love, mira.' adding a reminder to call her at noon — you usually do." }] }) },

  { id: 'shot_19', title: 'The audit', at: '7:48pm', durationMs: 6000,
    html: () => whatsappFrame({ at: '7:48pm', lines: [], ref: 'Spotify · renews tomorrow', body: "spotify renews tomorrow. <b>₹229</b>. you used it twice this month. apple music handles the rest. cancel?", buttons: ['cancel', 'keep it', 'remind me next month'] }) },

  { id: 'shot_20', title: 'Cancelled + learned', at: '7:48pm', durationMs: 6000,
    html: () => whatsappFrame({ at: '7:48pm', lines: [{ from: 'user', text: 'cancel' }, { from: 'donna', text: "cancelled. ₹229/mo saved. i'll remember you preferred apple music." }] }) },

  { id: 'shot_21', title: 'Today, done', at: '11:02pm', durationMs: 8000,
    run: async (page) => { await openTab(page, 'Dashboard'); await page.waitForTimeout(600); await slowScroll(page); } },

  { id: 'shot_22', title: 'The moat', at: '11:02pm', durationMs: 8000,
    html: () => pageHtml(`<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
      <div class="serif" style="font-size:40px">247</div><div style="font-size:12px;color:#9a8b7d;letter-spacing:.1em">DAYS WITH DONNA</div>
      <div class="serif" style="font-size:40px;margin-top:22px">1,847</div><div style="font-size:12px;color:#9a8b7d;letter-spacing:.1em">THINGS CAUGHT</div>
      <div class="serif" style="font-size:40px;margin-top:22px">94%</div><div style="font-size:12px;color:#9a8b7d;letter-spacing:.1em">DELIVERED ON TIME</div></div>`) },

  { id: 'shot_23', title: 'End card', at: '', durationMs: 8000, html: () => endFrame() },
];

// ── record loop ──────────────────────────────────────────────────────────────
async function recordShot(browser: Browser, shot: Shot): Promise<void> {
  const dir = path.join(OUT, shot.id);
  fs.mkdirSync(dir, { recursive: true });
  const context: BrowserContext = await browser.newContext({
    viewport: VP, deviceScaleFactor: DSF, isMobile: true, hasTouch: true,
    recordVideo: { dir, size: VP },
  });
  const page = await context.newPage();
  try {
    if (shot.run) { await gotoApp(page); await shot.run(page); }
    else if (shot.html) { await page.setContent(shot.html(), { waitUntil: 'load' }); }
    await page.waitForTimeout(shot.durationMs);
    await page.screenshot({ path: path.join(dir, `${shot.id}.png`) });
  } catch (e: any) {
    console.warn(`  ! ${shot.id}: ${e?.message || e}`);
  }
  await context.close(); // flushes the video
  const vids = fs.readdirSync(dir).filter(f => f.endsWith('.webm'));
  if (vids[0]) fs.renameSync(path.join(dir, vids[0]), path.join(dir, `${shot.id}.webm`));
  console.log(`✓ recorded ${shot.id} — ${shot.title}`);
}

async function main(): Promise<void> {
  const only = (() => { const i = process.argv.indexOf('--only'); return i >= 0 ? process.argv[i + 1] : null; })();
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: HEADLESS });
  console.log(`recording ${only ? only : 'all 23 shots'} from ${BASE_URL} -> ${OUT}/`);
  for (const shot of SHOTS) {
    if (only && shot.id !== only) continue;
    await recordShot(browser, shot);
  }
  await browser.close();
  console.log('done. per-shot videos + keyframes are in', OUT + '/');
}

main().catch((e) => { console.error(e); process.exit(1); });
