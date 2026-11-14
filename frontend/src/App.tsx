import { useEffect, useState } from 'react'
import AgentLogPanel, { type AgentStep } from './components/AgentLogPanel'
import QueryBox from './components/QueryBox'
import Report from './components/Report'
import SiteCard from './components/SiteCard'
import SiteMap from './components/SiteMap'
import type { BusinessBrief, RunResult, Site } from './types'

export default function App() {
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState('')
  const [selectedSiteId, setSelectedSiteId] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [steps, setSteps] = useState<AgentStep[]>([])
  const [showReport, setShowReport] = useState(false)

  // Load initial golden fixture on start
  useEffect(() => {
    fetch('/api/runs/golden')
      .then((r) => (r.ok ? r.json() : Promise.reject(`backend returned ${r.status}`)))
      .then((data: RunResult) => {
        setRun(data)
        if (data.sites?.length > 0) {
          setSelectedSiteId(data.sites[0].id)
        }
      })
      .catch((e) => setError(`Could not load run: ${e}`))
  }, [])

  // Live /analyze stream (Dev 2 Hours 6.5–9)
  const handleSearch = (query: string) => {
    setLoading(true)
    setError('')
    setSteps([])

    fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(({ runId, brief }: { runId: string; brief: BusinessBrief }) => {
        // Initialize an active empty run that fills in progressively
        setRun({
          runId,
          brief,
          sites: [],
          report: '',
          createdAt: new Date().toISOString(),
        })

        const sse = new EventSource(`/api/runs/${runId}/events`)

        sse.addEventListener('brief', (ev) => {
          const b = JSON.parse(ev.data) as BusinessBrief
          setRun((prev) => (prev ? { ...prev, brief: b } : prev))
        })

        sse.addEventListener('step', (ev) => {
          const stepData = JSON.parse(ev.data) as AgentStep
          setSteps((prev) => {
            const idx = prev.findIndex((s) => s.id === stepData.id)
            if (idx >= 0) {
              const copy = [...prev]
              copy[idx] = stepData
              return copy
            }
            return [...prev, stepData]
          })
        })

        sse.addEventListener('site', (ev) => {
          const newSite = JSON.parse(ev.data) as Site
          setRun((prev) => {
            if (!prev) return prev
            const existingIdx = prev.sites.findIndex((s) => s.id === newSite.id)
            const updatedSites =
              existingIdx >= 0
                ? prev.sites.map((s, idx) => (idx === existingIdx ? newSite : s))
                : [...prev.sites, newSite]
            return { ...prev, sites: updatedSites }
          })
          setSelectedSiteId(newSite.id)
        })

        sse.addEventListener('sim', (ev) => {
          const { siteId, result } = JSON.parse(ev.data)
          setRun((prev) => {
            if (!prev) return prev
            const updated = prev.sites.map((s) => (s.id === siteId ? { ...s, sim: result } : s))
            return { ...prev, sites: updated }
          })
        })

        sse.addEventListener('report', (ev) => {
          const { markdown } = JSON.parse(ev.data)
          setRun((prev) => (prev ? { ...prev, report: markdown } : prev))
        })

        sse.addEventListener('done', () => {
          setLoading(false)
          sse.close()
        })

        sse.addEventListener('error', (ev: MessageEvent) => {
          try {
            const errData = JSON.parse(ev.data)
            if (errData?.fatal) {
              setError(`Analysis failed: ${errData.message}`)
            }
          } catch {
            // normal stream completion or network disconnect
          }
          setLoading(false)
          sse.close()
        })
      })
      .catch((err) => {
        setError(`Failed to trigger analysis: ${err.message}`)
        setLoading(false)
      })
  }

  return (
    <div className="app-layout">
      {/* Top bar: brand and decision report */}
      <header className="app-topbar no-print">
        <div className="topbar-brand">
          <span className="brand-logo">📍 BeforeYouSign</span>
        </div>
        {run && (
          <div className="topbar-actions">
            <button
              type="button"
              className="decision-report-btn"
              onClick={() => setShowReport(true)}
              disabled={loading}
              title="Open one-page executive report ready to print or export as PDF"
            >
              📄 Decision Report (PDF)
            </button>
          </div>
        )}
      </header>

      {/* Map, ranked site cards (fill in live as sites finish), agent log */}
      <main className="main-content">
        {/* floating query box over the map; shows the parsed brief as chips */}
        <div className="app-header no-print">
          <QueryBox brief={run?.brief} onSearch={handleSearch} loading={loading} />
        </div>
        <SiteMap sites={run?.sites ?? []} selectedSiteId={selectedSiteId} onSelectSite={setSelectedSiteId} />
        {run && (
          <aside className="sites no-print">
            <div className="sites-header">
              Candidate Properties ({run.sites.length})
              {loading && <span className="streaming-dot">● streaming…</span>}
            </div>
            {run.sites.map((s, i) => (
              <SiteCard key={s.id} site={s} rank={i + 1} />
            ))}
          </aside>
        )}
        <div className="no-print">
          <AgentLogPanel steps={steps.length > 0 ? steps : undefined} />
        </div>
      </main>

      {showReport && run && <Report run={run} onClose={() => setShowReport(false)} />}

      {error && (
        <div role="alert" className="error-alert no-print">
          {error}
        </div>
      )}
    </div>
  )
}
