// Types mirror backend/squadlink/api/schemas.py.

export type ClubRef = { id: number; name: string }
export type Club = ClubRef & { league: string; aliases: string[] }

export type Player = {
  id: number
  name: string
  full: string
  nation: string
  dob: string | null
  ovr: number | null
  latest_club: ClubRef | null
  latest_season: string | null
  first_season: string | null
}

export type Hop = { from_id: number; to: Player; club: ClubRef; seasons: string[]; rarity: number }
export type GameStatus = 'in_progress' | 'won' | 'abandoned'

export type Game = {
  id: string
  status: GameStatus
  start: Player
  end: Player
  current: Player
  hops: Hop[]
  last_club_id: number | null
  par: number
  data_range: string
  started_at: string | null
}

export type GameSummary = {
  id: string
  status: GameStatus
  start: Player
  end: Player
  hops: number
  par: number
  score: number | null
  started_at: string | null
}

export type Score = {
  hops: number
  optimal_hops: number
  efficiency: number
  rarity: number
  efficiency_points: number
  rarity_points: number
  total: number
  efficiency_weight: number
  rarity_weight: number
}

export type Result = {
  game: Game
  optimal_path: Hop[]
  score: Score | null
  share_text: string | null
  data_range: string
}

export type Meta = { season_range: string; seasons: string[]; graph_version: number; players: number; clubs: number }
export type User = { id: string; email: string }

export class ApiError extends Error {
  status: number
  code: string | null
  constructor(status: number, message: string, code: string | null = null) {
    super(message)
    this.status = status
    this.code = code
  }
}

const TOKEN_KEY = 'squadlink.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // storage unavailable (private mode): the session just won't survive a reload
  }
}

let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

// fastapi-users error codes -> readable messages
const AUTH_MESSAGES: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: 'Wrong email or password.',
  REGISTER_USER_ALREADY_EXISTS: 'An account with this email already exists.',
  LOGIN_USER_NOT_VERIFIED: 'Please verify your email first.',
}

function errorFrom(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return new ApiError(status, AUTH_MESSAGES[detail] ?? detail, detail)
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const d = detail as { code?: string; message?: string; reason?: string }
    return new ApiError(status, d.message ?? d.reason ?? 'Something went wrong.', d.code ?? null)
  }
  if (Array.isArray(detail)) {
    const first = detail[0] as { loc?: unknown[]; msg?: string }
    return new ApiError(status, `${first?.loc?.slice(-1)[0] ?? 'input'}: ${first?.msg ?? 'invalid'}`)
  }
  return new ApiError(status, `Request failed (${status}).`)
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && typeof init.body === 'string') headers.set('Content-Type', 'application/json')

  let res: Response
  try {
    res = await fetch(path, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Can’t reach the server. Is the backend running?')
  }
  const body = res.status === 204 ? null : await res.json().catch(() => null)
  if (res.status === 401 && token) onUnauthorized()
  if (!res.ok) throw errorFrom(res.status, body)
  return body as T
}

const post = <T,>(path: string, data?: unknown) =>
  request<T>(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) })

export const api = {
  meta: () => request<Meta>('/api/meta'),

  async login(email: string, password: string) {
    const form = new URLSearchParams({ username: email, password })
    const r = await request<{ access_token: string }>('/auth/jwt/login', { method: 'POST', body: form })
    return r.access_token
  },
  register: (email: string, password: string) => post<User>('/auth/register', { email, password }),
  me: () => request<User>('/users/me'),

  searchPlayers: (q: string, signal?: AbortSignal) =>
    request<{ ambiguous: boolean; results: Player[] }>(`/api/players/search?q=${encodeURIComponent(q)}&limit=8`, {
      signal,
    }),
  searchClubs: (q: string, signal?: AbortSignal) =>
    request<{ results: Club[] }>(`/api/clubs/search?q=${encodeURIComponent(q)}&limit=8`, { signal }),

  newGame: () => post<Game>('/api/games'),
  games: () => request<GameSummary[]>('/api/games'),
  game: (id: string) => request<Game>(`/api/games/${id}`),
  move: (id: string, player_id: number, club_id: number) => post<Game>(`/api/games/${id}/moves`, { player_id, club_id }),
  /** Remove hop `idx` and every hop after it. */
  removeFrom: (id: string, idx: number) => request<Game>(`/api/games/${id}/moves/${idx}`, { method: 'DELETE' }),
  giveUp: (id: string) => post<Game>(`/api/games/${id}/give-up`),
  result: (id: string) => request<Result>(`/api/games/${id}/result`),
}
