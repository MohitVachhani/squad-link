import { useCallback } from 'react'
import { api, type Club, type Player } from '../api'
import { Autocomplete } from './Autocomplete'
import { initials, playerSub } from '../format'

function Row({ badge, main, sub }: { badge: string; main: string; sub: string }) {
  return (
    <>
      <span className="initials">{badge}</span>
      <span>
        <div className="main">{main}</div>
        <div className="sub">{sub}</div>
      </span>
    </>
  )
}

function Chosen({ main, sub }: { main: string; sub: string }) {
  return (
    <span>
      <div className="main" style={{ fontWeight: 600 }}>{main}</div>
      <div className="sub muted small">{sub}</div>
    </span>
  )
}

type PickerProps<T> = { value: T | null; onChange: (v: T | null) => void; disabled?: boolean; autoFocus?: boolean }

export function PlayerPicker(props: PickerProps<Player>) {
  const search = useCallback(async (q: string, signal: AbortSignal) => {
    const r = await api.searchPlayers(q, signal)
    return {
      items: r.results,
      // Never guess between namesakes: tell the user to pick.
      note: r.ambiguous ? `Several players are called “${q}” — pick the right one.` : undefined,
    }
  }, [])
  return (
    <Autocomplete<Player>
      {...props}
      label="Next player"
      placeholder="Start typing a name, e.g. Kante"
      search={search}
      itemKey={(p) => p.id}
      renderItem={(p) => (
        <Row badge={initials(p.name)} main={p.full !== p.name ? `${p.name} — ${p.full}` : p.name} sub={playerSub(p)} />
      )}
      renderSelected={(p) => <Chosen main={p.name} sub={playerSub(p)} />}
    />
  )
}

export function ClubPicker(props: PickerProps<Club>) {
  const search = useCallback(
    async (q: string, signal: AbortSignal) => ({ items: (await api.searchClubs(q, signal)).results }),
    [],
  )
  const sub = (c: Club) => (c.aliases.length ? `${c.league} · also ${c.aliases.join(', ')}` : c.league)
  return (
    <Autocomplete<Club>
      {...props}
      label="Shared club"
      placeholder="The club they played for together"
      search={search}
      itemKey={(c) => c.id}
      renderItem={(c) => <Row badge={initials(c.name)} main={c.name} sub={sub(c)} />}
      renderSelected={(c) => <Chosen main={c.name} sub={c.league || 'Club'} />}
    />
  )
}
