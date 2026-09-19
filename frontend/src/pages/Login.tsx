import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth'
import { BrandMark, LinkPill, PlayerCard } from '../components/ui'

// A real chain from our data (Cavani → Luis Alberto is 3 hops).
const EXAMPLE = [
  { name: 'Cavani', nation: 'Uruguay' },
  { club: 'PSG', season: '2014/15' },
  { name: 'Ibrahimović', nation: 'Sweden' },
  { club: 'Milan', season: '2020/21' },
  { name: 'Romagnoli', nation: 'Italy' },
  { club: 'Lazio', season: '2022/23' },
  { name: 'L. Alberto', nation: 'Spain' },
] as const

function PitchLines() {
  return (
    <svg className="pitch" viewBox="0 0 640 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <g fill="none" stroke="#E8F1EA" strokeWidth="2">
        <rect x="-200" y="80" width="1040" height="640" />
        <line x1="320" y1="80" x2="320" y2="720" />
        <circle cx="320" cy="400" r="110" />
        <circle cx="320" cy="400" r="4" fill="#E8F1EA" />
        <rect x="-200" y="230" width="190" height="340" />
        <rect x="650" y="230" width="190" height="340" />
      </g>
    </svg>
  )
}

export function Login() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const isLogin = mode === 'login'

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await (isLogin ? login : register)(email.trim(), password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  function switchTo(m: 'login' | 'signup') {
    setMode(m)
    setError(null)
  }

  return (
    <div className="auth">
      <section className="auth-brand">
        <PitchLines />
        <div className="row" style={{ gap: 12 }}>
          <BrandMark size={40} />
          <span className="brand-name" style={{ fontSize: 28 }}>Squadlink</span>
        </div>
        <div className="stack" style={{ gap: 28 }}>
          <h1>
            Connect any two
            <br />
            footballers.
            <br />
            <span style={{ color: 'var(--lime)' }}>Fewest hops wins.</span>
          </h1>
          <p style={{ fontSize: 18, color: '#B9CBC0', maxWidth: 460 }}>
            Link players through clubs where they shared a dressing room in the same season. Beat par, find the rare
            route, share your chain.
          </p>
          <div className="chain auth-example" aria-label="Example chain">
            {EXAMPLE.map((x, i) =>
              'club' in x ? (
                <LinkPill key={i} club={x.club} seasons={[x.season]} />
              ) : (
                <PlayerCard key={i} p={x} variant={i === EXAMPLE.length - 1 ? 'target' : 'gold'} />
              ),
            )}
          </div>
        </div>
        <p className="dim small">Careers 2014/15 – 2023/24 · Top-5 European leagues</p>
      </section>

      <section className="auth-form">
        <form onSubmit={submit}>
          <div className="tabs" role="tablist">
            <button type="button" role="tab" aria-selected={isLogin} onClick={() => switchTo('login')}>Log in</button>
            <button type="button" role="tab" aria-selected={!isLogin} onClick={() => switchTo('signup')}>Sign up</button>
          </div>

          <div className="stack" style={{ gap: 6 }}>
            <h2 style={{ fontSize: 40 }}>{isLogin ? 'Back on the pitch' : 'Join the squad'}</h2>
            <p className="muted">{isLogin ? 'Log in to pick up your games and scores.' : 'Free. Takes less than a minute.'}</p>
          </div>

          <label className="field">
            <span className="label">Email</span>
            <input className="input" type="email" required autoComplete="email" placeholder="you@example.com"
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field">
            <span className="label">Password</span>
            <input className="input" type="password" required minLength={isLogin ? undefined : 8}
              autoComplete={isLogin ? 'current-password' : 'new-password'} placeholder="••••••••"
              value={password} onChange={(e) => setPassword(e.target.value)} />
            {!isLogin && <span className="dim small">At least 8 characters.</span>}
          </label>

          {error && <p className="error" role="alert">{error}</p>}

          <button type="submit" className="btn block" disabled={busy}>
            {busy ? 'Please wait…' : isLogin ? 'Log in & play' : 'Create account'}
          </button>
        </form>
      </section>
    </div>
  )
}
