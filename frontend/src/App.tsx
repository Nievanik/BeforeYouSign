import { useEffect, useState } from 'react'
import AgentLogPanel, { type AgentStep } from './components/AgentLogPanel'
import AgentReport from './components/AgentReport'
import { SparkleDoodle } from './components/EditorialIllustrations'
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
  const [showLeftPanel, setShowLeftPanel] = useState(true)
  const [activeNav, setActiveNav] = useState<'explore' | 'simulations'>('explore')

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

  // Live /analyze stream
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
          sse.close()
          fetch(`/api/runs/${runId}`)
            .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
            .then((final: RunResult) => {
              setRun(final)
              if (final.sites[0]) setSelectedSiteId(final.sites[0].id)
            })
            .catch(() => {})
            .finally(() => setLoading(false))
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

  const simulateSite = async (siteId: string) => {
    if (!run) return
    const res = await fetch(`/api/runs/${run.runId}/sites/${siteId}/simulate`, { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const site = (await res.json()) as Site
    setRun((prev) => (prev ? { ...prev, sites: prev.sites.map((s) => (s.id === site.id ? site : s)) } : prev))
  }

  const [simulatingAll, setSimulatingAll] = useState(false)
  const unsimulated = run && !loading && run.runId !== 'golden' ? run.sites.filter((s) => !s.sim) : []
  const simulateRemaining = async () => {
    setSimulatingAll(true)
    try {
      for (const s of unsimulated) await simulateSite(s.id)
    } catch (e) {
      setError(`Simulation failed: ${e}`)
    } finally {
      setSimulatingAll(false)
    }
  }

  const odds = (s: Site) => s.sim?.pProfitableBy12 ?? -1
  const shownSites = loading && run ? [...run.sites].sort((a, b) => odds(b) - odds(a)) : (run?.sites ?? [])

  return (
    <div className="app-layout">
      {/* Editorial Custom Navigation Bar */}
      <header className="editorial-navbar no-print">
        <div className="nav-brand-section">
          <div className="brand-badge-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </div>
          <div className="brand-text-block">
            <span className="brand-title">BeforeYouSign</span>
            <span className="brand-sub">LOCATION INTELLIGENCE</span>
          </div>
        </div>

        <nav className="nav-menu">
          <button
            type="button"
            className={`nav-menu-btn ${activeNav === 'explore' ? 'is-active' : ''}`}
            onClick={() => {
              setActiveNav('explore')
              setShowLeftPanel(true)
            }}
          >
            Explore Locations
          </button>
          <button
            type="button"
            className={`nav-menu-btn ${activeNav === 'simulations' ? 'is-active' : ''}`}
            onClick={() => {
              setActiveNav('simulations')
              setShowLeftPanel(true)
              const card = document.querySelector('.card')
              if (card) card.scrollIntoView({ behavior: 'smooth' })
            }}
          >
            Simulations
          </button>
          <button
            type="button"
            className="nav-menu-btn"
            onClick={() => setShowReport(true)}
            disabled={!run}
            title="Open printable executive decision brief"
          >
            Executive Brief
          </button>
        </nav>

        <div className="nav-action-section">
          <button
            type="button"
            className="primary-action-pill"
            onClick={() => {
              setShowLeftPanel(true)
              const input = document.querySelector<HTMLInputElement>('.search-input')
              if (input) {
                input.focus()
                input.select()
              }
            }}
          >
            <SparkleDoodle size={14} color="#FAF3E9" />
            <span>Analyze a Location</span>
          </button>
        </div>
      </header>

      {/* Main Map + Sidebar Workspace */}
      <main className="main-content">
        <SiteMap
          sites={run?.sites ?? []}
          selectedSiteId={selectedSiteId}
          onSelectSite={setSelectedSiteId}
        />

        {/* Floating Decision Report circular button at bottom left */}
        {run && (
          <button
            type="button"
            className="bottom-left-report-btn no-print"
            onClick={() => setShowReport(true)}
            disabled={loading}
            title="Download Decision Report (PDF)"
            aria-label="Download Decision Report (PDF)"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <polyline points="9 15 12 18 15 15" />
            </svg>
            <span className="report-tooltip">Download Decision Report (PDF)</span>
          </button>
        )}

        {/* Floating Hamburger / Reopen button when left panel is collapsed */}
        {!showLeftPanel && (
          <button
            type="button"
            className="floating-panel-toggle-btn no-print"
            onClick={() => setShowLeftPanel(true)}
            title="Show Search and Candidate Locations"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
            <span className="toggle-btn-label">
              Explore Locations {run?.sites && run.sites.length > 0 ? `(${run.sites.length})` : ''}
            </span>
          </button>
        )}

        {/* Left Column: Editorial Search & Candidate Properties Sidebar */}
        <div className={`left-panel no-print ${!showLeftPanel ? 'is-collapsed' : ''}`}>
          <QueryBox
            brief={run?.brief}
            onSearch={handleSearch}
            loading={loading}
            onTogglePanel={() => setShowLeftPanel(false)}
          />

          {run && (
            <aside className="sites">
              <div className="sites-header editorial-card">
                <div className="sites-header-left">
                  <span className="sites-header-spark">✦</span>
                  <span className="sites-header-title">Candidate Spots</span>
                  <span className="sites-count-pill">{run.sites.length}</span>
                </div>

                <div className="sites-header-right">
                  {loading && <span className="streaming-badge">● streaming…</span>}
                  {unsimulated.length > 0 && (
                    <button
                      type="button"
                      className="simulate-btn"
                      onClick={simulateRemaining}
                      disabled={simulatingAll}
                    >
                      {simulatingAll ? 'Simulating…' : `Simulate remaining ${unsimulated.length}`}
                    </button>
                  )}
                </div>
              </div>

              {run.report && !loading && (
                <details className="agent-report-card editorial-card" open>
                  <summary className="agent-report-summary">
                    <span className="summary-icon">✦</span>
                    <span>AI Location Recommendation</span>
                  </summary>
                  <div className="agent-report-content">
                    <AgentReport markdown={run.report} />
                  </div>
                </details>
              )}

              {shownSites.map((s, i) => (
                <SiteCard
                  key={s.id}
                  site={s}
                  rank={i + 1}
                  onSimulate={!s.sim && unsimulated.includes(s) ? () => simulateSite(s.id) : undefined}
                />
              ))}
            </aside>
          )}
        </div>

        {/* Autonomous AI Investigation Panel ("Behind the Location") on bottom right */}
        <div className="no-print">
          <AgentLogPanel steps={steps.length > 0 ? steps : undefined} />
        </div>
      </main>

      {/* Decision Report Modal */}
      {showReport && run && <Report run={run} onClose={() => setShowReport(false)} />}

      {/* Error Banner */}
      {error && (
        <div role="alert" className="error-alert no-print">
          <span className="error-icon">✕</span>
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
