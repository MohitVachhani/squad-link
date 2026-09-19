import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Warm up the API (a serverless cold start loads the player graph) while the user is still on the sign-in screen.
// Fire-and-forget: nothing waits on it and failures don't matter.
fetch('/health').catch(() => {})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
