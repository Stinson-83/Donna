// Push notifications — native only. Registers with FCM, uploads the device
// token under the CURRENT identity (so pings reach the right person), and routes
// a notification tap into chat. No-ops on web and degrades silently if the
// plugin or Firebase isn't present, so the build/runtime are never blocked.
import { Capacitor } from '@capacitor/core'
import { getUserId } from './identity.js'
import { API_BASE } from './api.js'

let inflight = false

async function uploadToken(token) {
  if (!token) return
  try {
    await fetch(`${API_BASE}/push/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user: getUserId(), token, platform: Capacitor.getPlatform() }),
    })
  } catch {
    /* offline — the next launch re-registers */
  }
}

// Safe to call again on identity change: it re-registers and re-keys the token
// to the new user server-side.
export async function initPush(onOpen) {
  if (inflight || !Capacitor.isNativePlatform()) return
  inflight = true
  let PushNotifications
  try {
    ;({ PushNotifications } = await import('@capacitor/push-notifications'))
  } catch {
    inflight = false
    return // plugin not installed in this build
  }
  try {
    let perm = await PushNotifications.checkPermissions()
    if (perm.receive === 'prompt' || perm.receive === 'prompt-with-rationale') {
      perm = await PushNotifications.requestPermissions()
    }
    if (perm.receive !== 'granted') return

    await PushNotifications.removeAllListeners()
    await PushNotifications.addListener('registration', (t) => uploadToken(t.value))
    await PushNotifications.addListener('registrationError', (e) =>
      console.warn('push: registration error', e),
    )
    // Tap on a notification (app backgrounded or cold) -> open chat.
    await PushNotifications.addListener('pushNotificationActionPerformed', () => onOpen?.())
    await PushNotifications.register()
  } catch (e) {
    console.warn('push: init failed (firebase not configured?)', e)
  } finally {
    inflight = false
  }
}
