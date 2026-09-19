import { useEffect, useState } from 'react'
import { api, type GameSummary } from '../api'
import { navigate } from '../router'

export function Home() {
  const [games, setGames] = useState<GameSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    api.games().then(setGames, (e) => setError(e.message))
  }, [])

  async function start() {
    setStarting(true)
    setError(null)
    try {
      const g = await api.newGame()
      navigate({ page: 'game', id: g.id })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start a game.')
      setStarting(false)
    }
  }

  return (
    <main className="page">
      <div className="page-main">
        <div className="panel deep stack" style={{ gap: 16 }}>
          <div className="eyebrow" style={{ color: 'var(--lime)' }}>Practice puzzle</div>
          <h1 style={{ fontSize: 'clamp(36px, 5vw, 56px)', lineHeight: 0.95 }}>
            Two players. <span style={{ color: 'var(--lime)' }}>Find the link.</span>
          </h1>
          <p className="muted" style={{ fontSize: 17, maxWidth: 560 }}>
            You get a start player and a target. Name a teammate of the current player and the club they shared, hop
            by hop, until you reach the target.
          </p>
          <div>
            <button className="btn" onClick={start} disabled={starting}>
              {starting ? 'Starting…' : 'Start a random puzzle'}
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </div>

        <section className="stack">
          <h2 className="section">Your games</h2>
          {games === null && !error && <p className="muted">Loading…</p>}
          {games?.length === 0 && <p className="muted">No games yet — start one above.</p>}
          {games && games.length > 0 && (
            <div className="panel table-wrap" style={{ padding: '8px 12px' }}>
              <table>
                <thead>
                  <tr><th>Puzzle</th><th>Hops / par</th><th>Score</th><th></th></tr>
                </thead>
                <tbody>
                  {games.map((g) => (
                    <tr key={g.id}>
                      <td>{g.start.name} → {g.end.name}</td>
                      <td className="num">{g.hops} / {g.par}</td>
                      <td className="num">
                        {g.status === 'won' ? g.score?.toFixed(1) : g.status === 'abandoned' ? <span className="dim">gave up</span> : <span className="dim">in play</span>}
                      </td>
                      <td>
                        <a href={g.status === 'in_progress' ? `#/game/${g.id}` : `#/result/${g.id}`}>
                          {g.status === 'in_progress' ? 'Continue' : 'Result'}
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
