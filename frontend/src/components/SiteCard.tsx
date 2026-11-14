import { useState } from 'react'
import type { Site } from '../types'
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

const ABBR: Record<string, string> = { north: 'N', east: 'E', south: 'S', west: 'W' }

export default function SiteCard({ site, rank }: { site: Site; rank: number }) {
  const a = site.aerial
  const [view, setView] = useState('above') // "above" or an oblique direction
  // oblique-north = camera facing north, so it shows the building's south side
  const src = view === 'above' ? a?.imageUrl : `/api/sites/${site.id}/oblique/${view}.jpg`
  return (
    <article className="card">
      <h2>
        #{rank} {site.address}
      </h2>
      {site.sim && (
        <p className="odds">{Math.round(site.sim.pProfitableBy12 * 100)}% chance of profit by month 12</p>
      )}
      <p>
        {site.rentMonthly != null ? `${usd(site.rentMonthly)}/mo` : 'Rent not given'} · {site.sizeSqft.toLocaleString()} sq ft
        {site.interior && ` · ~${site.interior.estSeats} seats`}
      </p>
      {a && (
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
            alt={view === 'above'
              ? `Aerial view of ${site.address}; parcel in gold, detected parking in cyan`
              : `Angled aerial photo of ${site.address}, camera looking ${view}`}
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
      )}
      {site.matterportModelId ? (
        <TourEmbed modelId={site.matterportModelId} buildingScan={site.gaps.includes('3D scan is of the whole building')} />
      ) : (
        <p className="gaps">No 3D scan for this property</p>
      )}
      {a?.roadAccessScore != null && <p>Road access {a.roadAccessScore}/5: {a.roadAccessReason}</p>}
      {site.gaps.length > 0 && <p className="gaps">Missing: {site.gaps.join(' · ')}</p>}
    </article>
  )
}
