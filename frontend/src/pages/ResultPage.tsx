import { useEffect, useState } from 'react'
import { api, type Result } from '../api'
import { Chain } from '../components/ui'
import { isRare } from '../format'
import { navigate } from '../router'

export function ResultPage({ id }: { id: string }) {
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.result(id).then(setResult, (e) => setError(e.message))
  }, [id])

  if (error) return <main className="page"><p className="error">{error}</p></main>
  if (!result) return <main className="page"><p className="muted">Loading…</p></main>

  const { game, score } = result
  const won = game.status === 'won'
  const rareLinks = game.hops.filter((h) => isRare(h.rarity)).length

  async function copy() {
    try {
      await navigator.clipboard.writeText(result!.share_text ?? '')
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }

  async function playAgain() {
    try {
      const g = await api.newGame()
      navigate({ page: 'game', id: g.id })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start a game.')
    }
  }

  return (
    <main className="page">
      <div className="page-main">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end', gap: 24 }}>
          <div className="stack" style={{ gap: 6 }}>
            <div className="eyebrow" style={{ color: won ? 'var(--lime)' : 'var(--gold)' }}>
              {won ? 'Full time' : 'Gave up'} · Practice puzzle
            </div>
            <h1 style={{ fontSize: 'clamp(36px, 5vw, 60px)', lineHeight: 0.95 }}>
              {game.start.name} → {game.end.name}
              <br />
              {won ? (
                <span style={{ color: 'var(--gold)' }}>in {game.hops.length} hops</span>
              ) : (
                <span style={{ color: 'var(--gold)' }}>not linked</span>
              )}{' '}
              <span className="dim" style={{ fontSize: '0.6em' }}>· par {game.par}</span>
            </h1>
          </div>
          {score && (
            <div className="score-circle" aria-label={`${score.total.toFixed(1)} points`}>
              <div className="num">{score.total.toFixed(1)}</div>
              <div className="eyebrow">points</div>
            </div>
          )}
        </div>

        <section className="stack">
          <div className="row" style={{ alignItems: 'baseline', gap: 10 }}>
            <h2 className="section">Your route</h2>
            <span className="muted small">{game.hops.length} hops</span>
          </div>
          <div className="panel">
            {game.hops.length ? (
              <Chain start={game.start} hops={game.hops} endId={game.end.id} />
            ) : (
              <p className="muted">No links made.</p>
            )}
          </div>
        </section>

        <section className="stack">
          <div className="row" style={{ alignItems: 'baseline', gap: 10 }}>
            <h2 className="section">Shortest route in our data</h2>
            <span className="muted small">{result.optimal_path.length} hops</span>
          </div>
          <div className="panel dashed">
            <Chain start={game.start} hops={result.optimal_path} ghost />
          </div>
          <p className="dim small">
            Shortest within careers {result.data_range}, top-5 European leagues, players rated 70+. A real-world route
            may be shorter.
          </p>
        </section>

        <div className="row">
          <button className="btn" onClick={playAgain}>Play another</button>
          <a href="#/" className="btn-link">Your games</a>
        </div>
      </div>

      <aside className="rail">
        <div className="panel stack" style={{ gap: 14 }}>
          <div className="panel-title">Score breakdown</div>
          {score ? (
            <>
              <div className="stack" style={{ gap: 6 }}>
                <div className="kv">
                  <span className="muted">Efficiency · best {score.optimal_hops} of your {score.hops}</span>
                  <span className="v">{score.efficiency_points.toFixed(1)} / {score.efficiency_weight * 100}</span>
                </div>
                <div className="bar"><div style={{ width: `${score.efficiency * 100}%` }} /></div>
              </div>
              <div className="stack" style={{ gap: 6 }}>
                <div className="kv">
                  <span className="muted">
                    Rarity · {rareLinks ? `${rareLinks} rare link${rareLinks > 1 ? 's' : ''}` : `avg ${(score.rarity * 100).toFixed(0)}%`}
                  </span>
                  <span className="v">{score.rarity_points.toFixed(1)} / {score.rarity_weight * 100}</span>
                </div>
                <div className="bar gold"><div style={{ width: `${score.rarity * 100}%` }} /></div>
              </div>
              <div className="divider" />
              <div className="kv" style={{ alignItems: 'baseline' }}>
                <span className="muted">Total</span>
                <span style={{ font: '800 30px var(--display)' }}>{score.total.toFixed(1)}</span>
              </div>
            </>
          ) : (
            <p className="muted">No score when you give up — the shortest route is on the left.</p>
          )}
        </div>

        {result.share_text && (
          <div className="panel deep stack">
            <div className="panel-title">Share text</div>
            <pre className="share">{result.share_text}</pre>
            <button type="button" className="btn-ghost" onClick={copy}>{copied ? 'Copied!' : 'Copy to clipboard'}</button>
          </div>
        )}
      </aside>
    </main>
  )
}
