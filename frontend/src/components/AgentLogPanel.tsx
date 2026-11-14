import { useState } from 'react'

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

const TOOL_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  plan: { bg: '#e0e7ff', text: '#3730a3', label: 'PLAN' },
  costar: { bg: '#dbeafe', text: '#1e40af', label: 'COSTAR' },
  census: { bg: '#fef3c7', text: '#92400e', label: 'CENSUS' },
  osm: { bg: '#fce7f3', text: '#9d174d', label: 'OSM' },
  vexcel: { bg: '#dcfce7', text: '#166534', label: 'VEXCEL' },
  matterport: { bg: '#ede9fe', text: '#5b21b6', label: 'MATTERPORT' },
  sim: { bg: '#ffedd5', text: '#9a3412', label: 'SIMULATION' },
  report: { bg: '#f3f4f6', text: '#1f2937', label: 'REPORT' },
}

export default function AgentLogPanel({ steps = DEFAULT_EXAMPLE_STEPS }: { steps?: AgentStep[] }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className={`agent-log-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="agent-log-header" onClick={() => setCollapsed(!collapsed)}>
        <div className="agent-header-title">
          <span className="live-indicator" />
          <strong>Agent Investigation Log</strong>
          <span className="step-count">({steps.length} steps)</span>
        </div>
        <button
          type="button"
          className="collapse-toggle"
          aria-label={collapsed ? 'Expand agent log' : 'Collapse agent log'}
        >
          {collapsed ? '▲ Expand' : '▼ Minimize'}
        </button>
      </div>

      {!collapsed && (
        <div className="agent-log-body">
          {steps.map((s) => {
            const badge = TOOL_COLORS[s.tool] || { bg: '#f3f4f6', text: '#333', label: s.tool.toUpperCase() }
            return (
              <div key={s.id} className={`log-entry status-${s.status}`}>
                <div className="log-badge-col">
                  <span
                    className="tool-tag"
                    style={{ backgroundColor: badge.bg, color: badge.text }}
                  >
                    {badge.label}
                  </span>
                </div>
                <div className="log-text-col">
                  <span className="log-msg">{s.message}</span>
                  {s.siteAddress && <span className="site-tag">{s.siteAddress}</span>}
                </div>
                {s.durationMs && (
                  <span className="duration-tag">{s.durationMs}ms</span>
                )}
                <span className="status-icon">
                  {s.status === 'done' && '✓'}
                  {s.status === 'running' && '⏳'}
                  {s.status === 'error' && '✕'}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
