import { AuthProvider, useAuth } from './auth'
import { TopBar } from './components/TopBar'
import { GamePage } from './pages/GamePage'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { ResultPage } from './pages/ResultPage'
import { useRoute } from './router'

function Shell() {
  const { user, loading } = useAuth()
  const route = useRoute()

  if (loading) return <main className="page muted">Loading…</main>
  if (!user) return <Login />

  return (
    <>
      <TopBar />
      {route.page === 'home' && <Home />}
      {route.page === 'game' && <GamePage key={route.id} id={route.id} />}
      {route.page === 'result' && <ResultPage key={route.id} id={route.id} />}
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  )
}
