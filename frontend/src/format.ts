import type { Player } from './api'

/** '2021/22' -> '21/22'; a run of seasons -> '21/22–22/23'. */
export function shortSeasons(seasons: string[]): string {
  const s = (x: string) => x.slice(2)
  return seasons.length <= 1 ? s(seasons[0] ?? '') : `${s(seasons[0])}–${s(seasons[seasons.length - 1])}`
}

export function isRare(rarity: number) {
  return rarity >= 0.6
}

export function initials(name: string) {
  const parts = name.replace(/\./g, '').split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase()
}

/** "England · Man United 23/24 · b. 1997": enough to tell namesakes apart. */
export function playerSub(p: Player) {
  return [
    p.nation,
    p.latest_club && `${p.latest_club.name} ${shortSeasons([p.latest_season ?? ''])}`,
    p.dob && `b. ${p.dob.slice(0, 4)}`,
  ]
    .filter(Boolean)
    .join(' · ')
}
