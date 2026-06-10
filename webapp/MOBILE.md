# Donna — Mobile (Capacitor) Guide

The existing React/Vite app is wrapped with **Capacitor 8** into a native mobile
app. Everything here is doable **from Linux** — Android Emulator for testing,
APKs for distribution. iOS is fully scaffolded and ready for a Mac later (no
Xcode/macOS needed now).

- App name: **Donna** · Bundle ID: **ai.donna.app**
- Web build dir: `dist/` (Vite, `base: './'`) · Capacitor `webDir: dist`
- Native projects: `android/` (Gradle) and `ios/` (Swift Package Manager)

---

## 0. One-time toolchain (Linux)

| Tool | Version | Notes |
|------|---------|-------|
| Node | 18+ (have 22) | ✅ |
| **JDK** | **21** | Capacitor 8 / AGP 8.13 need JDK 17+, **21 recommended**. You currently have JDK 11 — upgrade. Easiest: use **Android Studio's bundled JDK 21** (no separate install). |
| Android Studio | Ladybug (2024.2)+ | Provides the SDK, emulator, and a bundled JDK 21. |
| Android SDK | Platform **36**, Build-Tools 35+, Platform-Tools | Installed via Android Studio SDK Manager. |
| Gradle | 8.14.3 | Auto-downloaded by `android/gradlew` — no manual install. |

Install Android Studio (Linux): download from developer.android.com/studio, unzip,
run `bin/studio.sh`. On first launch it installs the SDK + an emulator system image.

Set these in `~/.bashrc` (adjust path to your SDK):
```bash
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin"
# Use Android Studio's JDK 21 for Gradle (so you don't need a system JDK 21):
export JAVA_HOME="$HOME/android-studio/jbr"   # path where you unzipped Android Studio
```

> The repo needs `android/local.properties` pointing at the SDK. Android Studio
> writes it automatically on first open; or create it manually:
> `echo "sdk.dir=$ANDROID_HOME" > android/local.properties`

---

## 1. Environment configuration

No hardcoded URLs. Vite mode-based env files (`webapp/`):

| File | Used by | `VITE_API_BASE` | `VITE_MOCK` |
|------|---------|-----------------|------------|
| `.env.development` | `npm run dev` | `http://localhost:8000` | `1` |
| `.env.production` | `npm run build` | `https://api.donna.app` | `0` |
| `.env.mobile` | `npm run build:mobile` | `http://10.0.2.2:8000` | `1` |

- **`10.0.2.2`** is how the Android emulator reaches the **host** machine
  (its own `localhost` is the emulator). Set `VITE_MOCK=0` in `.env.mobile` and
  run the backend on the host to use the real cognition layer from the emulator.
- Secrets / per-machine overrides go in `.env.*.local` (gitignored).

---

## 2. Daily workflow (Linux)

```bash
cd webapp

# pure web dev (browser), mock data, no backend
npm run dev

# build the mobile web bundle + push into the native projects
npm run mobile:sync

# open Android Studio on the project (needs Studio installed)
npm run android:open

# build + install + launch on a running emulator/device
npm run android:run
```

All scripts (in `package.json`):

| Script | Does |
|--------|------|
| `npm run build:mobile` | `vite build --mode mobile` |
| `npm run mobile:build` | build:mobile + `cap copy` (web assets only) |
| `npm run mobile:sync` | build:mobile + `cap sync` (assets + native plugins) |
| `npm run android:open` | `cap open android` (launch Android Studio) |
| `npm run android:run` | sync + `cap run android` (pick emulator/device) |
| `npm run android:apk` | sync + `gradlew assembleDebug` → debug APK |
| `npm run android:apk:release` | sync + `gradlew assembleRelease` |
| `npm run assets` | regenerate icons/splash from `assets/logo*.png` |
| `npm run ios:sync` / `ios:open` | for use on a Mac |
| `npm run release` | sync + `gradlew assembleRelease` |

---

## 3. Android Emulator (Pixel 9 Pro)

1. Android Studio → **More Actions → Virtual Device Manager → Create Device**.
2. Pick **Pixel 9 Pro** → system image **API 36** (download if needed) → Finish.
3. Start the emulator (▶ in Device Manager), or headless from the terminal:
   ```bash
   emulator -list-avds
   emulator -avd Pixel_9_Pro &
   adb devices            # confirm it shows up
   ```
4. From `webapp/`: `npm run android:run` → builds, installs, and launches Donna
   on the emulator. (Or `npm run android:open` and hit ▶ Run in Studio.)

The app runs standalone in mock mode. For live data: run the backend on the host
(`uvicorn api.main:app --port 8000`, with `python -m backend.cognition.seed`),
set `.env.mobile` `VITE_MOCK=0`, `npm run mobile:sync`, re-run.

---

## 4. APK generation

```bash
# Debug APK (installable, unsigned-for-store, fine for testing/sharing)
npm run android:apk
# → android/app/build/outputs/apk/debug/app-debug.apk
adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

### Release (signed) APK
1. Create a keystore (once):
   ```bash
   keytool -genkey -v -keystore donna-release.keystore \
     -alias donna -keyalg RSA -keysize 2048 -validity 10000
   ```
   Keep `donna-release.keystore` and the passwords safe and OUT of git.
2. Create `android/keystore.properties` (gitignored):
   ```properties
   storeFile=../donna-release.keystore
   storePassword=YOUR_STORE_PASSWORD
   keyAlias=donna
   keyPassword=YOUR_KEY_PASSWORD
   ```
3. Wire signing in `android/app/build.gradle` (inside `android { }`):
   ```gradle
   def kp = new Properties()
   def kpf = rootProject.file("keystore.properties")
   if (kpf.exists()) { kp.load(new FileInputStream(kpf)) }
   signingConfigs {
       release {
           if (kpf.exists()) {
               storeFile file(kp['storeFile']); storePassword kp['storePassword']
               keyAlias kp['keyAlias']; keyPassword kp['keyPassword']
           }
       }
   }
   buildTypes { release { signingConfig signingConfigs.release } }
   ```
4. Build:
   ```bash
   npm run android:apk:release
   # → android/app/build/outputs/apk/release/app-release.apk
   ```
   For Play Store, build an **AAB** instead: `cd android && ./gradlew bundleRelease`
   → `android/app/build/outputs/bundle/release/app-release.aab`.

---

## 5. iOS — when a Mac is available (no work needed now)

The `ios/` project (Swift Package Manager, Capacitor 8) is already generated with
the bundle ID, icons, splash, and plugins. On a Mac with Xcode:

```bash
git clone <repo> && cd webapp
npm install
npm run build:mobile        # or: npm run build (production)
npx cap sync ios
npx cap open ios            # opens Xcode
```
Then in Xcode: set your Team (Signing & Capabilities), pick a device/simulator,
Run. For TestFlight: Product → Archive → Distribute App → App Store Connect.
(Bundle ID `ai.donna.app` must exist in your Apple Developer account.)

---

## 6. What makes it feel native

- **Safe areas:** `viewport-fit=cover` + `env(safe-area-inset-*)` via `.safe-top`
  / `.safe-bottom` / `.safe-x` on the frame and tab bar (notch, status bar,
  gesture nav). Inert in the browser, engaged on device.
- **Splash:** `@capacitor/splash-screen`, Morning canvas `#f6f2ec`, hidden by
  `src/native.js` once React mounts.
- **Status bar:** `@capacitor/status-bar` synced to Morning/Night in `native.js`.
- **Keyboard:** `@capacitor/keyboard` (`resize: native`) so the chat composer
  stays above the keyboard.
- **Scrolling:** momentum scroll on `.scroll`/`.thread`; `overscroll-behavior:
  none` kills rubber-band / pull-to-refresh.
- **Icons/splash:** generated from `assets/logo.png` (+ dark) via `npm run assets`.

---

## 7. Troubleshooting

- **`SDK location not found`** → create `android/local.properties` with `sdk.dir=...`
  (Android Studio does this automatically on first open).
- **`Unsupported class file major version` / Gradle JDK error** → Gradle is using
  JDK 11. Point `JAVA_HOME` at JDK 21 (or Android Studio: Settings → Build →
  Build Tools → Gradle → Gradle JDK → 21).
- **App can't reach the backend on the emulator** → use `http://10.0.2.2:8000`,
  not `localhost`; ensure the backend is running on the host; `allowMixedContent`
  is already enabled for http during testing.
- **White screen** → confirm `webDir: dist`, `base: './'` in `vite.config.js`,
  and that you ran `npm run mobile:sync` after the last web change.
