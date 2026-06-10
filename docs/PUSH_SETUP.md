# Push notifications setup (Firebase Cloud Messaging)

Push is **fully wired but config-gated**: the backend runs and the Android APK
builds today without any of this. Push starts working once you add a Firebase
project. Three steps — one in the Firebase console, one in the app, one on the
server.

## What's already done (no action needed)

- `@capacitor/push-notifications` is installed and wired into the Android project.
- The app (`webapp/src/push.js`) registers on launch, uploads its FCM token to
  `POST /push/register` under the current identity, and routes a notification
  tap into the Chat tab.
- The backend stores device tokens (`device_tokens` table, auto-created),
  exposes `POST /push/register` and `POST /push/test`, and pushes Donna's
  proactive bursts to the app via `backend/integrations/push.py`.
- Android Gradle already applies the `google-services` plugin **only if**
  `google-services.json` is present (Capacitor scaffolds this), so the build
  never breaks before Firebase is configured.

## Step 1 — Create a Firebase project (console)

1. https://console.firebase.google.com → **Add project** (or reuse one).
2. **Project settings → General → Your apps → Add app → Android.**
   - Android package name: **`ai.donna.app`** (must match `capacitor.config.ts` `appId`).
   - Download **`google-services.json`**.
3. Put it at: `webapp/android/app/google-services.json`.

That's the entire client side. Rebuild the APK (`npm run android:apk` in
`webapp/`) and the device will start registering for push.

## Step 2 — Service account for the backend (console)

1. **Project settings → Service accounts → Generate new private key.** This
   downloads a JSON key.
2. Give it to the backend as `FCM_SERVICE_ACCOUNT_JSON`:
   - **Railway:** paste the whole JSON as the value of the env var
     `FCM_SERVICE_ACCOUNT_JSON` (one line is fine; it's valid JSON).
   - **Local:** either paste it inline in `.env`, or save the file somewhere and
     set `FCM_SERVICE_ACCOUNT_JSON=/abs/path/to/key.json`.
3. `FCM_PROJECT_ID` is optional — it defaults to the `proai.donna.appject_id` inside the key.

Restart the backend. `is_configured()` is now true.

## Step 3 — Verify end to end

1. Install the rebuilt APK, open the app, accept the notification permission.
   (On first launch you should see `POST /push/register` hit the backend.)
2. Fire a test ping (replace `<your-app-id>` with the value the app uses — for
   the demo identity it's `demo-aarav`; for a claimed profile it's the slug shown
   after onboarding):

   ```bash
   curl -X POST https://<your-backend>/push/test \
     -H 'Content-Type: application/json' \
     -d '{"user":"<your-app-id>","body":"hello from donna"}'
   ```

   - `{"ok": true, "configured": true, "delivered": 1}` → it works.
   - `{"configured": false, ...}` → the service account isn't set on the server.
   - `{"ok": false, "configured": true, "delivered": 0}` → server is fine but no
     device is registered for that id (open the app and grant permission first).

## How proactive push happens in normal use

When a notable email arrives, the Composio webhook runs Donna's brain in
`mode="proactive"`. If she decides to surface it (doesn't `stay_silent`), the
same outbound bubbles are pushed to the user's devices via `notify_outbound`.
Tapping the notification opens Chat. No extra wiring — it rides the existing
proactive path in `backend/integrations/proactive_email_trigger.py`.

## iOS (later, on a Mac)

The same `@capacitor/push-notifications` plugin and backend cover iOS. You'll
additionally need an APNs key uploaded to Firebase (Project settings → Cloud
Messaging → Apple app config) and the Push Notifications capability enabled in
Xcode. The backend code is already platform-agnostic (the `apns` block is set in
every FCM message).
