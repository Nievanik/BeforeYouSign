import type { Site } from '../types'

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

export default function SiteCard({ site, rank }: { site: Site; rank: number }) {
  const a = site.aerial
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
          <img src={a.imageUrl} alt={`Aerial view of ${site.address}; parcel in gold, detected parking in cyan`} loading="lazy" />
          <figcaption>
            {parkingText(site)}
            <br />
            <small>Imagery © Vexcel Imaging US, Inc.</small>
          </figcaption>
        </figure>
      )}
      {a?.roadAccessScore != null && <p>Road access {a.roadAccessScore}/5: {a.roadAccessReason}</p>}
      {site.gaps.length > 0 && <p className="gaps">Missing: {site.gaps.join(' · ')}</p>}
    </article>
  )
}
