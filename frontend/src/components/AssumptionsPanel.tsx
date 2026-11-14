import { useState } from 'react'
import type { SimResult, Site } from '../types'

interface AssumptionsPanelProps {
  site: Site
  businessType?: string
  onSimResultUpdate: (newSim: SimResult | null) => void
  onClose?: () => void
}

interface OverridesState {
  rentMonthly: number
  ticket: number
  laborFixedMonthly: number
  startupCost: number
  cogsMid: number
  newCompetitors: boolean
  accessPenalty: boolean
}

export default function AssumptionsPanel({
  site,
  businessType = 'boba',
  onSimResultUpdate,
  onClose,
}: AssumptionsPanelProps) {
  const baseSim = site.sim
  const initialRent = site.rentMonthly ?? 5000
  const initialTicket = Number(baseSim?.assumptions?.ticket ?? baseSim?.assumptions?.avgTicket ?? 8.0)
  const initialLabor = Number(baseSim?.assumptions?.laborFixedMonthly ?? baseSim?.assumptions?.laborMonthly ?? 7000)
  const initialStartup = Number(baseSim?.assumptions?.startupCost ?? 110000)
  const initialCogsMin = Number(baseSim?.assumptions?.cogsMin ?? 0.25)
  const initialCogsMax = Number(baseSim?.assumptions?.cogsMax ?? 0.35)
  const initialCogsMid = Math.round(((initialCogsMin + initialCogsMax) / 2) * 100)

  const [form, setForm] = useState<OverridesState>({
    rentMonthly: initialRent,
    ticket: initialTicket,
    laborFixedMonthly: initialLabor,
    startupCost: initialStartup,
    cogsMid: initialCogsMid,
    newCompetitors: true,
    accessPenalty: true,
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasChanged, setHasChanged] = useState(false)
  const [simulatedOdds, setSimulatedOdds] = useState<number | null>(baseSim?.pProfitableBy12 ?? null)

  const handleReset = () => {
    setForm({
      rentMonthly: initialRent,
      ticket: initialTicket,
      laborFixedMonthly: initialLabor,
      startupCost: initialStartup,
      cogsMid: initialCogsMid,
      newCompetitors: true,
      accessPenalty: true,
    })
    setHasChanged(false)
    setSimulatedOdds(baseSim?.pProfitableBy12 ?? null)
    onSimResultUpdate(null) // reset to base
  }

  const runWhatIf = async (currentForm: OverridesState) => {
    setLoading(true)
    setError(null)
    try {
      const cogsFraction = currentForm.cogsMid / 100
      const overrides = {
        rentMonthly: currentForm.rentMonthly,
        ticket: currentForm.ticket,
        laborFixedMonthly: currentForm.laborFixedMonthly,
        startupCost: currentForm.startupCost,
        cogsMin: Math.max(0.05, cogsFraction - 0.05),
        cogsMax: Math.min(0.70, cogsFraction + 0.05),
        newCompetitors: currentForm.newCompetitors,
        accessPenalty: currentForm.accessPenalty,
      }

      const res = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site,
          businessType,
          overrides,
        }),
      })

      if (!res.ok) {
        throw new Error(`Simulation returned status ${res.status}`)
      }

      const updatedSim: SimResult = await res.json()
      setSimulatedOdds(updatedSim.pProfitableBy12)
      setHasChanged(true)
      onSimResultUpdate(updatedSim)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  const updateField = <K extends keyof OverridesState>(key: K, value: OverridesState[K]) => {
    const updated = { ...form, [key]: value }
    setForm(updated)
    runWhatIf(updated)
  }

  const baseOdds = baseSim?.pProfitableBy12 ?? 0
  const currentOdds = simulatedOdds ?? baseOdds
  const oddsDiff = Math.round((currentOdds - baseOdds) * 100)

  return (
    <div className="assumptions-panel">
      <div className="assumptions-header">
        <div className="header-left">
          <h4>What-If Assumptions</h4>
          <span className="subtitle">Tune economic levers to see outcome changes</span>
        </div>
        {onClose && (
          <button type="button" className="close-btn" onClick={onClose} aria-label="Close assumptions">
            ✕
          </button>
        )}
      </div>

      {/* Real-time comparison delta badge */}
      <div className="what-if-delta">
        <div className="delta-stat">
          <span className="delta-label">Month 12 Odds:</span>
          <span className="delta-value">
            {Math.round(currentOdds * 100)}%
            {hasChanged && oddsDiff !== 0 && (
              <span className={`diff-pill ${oddsDiff > 0 ? 'pos' : 'neg'}`}>
                {oddsDiff > 0 ? `+${oddsDiff}%` : `${oddsDiff}%`}
              </span>
            )}
          </span>
        </div>
        {loading && <span className="sim-spinner">Re-simulating...</span>}
      </div>

      {error && <div className="sim-error">{error}</div>}

      <div className="levers-grid">
        {/* Rent input */}
        <div className="lever-control">
          <div className="lever-label-row">
            <label htmlFor={`rent-${site.id}`}>Monthly Rent</label>
            <span className="lever-val">${form.rentMonthly.toLocaleString()}/mo</span>
          </div>
          <input
            id={`rent-${site.id}`}
            type="range"
            min={1000}
            max={15000}
            step={250}
            value={form.rentMonthly}
            onChange={(e) => updateField('rentMonthly', Number(e.target.value))}
          />
        </div>

        {/* Average Ticket */}
        <div className="lever-control">
          <div className="lever-label-row">
            <label htmlFor={`ticket-${site.id}`}>Average Ticket</label>
            <span className="lever-val">${form.ticket.toFixed(2)}</span>
          </div>
          <input
            id={`ticket-${site.id}`}
            type="range"
            min={4.0}
            max={35.0}
            step={0.5}
            value={form.ticket}
            onChange={(e) => updateField('ticket', Number(e.target.value))}
          />
        </div>

        {/* Fixed Monthly Labor */}
        <div className="lever-control">
          <div className="lever-label-row">
            <label htmlFor={`labor-${site.id}`}>Fixed Labor / Mo</label>
            <span className="lever-val">${form.laborFixedMonthly.toLocaleString()}/mo</span>
          </div>
          <input
            id={`labor-${site.id}`}
            type="range"
            min={2000}
            max={35000}
            step={500}
            value={form.laborFixedMonthly}
            onChange={(e) => updateField('laborFixedMonthly', Number(e.target.value))}
          />
        </div>

        {/* Cost of Goods Sold (COGS %) */}
        <div className="lever-control">
          <div className="lever-label-row">
            <label htmlFor={`cogs-${site.id}`}>Cost of Goods (COGS)</label>
            <span className="lever-val">{form.cogsMid}%</span>
          </div>
          <input
            id={`cogs-${site.id}`}
            type="range"
            min={10}
            max={65}
            step={1}
            value={form.cogsMid}
            onChange={(e) => updateField('cogsMid', Number(e.target.value))}
          />
        </div>

        {/* Startup Fitout Cost */}
        <div className="lever-control">
          <div className="lever-label-row">
            <label htmlFor={`startup-${site.id}`}>Startup / Fitout</label>
            <span className="lever-val">${(form.startupCost / 1000).toFixed(0)}k</span>
          </div>
          <input
            id={`startup-${site.id}`}
            type="range"
            min={30000}
            max={400000}
            step={5000}
            value={form.startupCost}
            onChange={(e) => updateField('startupCost', Number(e.target.value))}
          />
        </div>
      </div>

      {/* Model Factor Switches */}
      <div className="switches-row">
        <label className="switch-item">
          <input
            type="checkbox"
            checked={form.newCompetitors}
            onChange={(e) => updateField('newCompetitors', e.target.checked)}
          />
          <span>Model new competitor openings</span>
        </label>

        <label className="switch-item">
          <input
            type="checkbox"
            checked={form.accessPenalty}
            onChange={(e) => updateField('accessPenalty', e.target.checked)}
          />
          <span>Apply road/access handicap</span>
        </label>
      </div>

      {/* Reset button */}
      <div className="panel-actions">
        <button
          type="button"
          className="reset-btn"
          disabled={!hasChanged || loading}
          onClick={handleReset}
        >
          Reset to Baseline
        </button>
      </div>
    </div>
  )
}
