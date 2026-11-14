import { useEffect, useState } from 'react'
import AgentLogPanel, { type AgentStep } from './components/AgentLogPanel'
import QueryBox from './components/QueryBox'
import Report from './components/Report'
import SiteCard from './components/SiteCard'
import SiteMap from './components/SiteMap'
import { SparkleDoodle } from './components/EditorialIllustrations'
import type { BusinessBrief, RunResult, Site } from './types'

const TOP = 3 // matches backend agent/run.py TOP

export default function App() {
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState('')
  const [selectedSiteId, setSelectedSiteId] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [steps, setSteps] = useState<AgentStep[]>([])
  const [showReport, setShowReport] = useState(false)
  const [showLeftPanel, setShowLeftPanel] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [picks, setPicks] = useState<string[]>([]) // the agent's top picks, sent before their simulations

  // Load initial golden fixture on start
  useEffect(() => {
    fetch('/api/runs/golden')
      .then((r) => (r.ok ? r.json() : Promise.reject(`backend returned ${r.status}`)))
      .then((data: RunResult) => {
        setRun(data)
      })
      .catch((e) => setError(`Could not load run: ${e}`))
  }, [])

  // Live /analyze stream (Dev 2 Hours 6.5–9)
  const handleSearch = (query: string) => {
    setHasSearched(true)
    setShowLeftPanel(true)
    setLoading(true)
    setError('')
    setSteps([])
    setPicks([])

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
        })

        sse.addEventListener('ranking', (ev) => {
          setPicks((JSON.parse(ev.data) as { siteIds: string[] }).siteIds)
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
          // the stored result has the agent's final ranking (cards arrived in simulation order) and its report
          fetch(`/api/runs/${runId}`)
            .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
            .then((final: RunResult) => {
              setRun(final)
            })
            .catch(() => { }) // keep the streamed cards if the fetch fails (e.g. a fatal error left no result)
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

  // simulate a candidate the agent skipped; the server stores it, so the final run stays complete
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
      for (const s of unsimulated) await simulateSite(s.id) // one at a time: each gathers live data
    } catch (e) {
      setError(`Simulation failed: ${e}`)
    } finally {
      setSimulatingAll(false)
    }
  }

  // while streaming, order by odds so far (unsimulated last); once done, the server's ranked order is used as-is
  // while the agent works: its picks as soon as it ranks them, before that every candidate as it arrives
  const sites = run?.sites ?? []
  const picked = picks.flatMap((id) => sites.filter((s) => s.id === id))
  const ranked = !loading ? sites : picked.length ? [...picked, ...sites.filter((s) => !picks.includes(s.id))] : sites
  const shownSites = loading && !picked.length ? ranked : ranked.slice(0, loading ? picked.length : TOP)
  const otherSites = ranked.slice(shownSites.length)
  const simulatingNow = (s: Site) => loading && picks.includes(s.id) && !s.sim

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
          sites={hasSearched ? shownSites : []}
          selectedSiteId={selectedSiteId}
          onSelectSite={(id) => {
            setSelectedSiteId(id)
            setHasSearched(true)
            setShowLeftPanel(true)
          }}
        />

        {/* Floating Decision Report circular button at bottom left */}
        {hasSearched && run && (
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
              Explore Locations {hasSearched && run?.sites && run.sites.length > 0 ? `(${run.sites.length})` : ''}
            </span>
          </button>
        )}

        {/* Left Column: Editorial Search & Candidate Findings Sidebar */}
        <div className={`left-panel no-print ${!showLeftPanel ? 'is-collapsed' : ''}`}>
          <QueryBox
            brief={run?.brief}
            onSearch={handleSearch}
            loading={loading}
            onTogglePanel={() => setShowLeftPanel(false)}
          />

          {hasSearched && run && (
            <aside className="sites">
              {shownSites.map((s, i) => (
                <SiteCard
                  key={s.id}
                  site={s}
                  rank={i + 1}
                  selected={s.id === selectedSiteId}
                  onSelect={() => setSelectedSiteId(s.id)}
                  simulatingNow={simulatingNow(s)}
                  onSimulate={!s.sim && unsimulated.includes(s) ? () => simulateSite(s.id) : undefined}
                />
              ))}
              {otherSites.length > 0 && (
                <details className="agent-report-card">
                  <summary>Other candidates ({otherSites.length})</summary>
                  {unsimulated.length > 0 && (
                    <button type="button" className="simulate-btn" onClick={simulateRemaining} disabled={simulatingAll}>
                      {simulatingAll ? 'Simulating…' : `Simulate remaining ${unsimulated.length}`}
                    </button>
                  )}
                  {otherSites.map((s, i) => (
                    <SiteCard
                      key={s.id}
                      site={s}
                      rank={TOP + i + 1}
                      onSimulate={!s.sim && unsimulated.includes(s) ? () => simulateSite(s.id) : undefined}
                    />
                  ))}
                </details>
              )}
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
