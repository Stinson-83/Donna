# Surface Projections v1.0

One `DonnaCard` payload renders on every surface. Projections are deterministic
rules applied by the backend (not the model, not the client) so a card never has
to be authored twice. `card_id` + `action_id` stay stable across surfaces, so an
Approve tapped on the lock screen resolves the same card shown in Live.

## Projection table

| Surface | What renders | Rule |
|---|---|---|
| **Live (full)** | every block | the source of truth |
| **Dashboard hero** | header + body + delta + actions | drop key_values/steps/graph detail; keep counts in section label |
| **Push notification** | title = app name; body = `body.text` (fallback: header.label + delta); buttons = `actions` (max 2) | strip markdown bold to plain; body ≤ 140 chars, truncate at clause |
| **Island · expanded** | header.label + body + delta + actions | long-press surface; espresso native styling |
| **Island · compact** | `d` mark + one datum | datum priority: countdown (`expires_at`) → delta.to → header.label |
| **Live Activity** | header.ref + delta + footer | only for cards with `expires_at` or ongoing trackers |
| **History (after resolve)** | one system line | "✓ {resolution summary}" — the card itself never re-renders in History |

## Resolution flow

1. User taps an action anywhere → backend resolves `action_id`.
2. Card flips to `theme: "settled"` in Live; Dashboard hero slot releases;
   notification/Live Activity dismissed; History gains a system line.
3. If `expires_at` passes unactioned → card sinks to settled with footer
   "expired · she'll re-ask if it matters" and Donna decides whether to re-raise.

## Notification copy rules

Donna voice applies (lowercase, no em dashes, one question max). Button labels
are verbs ≤ 14 chars. Never two notifications for one card_id; update in place.
