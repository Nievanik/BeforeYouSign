import { useEffect, useState } from 'react'
import SiteMap from './components/SiteMap'
import type { RunResult } from './types'

export default function App() {
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    // shortcut: loads the fixture run; swap for POST /api/analyze + SSE in Phase 5
    fetch('/api/runs/golden')
      .then((r) => (r.ok ? r.json() : Promise.reject(`backend returned ${r.status}`)))
      .then(setRun)
      .catch((e) => setError(`Could not load run (is the backend running?): ${e}`))
  }, [])

  return (
    <>
      <SiteMap sites={run?.sites ?? []} />
      {error && <div role="alert" style={{ position: 'absolute', top: 12, left: 12, background: '#fee', padding: 8 }}>{error}</div>}
    </>
  )
}
