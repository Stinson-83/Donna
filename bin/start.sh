#!/bin/sh
# Role-switching entrypoint for the Donna container image.
#
# Railway (and anywhere else this image runs) selects the role via the
# DONNA_PROCESS_ROLE env var. This is what lets the same image power both
# the public API (webhook + dashboard backend) and the dedicated reminders
# worker that fires DonnaSchedule rows on time.
#
#   DONNA_PROCESS_ROLE=api        → uvicorn api.main:app  (default)
#   DONNA_PROCESS_ROLE=reminders  → python scripts/run_schedule_worker.py
#   DONNA_PROCESS_ROLE=proactive  → python scripts/run_proactive_runner.py
#
# Reminders need only DB + WhatsApp + the BRAIN-free templated send path.
# Proactive runs deterministic checks (finance, ...) and surfaces cards via the
# BRAIN loop. Both MUST NOT be co-located with the API — the API is busy with
# inbound webhooks and proactive turns and used to drop fires under load.

set -e

ROLE="${DONNA_PROCESS_ROLE:-api}"

case "$ROLE" in
    api)
        exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
        ;;
    reminders)
        exec python scripts/run_schedule_worker.py \
            --poll "${DONNA_REMINDERS_POLL_S:-5.0}" \
            --batch "${DONNA_REMINDERS_BATCH:-25}"
        ;;
    proactive)
        exec python scripts/run_proactive_runner.py \
            --poll "${DONNA_PROACTIVE_POLL_S:-300.0}"
        ;;
    *)
        echo "bin/start.sh: unknown DONNA_PROCESS_ROLE='$ROLE' (expected 'api', 'reminders', or 'proactive')" >&2
        exit 64
        ;;
esac
