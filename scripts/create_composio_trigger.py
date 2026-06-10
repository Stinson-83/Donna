"""One-off: create the Gmail new-message trigger for a connected Composio user.

The Composio dashboard creates triggers only via the SDK, so run this once after
connecting a Gmail account. It also prints the SDK version + the real
`triggers` API surface, so we can fix the in-app auto-subscribe to match.

Usage:
    pip install composio                       # the new Composio SDK
    export COMPOSIO_API_KEY=...                 # (or rely on .env)
    python scripts/create_composio_trigger.py <user_id>

<user_id> = the id you connected Gmail under (the same `user_id` you use in the
app / passed to Composio's OAuth).
"""
from __future__ import annotations

import os
import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

GMAIL_TRIGGER_SLUG = "GMAIL_NEW_GMAIL_MESSAGE"


def main() -> None:
    user_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DONNA_USER_ID", "")
    if not user_id:
        print("usage: python scripts/create_composio_trigger.py <user_id>")
        sys.exit(2)

    api_key = os.environ.get("COMPOSIO_API_KEY", "")
    if not api_key:
        print("COMPOSIO_API_KEY not set (env or .env)")
        sys.exit(2)

    try:
        import composio

        print("composio version:", getattr(composio, "__version__", "?"))
        from composio import Composio
    except ImportError:
        print("The new Composio SDK isn't installed. Run:  pip install composio")
        sys.exit(1)

    client = Composio(api_key=api_key)

    # 1. Discover the required config for this trigger.
    try:
        ttype = client.triggers.get_type(GMAIL_TRIGGER_SLUG)
        print(f"\n{GMAIL_TRIGGER_SLUG} required config:", getattr(ttype, "config", "?"))
    except Exception as e:
        print("get_type() failed:", type(e).__name__, e)

    # 2. Create the trigger. Most config-less triggers accept {}; if Gmail
    #    requires fields, the error will name them (see the config printed above).
    print(f"\nCreating {GMAIL_TRIGGER_SLUG} for user_id={user_id!r} ...")
    for cfg in ({}, {"interval": 1, "labelIds": "INBOX", "userId": "me"}):
        try:
            trigger = client.triggers.create(
                slug=GMAIL_TRIGGER_SLUG,
                user_id=user_id,
                trigger_config=cfg,
            )
            print(f"CREATED ✅  trigger_id = {getattr(trigger, 'trigger_id', trigger)}  (config={cfg})")
            print("Events will now be delivered to your project webhook URL.")
            return
        except Exception as e:
            print(f"create(config={cfg}) failed:", type(e).__name__, str(e)[:200])
    print("\n→ paste this whole output back and we'll set the exact trigger_config.")


if __name__ == "__main__":
    main()
