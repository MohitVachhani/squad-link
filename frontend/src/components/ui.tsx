import type { Hop, Player } from '../api'
import { isRare, shortSeasons } from '../format'

export function BrandMark({ size = 32 }: { size?: number }) {
  return (
    <span className="brand-mark" style={{ width: size, height: size }}>
      <svg width={size * 0.56} height={size * 0.56} viewBox="0 0 24 24" fill="none" stroke="#0E1A14" strokeWidth="2.4"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
        <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
      </svg>
    </span>
  )
}

export function Brand() {
  return (
    <a href="#/" className="brand">
      <BrandMark />
      <span className="brand-name">Squadlink</span>
    </a>
  )
}

type CardVariant = 'gold' | 'target' | 'ghost'

export function PlayerCard({ p, variant = 'gold' }: { p: Pick<Player, 'name' | 'nation'>; variant?: CardVariant }) {
  return (
    <div className={`pcard ${variant === 'gold' ? '' : variant}`}>
      <div className="pname">{p.name}</div>
      <div className="pnation">{p.nation}</div>
    </div>
  )
}

function Arrow({ dim, dashed }: { dim?: boolean; dashed?: boolean }) {
  const stroke = dim ? '#7F9689' : dashed ? '#3E6A52' : '#C8F545'
  const dash = dashed ? '3 3' : undefined
  return (
    <>
      <svg className="arrow-h" width="48" height="10" viewBox="0 0 48 10" aria-hidden="true">
        <path d="M0 5h42m-6-4 6 4-6 4" fill="none" stroke={stroke} strokeWidth="2" strokeDasharray={dash} />
      </svg>
      <svg className="arrow-v" width="10" height="26" viewBox="0 0 10 26" aria-hidden="true">
        <path d="M5 0v18m-4-5 4 5 4-5" fill="none" stroke={stroke} strokeWidth="2" strokeDasharray={dash} />
      </svg>
    </>
  )
}

export function LinkPill({ club, seasons, rarity, dim }: { club: string; seasons: string[]; rarity?: number; dim?: boolean }) {
  const rare = rarity !== undefined && isRare(rarity)
  return (
    <div className="link">
      <span className={`pill ${rare ? 'rare' : ''}`} title={rarity !== undefined ? `link rarity ${rarity.toFixed(2)}` : undefined}>
        {club} · {shortSeasons(seasons)}
        {rare && ' · rare'}
      </span>
      <Arrow dim={dim} />
    </div>
  )
}

/**
 * start card → [club pill → card]… Horizontal on desktop, vertical on phones (CSS).
 * `pendingTarget` draws the unfinished tail of a game in progress: "shared club?" → ? → target.
 */
export function Chain({ start, hops, endId, ghost, pendingTarget, onRemove }: {
  start: Player
  hops: Hop[]
  endId?: number
  ghost?: boolean
  pendingTarget?: Player
  /** Shows a remove button on each linked player: removes that hop and everything after it. */
  onRemove?: (idx: number) => void
}) {
  const cardFor = (p: Player): CardVariant => (ghost ? 'ghost' : p.id === endId ? 'target' : 'gold')
  return (
    <div className="chain">
      <PlayerCard p={start} variant={cardFor(start)} />
      {hops.map((h, i) => (
        <div key={i} style={{ display: 'contents' }}>
          <LinkPill club={h.club.name} seasons={h.seasons} rarity={ghost ? undefined : h.rarity} dim={ghost} />
          <div className="pcard-wrap">
            <PlayerCard p={h.to} variant={cardFor(h.to)} />
            {onRemove && (
              <button
                type="button"
                className="remove"
                onClick={() => onRemove(i)}
                aria-label={i === hops.length - 1 ? `Remove ${h.to.name}` : `Remove ${h.to.name} and the links after`}
                title={i === hops.length - 1 ? 'Remove this link' : 'Remove this link and everything after it'}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"
                  strokeLinecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
              </button>
            )}
          </div>
        </div>
      ))}
      {pendingTarget && (
        <>
          <div className="link">
            <span className="pill pending">shared club?</span>
            <Arrow dashed />
          </div>
          <div className="pcard slot" aria-hidden="true">?</div>
          <div className="link">
            <Arrow dashed />
          </div>
          <PlayerCard p={pendingTarget} variant="target" />
        </>
      )}
    </div>
  )
}
