import { useEffect, useState, type FormEvent } from 'react'
import { api, type Club, type Game, type Player } from '../api'
import { ClubPicker, PlayerPicker } from '../components/pickers'
import { Chain } from '../components/ui'
import { isRare, playerSub } from '../format'
import { navigate } from '../router'

function Matchup({ game }: { game: Game }) {
  const used = game.hops.length
  const dots = Array.from({ length: Math.max(game.par, used) }, (_, i) =>
    i < used ? (i < game.par ? 'on' : 'over') : '',
  )
  const card = (p: Player, label: string, target: boolean) => (
    <div className={`pcard ${target ? 'target' : ''}`}>
      <div className="corner">{label}</div>
      <div className="pname">{p.name}</div>
      <div className="pnation">{p.nation}</div>
      <div className="pmeta">{playerSub(p).split(' · ').slice(1).join(' · ')}</div>
    </div>
  )
  return (
    <div className="matchup">
      {card(game.start, 'From', false)}
      <div className="par">
        <div className="eyebrow">Par</div>
        <div className="big">{game.par}</div>
        <div className="muted small">hops · you’ve used {used}</div>
        <div className="par-dots" aria-hidden="true">
          {dots.map((d, i) => <span key={i} className={d} />)}
        </div>
      </div>
      {card(game.end, 'To', true)}
    </div>
  )
}

function LiveScore({ game }: { game: Game }) {
  const rarities = game.hops.map((h) => h.rarity)
  const avg = rarities.length ? rarities.reduce((a, b) => a + b, 0) / rarities.length : 0
  const level = !rarities.length ? '—' : avg >= 0.6 ? 'High' : avg >= 0.3 ? 'Medium' : 'Low'
  return (
    <div className="panel stack" style={{ gap: 14 }}>
      <div className="panel-title">Live score</div>
      <div className="kv"><span className="muted">Hops</span><span className="v">{game.hops.length} <span className="dim">/ par {game.par}</span></span></div>
      <div className="kv"><span className="muted">Rarity so far</span><span className="v">{level}</span></div>
      <div className="bar gold"><div style={{ width: `${Math.round(avg * 100)}%` }} /></div>
      <p className="dim small">
        Links through big squads score low on rarity. Route through a smaller squad for a bonus.
        {rarities.some(isRare) && ' You’ve found a rare link!'}
      </p>
    </div>
  )
}

function HowItWorks({ dataRange }: { dataRange: string }) {
  const steps = [
    'Name a player who was at the same club, in the same season, as the last player in your chain.',
    'Pick the club you’re linking through. You can’t use the same club twice in a row.',
    'Reach the target in as few hops as you can. Par is the shortest route in our data.',
  ]
  return (
    <div className="panel deep stack">
      <div className="panel-title">How it works</div>
      {steps.map((s, i) => (
        <div key={i} className="row" style={{ alignItems: 'flex-start', gap: 10, flexWrap: 'nowrap' }}>
          <span className="avatar" style={{ width: 24, height: 24, fontSize: 13, background: 'var(--line-dim)', color: 'var(--lime)' }}>{i + 1}</span>
          <span className="muted small" style={{ fontSize: 14 }}>{s}</span>
        </div>
      ))}
      <p className="dim small">Careers {dataRange} · Top-5 European leagues · rated 70+</p>
    </div>
  )
}

export function GamePage({ id }: { id: string }) {
  const [game, setGame] = useState<Game | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [player, setPlayer] = useState<Player | null>(null)
  const [club, setClub] = useState<Club | null>(null)
  const [moveError, setMoveError] = useState<string | null>(null)
  const [removed, setRemoved] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.game(id).then(setGame, (e) => setLoadError(e.message))
  }, [id])

  useEffect(() => {
    if (game && game.status !== 'in_progress') navigate({ page: 'result', id: game.id })
  }, [game])

  if (loadError) return <main className="page"><p className="error">{loadError}</p></main>
  if (!game) return <main className="page"><p className="muted">Loading…</p></main>

  const lastClub = game.hops.length ? game.hops[game.hops.length - 1].club : null

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!player || !club || !game) return
    setBusy(true)
    setMoveError(null)
    try {
      setGame(await api.move(game.id, player.id, club.id))
      setPlayer(null)
      setClub(null)
      setRemoved(null)
    } catch (err) {
      // Keep the selections so the user can fix just the wrong half.
      setMoveError(err instanceof Error ? err.message : 'Move failed.')
    } finally {
      setBusy(false)
    }
  }

  /** Remove hop `idx` and all after it, then pre-fill the form with it so the user can edit and re-add. */
  async function removeFrom(idx: number) {
    if (!game) return
    const gone = game.hops.slice(idx)
    if (gone.length > 1 && !confirm(`Remove ${gone.map((h) => h.to.name).join(', ')}? Links after ${gone[0].to.name} depend on it.`)) return
    setBusy(true)
    setMoveError(null)
    try {
      setGame(await api.removeFrom(game.id, idx))
      const h = gone[0]
      setPlayer(h.to)
      setClub({ id: h.club.id, name: h.club.name, league: '', aliases: [] })
      setRemoved(h.to.name)
    } catch (err) {
      setMoveError(err instanceof Error ? err.message : 'Could not remove that link.')
    } finally {
      setBusy(false)
    }
  }

  async function giveUp() {
    if (!game || !confirm('Give up and see the shortest route?')) return
    try {
      setGame(await api.giveUp(game.id))
    } catch (err) {
      setMoveError(err instanceof Error ? err.message : 'Could not give up.')
    }
  }

  return (
    <main className="page">
      <div className="page-main">
        <Matchup game={game} />

        <section className="stack">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2 className="section">Your chain</h2>
            {game.hops.length > 0 && (
              <button type="button" className="btn-ghost" onClick={() => removeFrom(game.hops.length - 1)} disabled={busy}>
                Undo last link
              </button>
            )}
          </div>
          <div className="panel">
            <Chain start={game.start} hops={game.hops} endId={game.end.id} pendingTarget={game.end}
              onRemove={busy ? undefined : removeFrom} />
          </div>
        </section>

        <form className="panel deep stack" style={{ gap: 16 }} onSubmit={submit}>
          <h2 style={{ fontSize: 26 }}>
            Who played with <span style={{ color: 'var(--gold)' }}>{game.current.name}</span>?
          </h2>
          {removed && (
            <div className="notice" role="status">
              <span>Removed {removed}. Change the player or club and add it again, or pick someone else.</span>
              <button type="button" className="btn-link" onClick={() => { setPlayer(null); setClub(null); setRemoved(null) }}>
                Clear
              </button>
            </div>
          )}
          {player?.id !== game.end.id && (
            <button type="button" className="target-shortcut" onClick={() => setPlayer(game.end)} disabled={busy}>
              <span className="pcard target mini" aria-hidden="true"><span className="pname">{game.end.name}</span></span>
              <span>
                <strong>Link straight to {game.end.name}</strong>
                <span className="dim small"> · the target — just pick the club they shared with {game.current.name}</span>
              </span>
            </button>
          )}
          <PlayerPicker value={player} onChange={setPlayer} disabled={busy} autoFocus={!removed} />
          <ClubPicker value={club} onChange={setClub} disabled={busy} />
          {lastClub && (
            <p className="dim small">
              Your last link was {lastClub.name}, so you can’t use it for this hop (in any season).
            </p>
          )}
          {moveError && <p className="error" role="alert">{moveError}</p>}
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <button type="submit" className="btn" disabled={!player || !club || busy}>
              {busy ? 'Checking…' : 'Add link'}
            </button>
            <button type="button" className="btn-link" onClick={giveUp} disabled={busy}>
              Give up &amp; see the route
            </button>
          </div>
        </form>
      </div>

      <aside className="rail">
        <LiveScore game={game} />
        <HowItWorks dataRange={game.data_range} />
      </aside>
    </main>
  )
}
