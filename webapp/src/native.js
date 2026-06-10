// Native bridge — no-ops on the web, engages inside the Capacitor app.
// Hides the splash once React is up, and keeps the status bar in sync with the
// Morning / Night theme. All calls are guarded + dynamically imported so the
// web build is unaffected.
import { Capacitor } from '@capacitor/core'

export const isNative = Capacitor.isNativePlatform()

const BG = { morning: '#f6f2ec', night: '#0e0d0c' }

export async function initNative(night) {
  if (!isNative) return
  try {
    const { SplashScreen } = await import('@capacitor/splash-screen')
    await applyTheme(night)
    await SplashScreen.hide()
  } catch {
    /* plugin unavailable — ignore */
  }
}

export async function applyTheme(night) {
  if (!isNative) return
  try {
    const { StatusBar, Style } = await import('@capacitor/status-bar')
    // Style.Light → dark text (for our light Morning bg); Style.Dark → light text (Night).
    await StatusBar.setStyle({ style: night ? Style.Dark : Style.Light })
    if (Capacitor.getPlatform() === 'android') {
      await StatusBar.setBackgroundColor({ color: night ? BG.night : BG.morning })
    }
  } catch {
    /* ignore */
  }
}
