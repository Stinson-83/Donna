# Domain Data Tables — what Donna observes

**Status:** Spec · 2026-06-11
**Depends on:** `architecture_decision.md` (§3 Context Assembly = retrieval, §10.1 memory backends), `proactive_runner.md` (§5 Layer-1 diff reads these), `memory_system.md` (Layer 1 raw-stays-in-source).
**Extends:** `database_schema.md`, which covers the meta-layer (events/workflows/watches/actions) well but **under-covers the domain data the demo needs**. This adds the concrete per-domain tables behind the dashboard's watching/scheduled/logistics and the finance/health/subscription/travel workflows. Unblocks building M1–M4.

---

## 1. The principle: cache the diff-able, retrieve the bulk

`memory_system.md` says "Donna does not duplicate everything; she retrieves when needed." True for bulk content. But `proactive_runner.md §5` needs a **warm, structured cache to diff against** every tick — you cannot detect "balance now below the AWS bill" by re-reading the bank on a 30s loop.

The resolution:

> **Cache the structured, queryable, frequently-diffed *facts* (calendar events, balances, bills, subscriptions, recent meals). Retrieve the bulk *content* (full email bodies, statements, documents) on demand via tools.**

So `finance_accounts.balance` is a cached fact (diffed by the runner); the full transaction PDF is not (fetched by a `read_*` tool when the loop needs it). Every domain table below is Donna's **working model of observed reality**, synced from an integration — not the external source of truth, but cheap enough to reason over continuously.

---

## 2. Common shape

Every domain table shares:

| Column | Why |
|---|---|
| `user_id` | tenant scope |
| `integration_id` | provenance (which connection produced this) |
| `external_id` + UNIQUE(user_id, source, external_id) | **idempotent upsert** — re-syncing never duplicates |
| `synced_at` | freshness; staleness drives a re-sync |
| `source` | gmail / google_calendar / hdfc / spotify / manual |

**Writers:** integration sync workers (deterministic) and the `integration_syncs` cursor (see `onboarding.md`). **Readers:** Context Assembly (ADR §3), `recall_*`/`read_*` tools, and the runner's Layer-1 diff. No LLM writes these.

---

## 3. Calendar

Backs the dashboard `scheduled` section (M1), the Conflict engine (overlap math), and the Preparation workflow.

```sql
calendar_events
  id UUID PK
  user_id UUID
  integration_id UUID
  external_id TEXT
  title TEXT
  description TEXT
  location TEXT
  start_ts TIMESTAMP
  end_ts TIMESTAMP
  all_day BOOLEAN
  attendees JSONB        -- [{name,email,response}]
  status TEXT            -- confirmed | tentative | cancelled
  source TEXT            -- google_calendar | outlook
  synced_at TIMESTAMP
  UNIQUE(user_id, source, external_id)
```

Conflict detection is deterministic overlap on `[start_ts, end_ts)` (ADR §6 "Conflict = pre-filter + loop for resolution").

---

## 4. Finance

Backs `logistics` (M1), the Finance workflow, the Risk engine's `low_balance_vs_bill` signal (M3), and is the **observed state** the L0 transfer action reasons over (the action itself is gated, §10.3 — these tables are read-only reality).

```sql
finance_accounts
  id UUID PK
  user_id UUID
  integration_id UUID
  external_id TEXT
  account_type TEXT       -- current | savings | credit_card
  institution TEXT        -- HDFC
  masked_number TEXT
  currency TEXT
  balance NUMERIC
  balance_synced_at TIMESTAMP
  UNIQUE(user_id, source, external_id)

bills
  id UUID PK
  user_id UUID
  account_id UUID NULL
  biller TEXT             -- AWS, electric, spotify
  amount NUMERIC
  currency TEXT
  due_date TIMESTAMP
  auto_pay BOOLEAN
  status TEXT             -- upcoming | paid | overdue
  source TEXT
  synced_at TIMESTAMP

transactions
  id UUID PK
  user_id UUID
  account_id UUID
  external_id TEXT
  amount NUMERIC
  currency TEXT
  direction TEXT          -- debit | credit
  merchant TEXT
  category TEXT
  occurred_at TIMESTAMP
  UNIQUE(user_id, account_id, external_id)
```

`transactions` also feeds **subscription detection** (§5) and spending-pattern insights. The runner's M3 diff is: `min(account.balance for fundable accounts) < bill.amount` within the bill's lead window → emit `low_balance_vs_bill`.

---

## 5. Subscriptions

Backs `logistics` (M1), the Subscription workflow, renewal watches (M8). Subscriptions are often **detected**, not API-given (recurring transactions, email receipts) — `detected_via` records provenance.

```sql
subscriptions
  id UUID PK
  user_id UUID
  integration_id UUID NULL
  service_name TEXT       -- Spotify
  amount NUMERIC
  currency TEXT
  billing_cycle TEXT      -- monthly | annual
  renewal_date TIMESTAMP
  status TEXT             -- active | cancelled | paused
  category TEXT           -- music | streaming | saas
  detected_via TEXT       -- integration | transaction | email_receipt
  synced_at TIMESTAMP

subscription_usage
  id UUID PK
  subscription_id UUID
  period_start TIMESTAMP
  period_end TIMESTAMP
  usage_count INTEGER     -- M8 "used 2x this month"
  usage_metric TEXT       -- plays | logins | hours
  synced_at TIMESTAMP
```

**Integration caveat:** "used 2x this month" needs listening history (Spotify recently-played); **cancelling** Spotify has no public API — the cancel action is likely email-/assisted-flow and is L1 (cards_and_delivery, §10.3). Flag for the integration layer; the schema is ready regardless.

---

## 6. Health & Nutrition

Backs the Health workflow and the Goal engine's health goals (M4). Calorie math needs a daily tally and a target.

```sql
health_logs
  id UUID PK
  user_id UUID
  log_type TEXT           -- meal | workout | sleep | weight
  occurred_at TIMESTAMP
  payload JSONB           -- meal: {items:[...], calories, macros}
  source TEXT             -- user | apple_health | google_fit
  created_at TIMESTAMP

nutrition_daily            -- materialized per-day aggregate (like metric_rollup)
  user_id UUID
  date DATE
  calories_consumed INTEGER
  calorie_target INTEGER   -- from goals
  macros JSONB
  computed_at TIMESTAMP
  PRIMARY KEY(user_id, date)
```

`nutrition_daily` gives "~1,840 so far, ~600 left" instantly and "day 3 over goal" by scanning the last N days. **Calorie estimation** for free-text meals ("biryani and sweet lassi") happens **inside the meal-logging loop turn** (M4 is a user turn → one loop) via a nutrition-lookup tool — not a separate engine, so it stays in the ADR budget. The `nutrition_daily` recompute is deterministic (sum of the day's meal logs).

---

## 7. Contacts (raw → relationships)

`relationships` (existing) is the **curated** important-people model. Deriving it needs raw contacts + interaction signal. `onboarding.md` computes `relationships.importance` / `interaction_frequency` from these + comms volume.

```sql
contacts
  id UUID PK
  user_id UUID
  integration_id UUID
  external_id TEXT
  name TEXT
  emails JSONB
  phones JSONB
  source TEXT             -- gmail | google_contacts | derived_from_email
  synced_at TIMESTAMP
  UNIQUE(user_id, source, external_id)
```

Interaction history is **derived** (email/message/calendar volume), not a separate table — computed during onboarding and continuously, written onto `relationships.interaction_frequency` / `last_interaction`.

---

## 8. Travel (lean)

Backs the Travel workflow and flight watches (the screenshot delay moment). The demo's M6 cab is a *ride action* (executed + audited in `actions`), not stored travel — so this table is light, for monitored trips only.

```sql
travel_items
  id UUID PK
  user_id UUID
  integration_id UUID NULL
  item_type TEXT          -- flight | hotel | ride
  external_id TEXT
  title TEXT              -- "BOM→NRT NH otto"
  start_ts TIMESTAMP
  end_ts TIMESTAMP NULL
  status TEXT             -- booked | delayed | cancelled | completed
  details JSONB           -- gate, seat, pnr, pickup plan
  source TEXT
  synced_at TIMESTAMP
```

---

## 9. Dashboard mapping

Which table feeds which dashboard section (Dashboard engine = deterministic projection, ADR §6):

| Section | Source |
|---|---|
| **watching** | `watches` (active) |
| **scheduled** | `calendar_events` (upcoming) + `scheduled_tasks` |
| **logistics** | `bills` (upcoming) + `subscriptions` (renewing) + `travel_items` |
| **holding** | open `commitments` + `pending` cards + active `watches` |
| **done** | terminal `actions` today |

This makes M1's dense dashboard a set of deterministic projections over these tables — no LLM to render the dashboard.

---

## 10. What is NOT cached here

Retrieved on demand via `read_*` tools, never duplicated into a table: full email bodies/threads, full bank statements, document contents, message histories beyond the comms log (`messages`, in `cards_and_delivery.md`). The line: **a fact you diff or rank → table; a blob you occasionally read → source + tool.**

---

## 11. Deterministic vs LLM

Every table here is sync-written (deterministic) and query-read. The only LLM that ever touches this layer is the **loop turn** that logs a meal (calorie estimate) or the bounded **onboarding extraction passes** (`onboarding.md`) — both already budgeted. The runner's diffs, the dashboard projection, and all `recall_*` reads are LLM-free.

---

## 12. Out of scope / open

- **Sync mechanics** (webhook vs poll per source, cursors) live in `onboarding.md` §`integration_syncs` and the integration layer.
- **Nutrition data source** and **Spotify cancel/usage** are integration gaps flagged above; schema is ready.
- **Encryption-at-rest / PII** for finance + contacts joins the still-open token-vault/security decision.
