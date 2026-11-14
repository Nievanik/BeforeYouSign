import { useState } from 'react'
import type { Band, MonthBand } from '../types'

interface ProfitFanProps {
  monthlyBands: MonthBand[]
  profitM12?: Band
  paybackMonths?: number | null
  expectedCustomers?: number
  breakEvenCustomers?: number
}

const usd = (n: number) => {
  const sign = n < 0 ? '-' : '+'
  const abs = Math.abs(Math.round(n))
  return `${sign}$${abs.toLocaleString()}`
}

const fmtK = (n: number) => {
  const sign = n < 0 ? '-' : ''
  const abs = Math.abs(n)
  if (abs >= 1000) {
    return `${sign}$${(abs / 1000).toFixed(abs % 1000 === 0 ? 0 : 1)}k`
  }
  return `${sign}$${Math.round(abs)}`
}

export default function ProfitFan({
  monthlyBands,
  profitM12,
  paybackMonths,
  expectedCustomers,
  breakEvenCustomers,
}: ProfitFanProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  if (!monthlyBands || monthlyBands.length === 0) {
    return <p className="gaps">No monthly profit projection available</p>
  }

  // Chart Dimensions
  const width = 340
  const height = 180
  const padLeft = 46
  const padRight = 14
  const padTop = 16
  const padBottom = 26

  const plotW = width - padLeft - padRight
  const plotH = height - padTop - padBottom

  // Bounds
  const allValues = monthlyBands.flatMap((b) => [b.p10, b.p50, b.p90])
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)

  // Ensure $0 line is included in range for visual perspective
  const yMin = Math.min(rawMin, 0) * 1.1
  const yMax = Math.max(rawMax, 0) * 1.15
  const ySpan = yMax - yMin || 1

  const getX = (m: number) => padLeft + ((m - 1) / (monthlyBands.length - 1)) * plotW
  const getY = (v: number) => padTop + plotH - ((v - yMin) / ySpan) * plotH

  // Generate fan area path (P90 forward, P10 reverse)
  const p90Points = monthlyBands.map((b) => `${getX(b.month)},${getY(b.p90)}`).join(' L ')
  const p10PointsReverse = [...monthlyBands]
    .reverse()
    .map((b) => `${getX(b.month)},${getY(b.p10)}`)
    .join(' L ')
  const fanPath = `M ${p90Points} L ${p10PointsReverse} Z`

  // Generate P50 line path
  const p50Path = monthlyBands
    .map((b, i) => `${i === 0 ? 'M' : 'L'} ${getX(b.month)},${getY(b.p50)}`)
    .join(' ')

  // Month 12 index
  const m12Data = monthlyBands.find((b) => b.month === 12)
  const m12P50 = profitM12?.p50 ?? m12Data?.p50
  const m12X = m12Data ? getX(12) : null
  const m12Y = m12P50 != null ? getY(m12P50) : null

  // Active hover data or default to Month 12
  const activeBand = hoveredIdx !== null ? monthlyBands[hoveredIdx] : m12Data ?? monthlyBands[monthlyBands.length - 1]

  // Y-ticks
  const yTicks = [yMin * 0.9, 0, yMax * 0.85]

  return (
    <div className="profit-fan">
      <div className="profit-fan-header">
        <h4>Monthly Profit Projection (24 Mo)</h4>
        <div className="profit-fan-legend">
          <span className="legend-band">
            <span className="legend-swatch band-swatch" />
            P10–P90
          </span>
          <span className="legend-median">
            <span className="legend-swatch line-swatch" />
            P50 Median
          </span>
        </div>
      </div>

      <div className="chart-container">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="fan-svg"
          onMouseLeave={() => setHoveredIdx(null)}
        >
          <defs>
            <linearGradient id="fanGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#2563eb" stopOpacity="0.06" />
            </linearGradient>
            <linearGradient id="p50Grad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#1d4ed8" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {yTicks.map((tick, i) => {
            const y = getY(tick)
            return (
              <g key={i}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke={tick === 0 ? '#dc2626' : '#e5e7eb'}
                  strokeDasharray={tick === 0 ? '3 3' : 'none'}
                  strokeWidth={tick === 0 ? 1.5 : 1}
                />
                <text
                  x={padLeft - 6}
                  y={y + 3.5}
                  textAnchor="end"
                  fontSize="9"
                  fill={tick === 0 ? '#b91c1c' : '#6b7280'}
                  fontWeight={tick === 0 ? '600' : 'normal'}
                >
                  {fmtK(tick)}
                </text>
              </g>
            )
          })}

          {/* Month 12 highlight line */}
          {m12X !== null && (
            <line
              x1={m12X}
              y1={padTop}
              x2={m12X}
              y2={height - padBottom}
              stroke="#9333ea"
              strokeDasharray="2 2"
              strokeWidth="1.2"
              opacity="0.75"
            />
          )}

          {/* Fan area (P10 to P90) */}
          <path d={fanPath} fill="url(#fanGrad)" />

          {/* Median line (P50) */}
          <path
            d={p50Path}
            fill="none"
            stroke="url(#p50Grad)"
            strokeWidth="2.2"
            strokeLinecap="round"
          />

          {/* Month 12 point */}
          {m12X !== null && m12Y !== null && (
            <circle cx={m12X} cy={m12Y} r="3.5" fill="#9333ea" stroke="#fff" strokeWidth="1.5" />
          )}

          {/* Hover highlight line & dot */}
          {hoveredIdx !== null && activeBand && (
            <g>
              <line
                x1={getX(activeBand.month)}
                y1={padTop}
                x2={getX(activeBand.month)}
                y2={height - padBottom}
                stroke="#1f2937"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <circle
                cx={getX(activeBand.month)}
                cy={getY(activeBand.p50)}
                r="4"
                fill="#2563eb"
                stroke="#fff"
                strokeWidth="2"
              />
            </g>
          )}

          {/* Transparent hit boxes for scrubbing months */}
          {monthlyBands.map((b, i) => {
            const x = getX(b.month) - plotW / (monthlyBands.length * 2)
            const w = plotW / monthlyBands.length
            return (
              <rect
                key={b.month}
                x={x}
                y={padTop}
                width={w}
                height={plotH}
                fill="transparent"
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredIdx(i)}
              />
            )
          })}

          {/* X axis ticks */}
          {[1, 6, 12, 18, 24].map((m) => {
            const x = getX(m)
            const isM12 = m === 12
            return (
              <text
                key={m}
                x={x}
                y={height - padBottom + 14}
                textAnchor="middle"
                fontSize="9.5"
                fill={isM12 ? '#9333ea' : '#6b7280'}
                fontWeight={isM12 ? 'bold' : 'normal'}
              >
                M{m}
              </text>
            )
          })}
        </svg>
      </div>

      {/* Interactive / Month 12 Metric readout */}
      {activeBand && (
        <div className="band-readout">
          <div className="readout-headline">
            <span className="readout-month">
              Month {activeBand.month}
              {activeBand.month === 12 && ' (Target)'}:
            </span>{' '}
            <strong className={activeBand.p50 >= 0 ? 'profit-pos' : 'profit-neg'}>
              {usd(activeBand.p50)}/mo
            </strong>{' '}
            <span className="readout-range">
              ({usd(activeBand.p10)} to {usd(activeBand.p90)})
            </span>
          </div>

          <div className="readout-sub">
            {expectedCustomers != null && breakEvenCustomers != null && (
              <span>
                Break-even: <strong>{Math.round(breakEvenCustomers)}</strong> cust/day · Expected:{' '}
                <strong>{Math.round(expectedCustomers)}</strong>
              </span>
            )}
            {paybackMonths != null && (
              <span>
                Payback: <strong>{paybackMonths} mo</strong>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
