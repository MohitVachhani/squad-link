import { useEffect, useState } from 'react'

// Minimal hash router: #/ , #/game/<id> , #/result/<id>. Survives reloads without server config.
export type Route = { page: 'home' } | { page: 'game'; id: string } | { page: 'result'; id: string }

function parse(hash: string): Route {
  const [, page, id] = hash.replace(/^#/, '').split('/')
  if ((page === 'game' || page === 'result') && id) return { page, id }
  return { page: 'home' }
}

export function navigate(to: Route) {
  window.location.hash = to.page === 'home' ? '/' : `/${to.page}/${to.id}`
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parse(window.location.hash))
  useEffect(() => {
    const onChange = () => setRoute(parse(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}
