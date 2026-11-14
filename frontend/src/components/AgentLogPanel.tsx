import { useState } from 'react'
import { SparkleDoodle } from './EditorialIllustrations'

export interface AgentStep {
  id: string
  tool: 'plan' | 'costar' | 'census' | 'osm' | 'vexcel' | 'matterport' | 'sim' | 'report'
  message: string
  status: 'running' | 'done' | 'error'
  siteAddress?: string
  durationMs?: number
}

// Built from the golden run investigation steps
const DEFAULT_EXAMPLE_STEPS: AgentStep[] = [
  {
    id: 's1',
    tool: 'plan',
    message: 'Parsed query: boba shop in Houston, max $6,000/mo rent, parking required',
    status: 'done',
    durationMs: 120,
  },
  {
    id: 's2',
    tool: 'costar',
    message: 'Queried CoStar commercial listings: retrieved active Houston ground-floor retail leases',
    status: 'done',
    durationMs: 450,
  },
  {
    id: 's3',
    tool: 'costar',
    message: 'Filtered candidate shortlist to 3 properties meeting size and rent constraints',
    status: 'done',
    durationMs: 230,
  },
  {
    id: 's4',
    tool: 'census',
    message: 'Fetched US Census ACS demographics (tract population, median income, commuter vehicle share)',
    status: 'done',
    siteAddress: '6003 Bellaire Blvd',
    durationMs: 380,
  },
  {
    id: 's5',
    tool: 'osm',
    message: 'Queried OpenStreetMap Overpass API for existing tea shops, cafés, and competitor density',
    status: 'done',
    siteAddress: '6003 Bellaire Blvd',
    durationMs: 510,
  },
  {
    id: 's6',
    tool: 'vexcel',
    message: 'Retrieved high-res Vexcel aerial ortho imagery and analyzed parking lot coverage',
    status: 'done',
    siteAddress: '6003 Bellaire Blvd',
    durationMs: 620,
  },
  {
    id: 's7',
    tool: 'matterport',
    message: 'Inspected Matterport 3D space model BoqDzrD8JLh: verified ~2,278 sq ft floor area & layout',
    status: 'done',
    siteAddress: '6003 Bellaire Blvd',
    durationMs: 340,
  },
  {
    id: 's8',
    tool: 'sim',
    message: 'Executed Huff gravity demand model & 1,000-iteration Monte Carlo financial cash-flow simulation',
    status: 'done',
    siteAddress: '6003 Bellaire Blvd',
    durationMs: 780,
  },
  {
    id: 's9',
    tool: 'sim',
    message: 'Completed comparative simulation for all candidate sites; 6003 Bellaire Blvd ranked #1',
    status: 'done',
    durationMs: 410,
  },
]

const TOOL_CONFIG: Record<string, { label: string; icon: string }> = {
  plan: { label: 'Scout Plan', icon: '🎯' },
  costar: { label: 'Lease Listings', icon: '🏬' },
  census: { label: 'Demographics', icon: '👥' },
  osm: { label: 'Competitors', icon: '☕' },
  vexcel: { label: 'Aerial & Parking', icon: '🛰️' },
  matterport: { label: '3D Walkthrough', icon: '📐' },
  sim: { label: 'Cash Flow Sim', icon: '🎲' },
  report: { label: 'Decision Brief', icon: '📑' },
}

export default function AgentLogPanel({ steps = DEFAULT_EXAMPLE_STEPS }: { steps?: AgentStep[] }) {
  const [collapsed, setCollapsed] = useState(false)
  const isAnyRunning = steps.some((s) => s.status === 'running')

  return (
    <aside
      className={`agent-log-panel editorial-card ${collapsed ? 'collapsed' : ''}`}
      aria-label="Behind the Location Investigation"
    >
      <div
        className="agent-log-header"
        onClick={() => setCollapsed(!collapsed)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setCollapsed(!collapsed)
          }
        }}
      >
        <div className="agent-header-title">
          <span className={`live-pulse-dot ${isAnyRunning ? 'is-running' : 'is-ready'}`} />
          <div className="agent-title-text">
            <span className="agent-log-kicker">BEHIND THE LOCATION</span>
            <strong className="agent-log-headline">Let's investigate this spot</strong>
          </div>
          <span className="step-count-pill">{steps.length} checks</span>
        </div>

        <button
          type="button"
          className="collapse-toggle-btn"
          aria-label={collapsed ? 'Expand investigation log' : 'Minimize investigation log'}
        >
          {collapsed ? '▲ Expand' : '▼ Minimize'}
        </button>
      </div>

      {!collapsed && (
        <div className="agent-log-body">
          <div className="investigation-intro">
            <SparkleDoodle size={14} color="#DA4324" />
            <span>Autonomous agent pipeline verifying leases, foot traffic, and cash flows:</span>
          </div>

          <div className="steps-scroll-container">
            {steps.map((s) => {
              const cfg = TOOL_CONFIG[s.tool] || { label: s.tool.toUpperCase(), icon: '🔍' }
              return (
                <div key={s.id} className={`log-entry status-${s.status}`}>
                  <div className="step-icon-col">
                    <span className="step-type-icon" title={cfg.label}>{cfg.icon}</span>
                  </div>

                  <div className="log-text-col">
                    <div className="step-tool-row">
                      <span className="tool-tag">{cfg.label}</span>
                      {s.siteAddress && <span className="site-tag">{s.siteAddress}</span>}
                    </div>
                    <span className="log-msg">{s.message}</span>
                  </div>

                  <div className="step-meta-col">
                    {s.durationMs && <span className="duration-tag">{s.durationMs}ms</span>}
                    <span className={`status-pill status-${s.status}`}>
                      {s.status === 'done' && '✓ Verified'}
                      {s.status === 'running' && '● Auditing'}
                      {s.status === 'error' && '✕ Alert'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </aside>
  )
}
