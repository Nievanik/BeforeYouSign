import { useState } from 'react'
import type { SimResult, Site } from '../types'
import AssumptionsPanel from './AssumptionsPanel'
import ProfitFan from './ProfitFan'
import TourEmbed from './TourEmbed'

const usd = (n: number) => `$${Math.round(n).toLocaleString()}`

function parkingText(site: Site): string {
  const a = site.aerial
  if (!a) return 'No aerial image'
  const year = a.collection?.match(/(20\d\d)/)?.[1]
  const photo = year ? `one ${year} photo` : 'one photo'
  return a.parkingSeen != null
    ? `About ${a.parkingSeen} spaces on the lot (estimated from ${photo}; may be shared with other tenants)`
    : `Parking areas outlined on the photo; count unclear from ${photo}`
}

function oddsColor(odds: number): string {
  if (odds >= 0.6) return '#16a34a' // Green
  if (odds >= 0.4) return '#d97706' // Amber
  return '#dc2626' // Red
}

function oddsBg(odds: number): string {
  if (odds >= 0.6) return '#f0fdf4'
  if (odds >= 0.4) return '#fffbeb'
  return '#fef2f2'
}

const ABBR: Record<string, string> = { north: 'N', east: 'E', south: 'S', west: 'W' }

export default function SiteCard({ site, rank }: { site: Site; rank: number }) {
  const a = site.aerial
  const [view, setView] = useState('above') // "above" or an oblique direction
  const [showChart, setShowChart] = useState(true)
  const [showAssumptions, setShowAssumptions] = useState(false)
  const [overrideSim, setOverrideSim] = useState<SimResult | null>(null)

  const currentSim = overrideSim ?? site.sim
  const odds = currentSim?.pProfitableBy12 ?? 0
  const color = oddsColor(odds)
  const src = view === 'above' ? a?.imageUrl : `/api/sites/${site.id}/oblique/${view}.jpg`

  return (
    <article className="card">
      <div className="card-header">
        <h2>
          #{rank} {site.address}
        </h2>
        <button
          type="button"
          className={`assumptions-btn ${overrideSim ? 'has-overrides' : ''}`}
          onClick={() => setShowAssumptions(!showAssumptions)}
          aria-expanded={showAssumptions}
          title="Tweak economic assumptions and test what-if scenarios"
        >
          ⚙️ {showAssumptions ? 'Close Levers' : 'What-If Levers'}
          {overrideSim && <span className="override-indicator">Active</span>}
        </button>
      </div>

      {/* Visual Odds Bar & Headline */}
      {currentSim ? (
        <div className="odds-section" style={{ backgroundColor: oddsBg(odds) }}>
          <div className="odds-header">
            <span className="odds-pct" style={{ color }}>
              {Math.round(odds * 100)}%
            </span>
            <span className="odds-label">chance of profit by month 12</span>
            {overrideSim && <span className="custom-tag">What-If scenario</span>}
          </div>

          <div
            className="odds-bar-track"
            role="progressbar"
            aria-valuenow={Math.round(odds * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="odds-bar-fill"
              style={{
                width: `${Math.max(4, Math.round(odds * 100))}%`,
                backgroundColor: color,
              }}
            />
          </div>

          <div className="odds-badges">
            <span className="badge">
              Median profit:{' '}
              {currentSim.medianMonthProfitable
                ? `Month ${currentSim.medianMonthProfitable}`
                : 'Not in 24 mo'}
            </span>
            {currentSim.paybackMonths != null && (
              <span className="badge">Payback: ~{currentSim.paybackMonths} mo</span>
            )}
            {currentSim.rentShare != null && (
              <span className="badge">Rent: {Math.round(currentSim.rentShare * 100)}% of rev</span>
            )}
          </div>
        </div>
      ) : (
        <div className="missing-state">Simulation data pending</div>
      )}

      {/* Assumptions / What-If Panel Drawer */}
      {showAssumptions && (
        <AssumptionsPanel
          site={site}
          onSimResultUpdate={setOverrideSim}
          onClose={() => setShowAssumptions(false)}
        />
      )}

      {/* Property & Rent Specs */}
      <div className="specs-row">
        {site.rentMonthly != null ? (
          <span className="spec-item spec-rent">
            <strong>{usd(overrideSim ? (overrideSim.assumptions.rentMonthly as number) : site.rentMonthly)}</strong>/mo
          </span>
        ) : (
          <span className="missing-pill">Rent not given</span>
        )}
        <span className="spec-sep">·</span>
        <span className="spec-item">{site.sizeSqft.toLocaleString()} sq ft</span>
        {site.interior?.estSeats != null && (
          <>
            <span className="spec-sep">·</span>
            <span className="spec-item">~{site.interior.estSeats} seats</span>
          </>
        )}
      </div>

      {/* Profit Fan Chart toggle */}
      {currentSim && currentSim.monthlyBands && (
        <div className="fan-chart-wrapper">
          <button
            type="button"
            className="toggle-btn"
            onClick={() => setShowChart(!showChart)}
            aria-expanded={showChart}
          >
            {showChart ? 'Hide monthly profit fan chart ▲' : 'Show monthly profit fan chart ▼'}
          </button>
          {showChart && (
            <ProfitFan
              monthlyBands={currentSim.monthlyBands}
              profitM12={currentSim.profitM12}
              paybackMonths={currentSim.paybackMonths}
              expectedCustomers={currentSim.expectedCustomers}
              breakEvenCustomers={currentSim.breakEvenCustomers}
            />
          )}
        </div>
      )}

      {/* Top Risk Factors */}
      {currentSim?.riskFactors && currentSim.riskFactors.length > 0 && (
        <div className="risk-section">
          <h3>Top Risk Factors</h3>
          <ul className="risk-list">
            {currentSim.riskFactors.map((r, i) => (
              <li key={i} className="risk-item">
                <span className="risk-impact" title={`Impact: ${(r.impact * 100).toFixed(0)}%`}>
                  {(r.impact * 100).toFixed(0)}%
                </span>
                <span className="risk-text">{r.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Aerial Imagery (Vexcel) */}
      {a ? (
        <figure>
          {a.obliqueDirections.length > 0 && (
            <div className="views" role="group" aria-label="Photo angle">
              {['above', ...a.obliqueDirections].map((d) => (
                <button type="button" key={d} aria-pressed={view === d} onClick={() => setView(d)}>
                  {d === 'above' ? 'From above' : `Looking ${ABBR[d] ?? d}`}
                </button>
              ))}
            </div>
          )}
          <img
            src={src}
            alt={
              view === 'above'
                ? `Aerial view of ${site.address}; parcel in gold, detected parking in cyan`
                : `Angled aerial photo of ${site.address}, camera looking ${view}`
            }
            loading="lazy"
          />
          <figcaption>
            {view === 'above' && (
              <>
                {parkingText(site)}
                <br />
              </>
            )}
            <small>Imagery © Vexcel Imaging US, Inc.</small>
          </figcaption>
        </figure>
      ) : (
        <p className="missing-state">No aerial imagery available</p>
      )}

      {a?.roadAccessScore != null && (
        <p className="access-score">
          <strong>Road access {a.roadAccessScore}/5:</strong> {a.roadAccessReason}
        </p>
      )}

      {/* 3D Scan & Floor plan (Matterport) */}
      {site.interior?.summary && <p className="summary">{site.interior.summary}</p>}
      {site.matterportModelId && (
        <details className="floorplan-details">
          <summary>Floor plan</summary>
          <img
            src={`/api/sites/${site.id}/floorplan.jpg`}
            alt={`Floor plan of the 3D scan at ${site.address}`}
            loading="lazy"
          />
        </details>
      )}

      {site.matterportModelId ? (
        <TourEmbed
          modelId={site.matterportModelId}
          buildingScan={site.gaps.includes('3D scan is of the whole building')}
        />
      ) : (
        <p className="missing-state">No 3D scan for this property</p>
      )}

      {/* Missing data gaps */}
      {site.gaps.length > 0 && (
        <p className="gaps">
          <strong>Data notes:</strong> {site.gaps.join(' · ')}
        </p>
      )}
    </article>
  )
}
