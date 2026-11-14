import { useEffect, useState } from 'react'
import Report from './components/Report'
import SiteCard from './components/SiteCard'
import SiteMap from './components/SiteMap'
import type { RunResult } from './types'

export default function App() {
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState('')
  const [showReport, setShowReport] = useState(false)

  useEffect(() => {
    // shortcut: loads the fixture run; swap for POST /api/analyze + SSE in Phase 5
    fetch('/api/runs/golden')
      .then((r) => (r.ok ? r.json() : Promise.reject(`backend returned ${r.status}`)))
      .then(setRun)
      .catch((e) => setError(`Could not load run (is the backend running?): ${e}`))
  }, [])

  return (
    <div className="app-layout">
      {/* Top Application Bar */}
      <header className="app-topbar no-print">
        <div className="topbar-brand">
          <span className="brand-logo">📍 BeforeYouSign</span>
          {run && (
            <span className="brief-pill">
              {run.brief.businessType.toUpperCase()} in {run.brief.city} · Max ${run.brief.maxRentMonthly.toLocaleString()}/mo
            </span>
          )}
        </div>
        {run && (
          <div className="topbar-actions">
            <button
              type="button"
              className="decision-report-btn"
              onClick={() => setShowReport(true)}
              title="Open one-page executive report ready to print or export as PDF"
            >
              📄 Decision Report (PDF)
            </button>
          </div>
        )}
      </header>

      {/* Map & Sites Container */}
      <main className="main-content">
        <SiteMap sites={run?.sites ?? []} />
        {run && (
          <aside className="sites no-print">
            {run.sites.map((s, i) => (
              <SiteCard key={s.id} site={s} rank={i + 1} />
            ))}
          </aside>
        )}
      </main>

      {/* One-Page Printable Report Modal */}
      {showReport && run && (
        <Report run={run} onClose={() => setShowReport(false)} />
      )}

      {error && (
        <div role="alert" className="error-alert no-print">
          {error}
        </div>
      )}
    </div>
  )
}
