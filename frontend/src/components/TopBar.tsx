import type { ReactNode } from 'react'
import { useAuth } from '../auth'
import { Brand } from './ui'

export function TopBar({ children }: { children?: ReactNode }) {
  const { user, logout } = useAuth()
  return (
    <header className="topbar">
      <Brand />
      {children}
      {user && (
        <div className="account">
          <span className="avatar" aria-hidden="true">{user.email[0]?.toUpperCase()}</span>
          <span className="small">{user.email}</span>
          <button type="button" className="btn-link" onClick={logout}>Log out</button>
        </div>
      )}
    </header>
  )
}
