import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

type Props<T> = {
  label: string
  placeholder: string
  value: T | null
  onChange: (value: T | null) => void
  search: (q: string, signal: AbortSignal) => Promise<{ items: T[]; note?: string }>
  itemKey: (item: T) => string | number
  renderItem: (item: T) => ReactNode
  renderSelected: (item: T) => ReactNode
  disabled?: boolean
  autoFocus?: boolean
}

/** Search-as-you-type picker. The user must pick an item: typed text alone is never submitted. */
export function Autocomplete<T>(props: Props<T>) {
  const { label, placeholder, value, onChange, search, itemKey, renderItem, renderSelected, disabled, autoFocus } =
    props
  const id = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  // Results are tagged with the query that produced them, so stale results never show for newer input.
  const [results, setResults] = useState<{ q: string; items: T[]; note?: string }>({ q: '', items: [] })
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const q = query.trim()
    if (!q || value) return // the list is hidden when the query is empty
    const ctrl = new AbortController()
    const t = setTimeout(async () => {
      try {
        const r = await search(q, ctrl.signal)
        setResults({ q, ...r })
        setActive(0)
        setError(null)
      } catch (e) {
        if (!ctrl.signal.aborted) setError(e instanceof Error ? e.message : 'Search failed')
      }
    }, 150)
    return () => {
      clearTimeout(t)
      ctrl.abort()
    }
  }, [query, value, search])

  function pick(item: T) {
    onChange(item)
    setQuery('')
    setOpen(false)
  }

  function clear() {
    onChange(null)
    setTimeout(() => inputRef.current?.focus())
  }

  if (value) {
    return (
      <div className="field">
        <span className="label">{label}</span>
        <div className="ac-selected">
          <div>{renderSelected(value)}</div>
          <button type="button" className="btn-link" onClick={clear} disabled={disabled}>
            Change
          </button>
        </div>
      </div>
    )
  }

  const q = query.trim()
  const fresh = results.q === q
  const items = fresh ? results.items : []
  const showList = open && q !== ''
  const listId = `${id}-list`
  return (
    <div className="field ac">
      <label className="label" htmlFor={id}>
        {label}
      </label>
      <input
        ref={inputRef}
        id={id}
        className="input"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && items[active] ? `${id}-opt-${active}` : undefined}
        autoComplete="off"
        placeholder={placeholder}
        value={query}
        disabled={disabled}
        autoFocus={autoFocus}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setOpen(true)
            setActive((a) => Math.min(a + 1, items.length - 1))
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setActive((a) => Math.max(a - 1, 0))
          } else if (e.key === 'Enter' && showList && items[active]) {
            e.preventDefault()
            pick(items[active])
          } else if (e.key === 'Escape') {
            setOpen(false)
          }
        }}
      />
      {showList && (
        <div className="ac-list">
          {fresh && results.note && <div className="ac-note">{results.note}</div>}
          <ul id={listId} role="listbox">
            {items.map((item, i) => (
              <li
                key={itemKey(item)}
                id={`${id}-opt-${i}`}
                role="option"
                aria-selected={i === active}
                className={`ac-item ${i === active ? 'active' : ''}`}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => {
                  e.preventDefault()
                  pick(item)
                }}
              >
                {renderItem(item)}
              </li>
            ))}
          </ul>
          {!fresh && !error && <div className="ac-empty">Searching…</div>}
          {fresh && !error && items.length === 0 && <div className="ac-empty">No matches in our data.</div>}
          {error && <div className="ac-empty error">{error}</div>}
        </div>
      )}
    </div>
  )
}
