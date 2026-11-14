import { useEffect, useState } from 'react'
import AgentLogPanel, { type AgentStep } from './components/AgentLogPanel'
import QueryBox from './components/QueryBox'
import SiteCard from './components/SiteCard'
import SiteMap from './components/SiteMap'
import type { BusinessBrief, RunResult, Site } from './types'

export default function App() {
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState('')
  const [selectedSiteId, setSelectedSiteId] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [steps, setSteps] = useState<AgentStep[]>([])

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
    <>
      {/* 1. Header with Query Box */}
      <header className="app-header">
        <QueryBox
          brief={run?.brief}
          onSearch={handleSearch}
          loading={loading}
        />
      </header>

      {/* 2. Fullscreen Interactive Map with Sites + Competitor Markers */}
      <SiteMap
        sites={run?.sites ?? []}
        selectedSiteId={selectedSiteId}
        onSelectSite={setSelectedSiteId}
      />

      {/* 3. Ranked Candidate Site Cards (fill in progressively as each site finishes) */}
      {run && (
        <aside className="sites">
          <div className="sites-header">
            Candidate Properties ({run.sites.length})
            {loading && <span style={{ marginLeft: 6, color: '#2563eb' }}>● streaming…</span>}
          </div>
          {run.sites.map((s, i) => (
            <SiteCard key={s.id} site={s} rank={i + 1} />
          ))}
        </aside>
      )}

      {/* 4. Agent Reasoning Log Panel */}
      <AgentLogPanel steps={steps.length > 0 ? steps : undefined} />

      {/* Error alert toast */}
      {error && (
        <div
          role="alert"
          style={{
            position: 'absolute',
            top: 14,
            right: 14,
            background: '#fee2e2',
            color: '#991b1b',
            border: '1px solid #f87171',
            borderRadius: 6,
            padding: '8px 14px',
            fontSize: 13,
            zIndex: 100,
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          {error}
        </div>
      )}
    </>
  )
}
