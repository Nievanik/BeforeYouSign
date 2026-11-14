import { useState } from 'react'
import type { BusinessBrief } from '../types'

interface QueryBoxProps {
  brief?: BusinessBrief
  onSearch?: (query: string) => void
  loading?: boolean
}

const PRESETS = [
  'Boba shop in Houston, max $6k/month rent, needs parking',
  'Coffee shop in Houston, max $8k/month rent, near daytime workers',
  'Hair salon in Houston, max $5k/month rent, 1000-1500 sq ft',
]

export default function QueryBox({ brief, onSearch, loading = false }: QueryBoxProps) {
  const [query, setQuery] = useState(
    'Boba shop in Houston, max $6k/month rent, needs parking'
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim() && onSearch) {
      onSearch(query.trim())
    }
  }

  return (
    <div className="query-box">
      <form onSubmit={handleSubmit} className="query-form">
        <div className="search-input-row">
          <input
            type="text"
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe your business idea, target city, rent budget, and requirements..."
            disabled={loading}
          />
          <button type="submit" className="search-button" disabled={loading}>
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
      </form>

      {brief && (
        <div className="brief-chips">
          <span className="chip chip-type">Type: {brief.businessType}</span>
          <span className="chip chip-city">City: {brief.city}</span>
          <span className="chip chip-rent">Max Rent: ${brief.maxRentMonthly.toLocaleString()}/mo</span>
          {brief.sizeSqftMin != null && (
            <span className="chip">Min Size: {brief.sizeSqftMin.toLocaleString()} sq ft</span>
          )}
          {brief.parkingRequired && <span className="chip chip-must">Must: parking</span>}
          {brief.mustHaves?.map((m) => (
            <span key={m} className="chip chip-must">Must: {m}</span>
          ))}
        </div>
      )}

      <div className="presets-row">
        <span className="presets-label">Try:</span>
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
  )
}
