// Demo-mode store. A single module-level slot holding the active scene. The real
// mock layer (cards.js) consults activeFixture(); it returns null unless a scene
// is installed, so the normal app is completely unaffected.
//
// Scene changes are a full page navigation (location.search), so every jump is an
// idempotent reset — no take inherits another's state. That is the whole point.

let _scene = null

export function installScene(scene) { _scene = scene }
export function activeScene() { return _scene }
export function activeFixture() { return _scene?.data ?? null }

// Navigate to a scene id (full reload -> deterministic reset).
export function goScene(id) {
  const u = new URL(window.location.href)
  u.searchParams.set('scene', id)
  window.location.href = u.toString()
}
