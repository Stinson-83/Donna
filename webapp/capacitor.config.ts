import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'ai.donna.app',
  appName: 'Donna',
  webDir: 'dist',
  // Morning canvas — the launch background before React mounts.
  backgroundColor: '#f6f2ec',
  android: {
    // Allow http to the dev/staging backend during testing. Tighten for store builds.
    allowMixedContent: true,
  },
  server: {
    androidScheme: 'https',
    // For live-reload on the emulator, run `npm run dev -- --host` and set:
    //   CAP_SERVER_URL=http://10.0.2.2:5173 npx cap run android
    // (read below), otherwise the built dist/ is bundled.
    ...(process.env.CAP_SERVER_URL
      ? { url: process.env.CAP_SERVER_URL, cleartext: true }
      : {}),
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      launchAutoHide: true,
      backgroundColor: '#f6f2ec',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false,
      splashFullScreen: true,
      splashImmersive: true,
    },
    Keyboard: {
      // Resize the webview when the keyboard opens so the chat composer stays visible.
      resize: 'native' as any,
      resizeOnFullScreen: true,
    },
  },
}

export default config
