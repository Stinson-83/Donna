import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import DemoRoot from './demo/DemoRoot.jsx'
import { bootstrapFromMagicLink } from './identity.js'
import './index.css'

// Demo mode: ?scene=shot_N freezes one storyboard moment for OBS capture. Sealed
// behind the URL flag — the real app is mounted otherwise, untouched.
const Root = new URLSearchParams(window.location.search).has('scene') ? DemoRoot : App

function mount() {
  createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <Root />
    </React.StrictMode>,
  )
}

// If Donna's dashboard link left a magic token in the URL (#t=), exchange it for
// a session before mounting so the first render is already authed. Never blocks
// on failure — it falls through to whatever identity exists.
bootstrapFromMagicLink().finally(mount)
