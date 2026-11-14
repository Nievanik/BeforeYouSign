import { useState } from 'react'
import type { BusinessBrief } from '../types'
import { SparkleDoodle } from './EditorialIllustrations'

interface QueryBoxProps {
  brief?: BusinessBrief
  onSearch?: (query: string) => void
  loading?: boolean
  onTogglePanel?: () => void
}

const PRESETS = [
  'Boba shop in Houston, max $6k/month rent, needs parking',
  'Coffee shop in Houston, max $8k/month rent, near daytime workers',
  'Hair salon in Houston, max $5k/month rent, 1000-1500 sq ft',
]

export default function QueryBox({ brief, onSearch, loading = false, onTogglePanel }: QueryBoxProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim() && onSearch) {
      onSearch(query.trim())
    }
  }

  return (
    <div className="query-box editorial-card">
      <div className="query-box-header">
        <div className="query-title-row">
          <span className="scout-badge">
            <SparkleDoodle size={14} color="#DA4324" />
            <span>SCOUT & SIMULATE</span>
          </span>
          {onTogglePanel && (
            <button
              type="button"
              className="panel-collapse-btn"
              onClick={onTogglePanel}
              title="Hide search panel"
              aria-label="Hide search panel"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>
        <h2 className="query-heading">Where should we open next?</h2>
      </div>

      <form onSubmit={handleSubmit} className="query-form">
        <div className="search-input-row">
          <input
            type="text"
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Boba shop in Houston, max $6k rent, parking..."
            disabled={loading}
          />
          <button type="submit" className="search-button" disabled={loading}>
            {loading ? (
              <span className="btn-loading-state">
                <span className="spinner-dot" /> Analyzing…
              </span>
            ) : (
              <span>Analyze</span>
            )}
          </button>
        </div>
      </form>

      {brief && (
        <div className="brief-chips">
          <span className="chip chip-type">
            <span className="chip-bullet">●</span> {brief.businessType}
          </span>
          <span className="chip chip-city">
            <span className="chip-bullet">📍</span> {brief.city}
          </span>
          <span className="chip chip-rent">
            <span className="chip-bullet">💰</span> Max ${brief.maxRentMonthly.toLocaleString()}/mo
          </span>
          {brief.mustHaves?.map((m) => (
            <span key={m} className="chip chip-must">
              ✓ {m}
            </span>
          ))}
        </div>
      )}

      <div className="presets-row">
        <span className="presets-label">Popular ideas:</span>
        <div className="preset-pill-list">
          {PRESETS.map((p) => (
            <button
              type="button"
              key={p}
              className="preset-pill"
              onClick={() => {
                setQuery(p)
                if (onSearch) onSearch(p)
              }}
            >
              {p.split(',')[0]}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
