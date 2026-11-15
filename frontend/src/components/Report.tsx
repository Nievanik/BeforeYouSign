import type { RunResult, Site } from '../types'
import AgentReport from './AgentReport'

interface ReportProps {
  run: RunResult
  onClose: () => void
}

const usd = (n: number) => `$${Math.round(n).toLocaleString()}`

export default function Report({ run, onClose }: ReportProps) {
  const { brief, sites } = run
  const topSite: Site | undefined = sites[0]
  const rentShareMax = Number(topSite?.sim?.assumptions?.rentShareMax ?? 0.15) // the business's own benchmark

  const handlePrint = () => {
    window.print()
  }

  return (
    <div className="report-overlay" role="dialog" aria-modal="true" aria-labelledby="report-title">
      <div className="report-modal">
        {/* Screen Action Bar (hidden in print) */}
        <header className="report-actions-bar no-print">
          <div className="bar-left">
            <span className="badge-tag">Executive Summary</span>
            <span className="report-meta">
              {brief.businessType.toUpperCase()} · {brief.city}
            </span>
          </div>
          <div className="bar-right">
            <button type="button" className="print-btn" onClick={handlePrint}>
              🖨️ Print / Save as PDF
            </button>
            <button type="button" className="close-report-btn" onClick={onClose} aria-label="Close report">
              ✕
            </button>
          </div>
        </header>

        {/* Printable One-Page Document */}
        <div className="printable-report">
          {/* Document Header */}
          <div className="doc-header">
            <div>
              <h1 id="report-title">BeforeYouSign: Site Selection Report</h1>
              <p className="doc-sub">
                Target: <strong>{brief.businessType.toUpperCase()}</strong> in <strong>{brief.city}</strong> · Max Budget:{' '}
                <strong>${brief.maxRentMonthly.toLocaleString()}/mo</strong>
                {brief.mustHaves?.length > 0 && ` · Must-haves: ${brief.mustHaves.join(', ')}`}
              </p>
            </div>
            <div className="doc-date">
              <span>Date: {new Date(run.createdAt || Date.now()).toLocaleDateString()}</span>
              <span>Run ID: {run.runId}</span>
            </div>
          </div>

          <hr className="doc-divider" />

          {/* Top Pick Highlight Card */}
          {topSite && topSite.sim && (
            <div className="top-pick-card">
              <div className="top-pick-badge">🏆 TOP RECOMMENDATION</div>
              <div className="top-pick-grid">
                <div>
                  <h2 className="top-address">#1 {topSite.address}</h2>
                  <p className="top-specs">
                    {topSite.rentMonthly != null ? `${usd(topSite.rentMonthly)}/mo` : 'Rent unlisted'} ·{' '}
                    {topSite.sizeSqft.toLocaleString()} sq ft
                    {topSite.interior?.estSeats != null && ` · ~${topSite.interior.estSeats} seats`}
                  </p>
                </div>
                <div className="top-metrics">
                  <div className="metric-box">
                    <span className="metric-val">{Math.round(topSite.sim.pProfitableBy12 * 100)}%</span>
                    <span className="metric-lbl">Month 12 Odds</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-val">~{Math.round(topSite.sim.expectedCustomers)}</span>
                    <span className="metric-lbl">Expected Cust/Day</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-val">{Math.round(topSite.sim.breakEvenCustomers)}</span>
                    <span className="metric-lbl">Break-Even Cust/Day</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-val">{topSite.sim.paybackMonths ?? '36+'} mo</span>
                    <span className="metric-lbl">Est. Payback</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {run.report && (
            <section className="report-section">
              <h3>Analyst Agent's Recommendation</h3>
              <AgentReport markdown={run.report} />
            </section>
          )}

          {/* Comparative Ranking Table */}
          <section className="report-section">
            <h3>Comparative Candidate Ranking</h3>
            <table className="ranking-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Location</th>
                  <th>Month 12 Odds</th>
                  <th>Rent / Mo</th>
                  <th>Exp. Demand</th>
                  <th>Break-Even</th>
                  <th>Rent % Rev</th>
                  <th>Primary Risk Factor</th>
                </tr>
              </thead>
              <tbody>
                {sites.map((s, i) => {
                  const sim = s.sim
                  const odds = sim ? Math.round(sim.pProfitableBy12 * 100) : null
                  const primaryRisk = sim?.riskFactors?.[0]?.text ?? 'None identified'
                  return (
                    <tr key={s.id} className={i === 0 ? 'top-row' : ''}>
                      <td>
                        <strong>#{i + 1}</strong>
                      </td>
                      <td className="addr-cell">{s.address}</td>
                      <td>
                        <strong className={odds && odds >= 60 ? 'pos' : ''}>{odds != null ? `${odds}%` : 'N/A'}</strong>
                      </td>
                      <td>{s.rentMonthly != null ? usd(s.rentMonthly) : 'Unlisted'}</td>
                      <td>{sim ? `~${Math.round(sim.expectedCustomers)}/day` : 'N/A'}</td>
                      <td>{sim ? `${Math.round(sim.breakEvenCustomers)}/day` : 'N/A'}</td>
                      <td>{sim?.rentShare != null ? `${Math.round(sim.rentShare * 100)}%` : 'N/A'}</td>
                      <td className="risk-cell">{primaryRisk}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </section>

          {/* Why Site #1 Won & Core Strengths */}
          {topSite && topSite.sim && (
            <section className="report-section strengths-section">
              <h3>Key Decision Drivers for #1</h3>
              <div className="strengths-grid">
                <div className="strength-item">
                  <strong>Customer Cushion:</strong> Requires {Math.round(topSite.sim.breakEvenCustomers)} customers/day
                  to cover fixed expenses. Modeled customer pull is ~{Math.round(topSite.sim.expectedCustomers)}/day
                  {topSite.sim.expectedCustomers > topSite.sim.breakEvenCustomers
                    ? `, a ${Math.round((topSite.sim.expectedCustomers / topSite.sim.breakEvenCustomers - 1) * 100)}% cushion.`
                    : ': below break-even, so profit depends on beating the model.'}
                </div>
                <div className="strength-item">
                  <strong>Rent Ratio:</strong> Rent is {Math.round(topSite.sim.rentShare * 100)}% of expected revenue
                  {topSite.sim.rentShare <= rentShareMax
                    ? `, within the ${Math.round(rentShareMax * 100)}% benchmark for this business.`
                    : `, above the ${Math.round(rentShareMax * 100)}% benchmark for this business.`}
                </div>
                <div className="strength-item">
                  <strong>Access & Parking:</strong>{' '}
                  {topSite.parkingAvailable
                    ? `CoStar records ${topSite.parkingSpaces ? `${topSite.parkingSpaces.toLocaleString()} parking spaces` : 'parking'} at this property`
                    : 'Parking is not recorded for this property; confirm it in person'}
                  {topSite.aerial?.roadAccessScore != null &&
                    `; road access scored ${topSite.aerial.roadAccessScore}/5 from the aerial photo`}
                  .
                </div>
              </div>
            </section>
          )}

          {/* Key Risks & Negotiating Points */}
          <section className="report-section">
            <h3>Lease Negotiations & Mitigations</h3>
            <ul className="risks-summary-list">
              {sites.slice(0, 3).map((s, i) => {
                const risks = s.sim?.riskFactors ?? []
                return (
                  <li key={s.id}>
                    <strong>
                      #{i + 1} {s.address}:
                    </strong>{' '}
                    {risks.length > 0
                      ? risks.map((r) => `${r.text} (${Math.round(r.impact * 100)}% sensitivity)`).join('; ')
                      : 'Standard retail operating risks.'}
                  </li>
                )
              })}
            </ul>
          </section>

          {/* Methodology & Honesty Disclosure */}
          <footer className="doc-footer">
            <div className="assumptions-note">
              <strong>Modeling Methodology & Benchmark Assumptions:</strong> Projections derived from 1,000 Monte
              Carlo iterations over a 24-month horizon integrating CoStar commercial property listings, US Census ACS 5-Year
              demographic commute patterns, and Vexcel aerial imagery.
            </div>
            <div className="honesty-disclaimer">
              <em>
                *Honesty Disclosure: The comparative ranking between sites is the primary decision signal. Exact dollar
                figures reflect benchmark operational assumptions and local market conditions.
              </em>
            </div>
          </footer>
        </div>
      </div>
    </div>
  )
}
