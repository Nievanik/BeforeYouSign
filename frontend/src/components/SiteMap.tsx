import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import type { Competitor, Site } from '../types'

maplibregl.setWorkerUrl(workerUrl)

const HOUSTON: [number, number] = [-95.3698, 29.7604]

interface SiteMapProps {
  sites: Site[]
  selectedSiteId?: string
  onSelectSite?: (siteId: string) => void
}

export default function SiteMap({ sites, selectedSiteId, onSelectSite }: SiteMapProps) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const [showCompetitors, setShowCompetitors] = useState(true)
  const [showComplements, setShowComplements] = useState(true)

  // Initialize Map
  useEffect(() => {
    const m = new maplibregl.Map({
      container: el.current!,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: HOUSTON,
      zoom: 12,
      pitch: 45,
    })
    m.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
    m.addControl(new maplibregl.FullscreenControl(), 'top-right')
    m.on('error', (e) => console.error('map error', e.error))
    map.current = m
    return () => m.remove()
  }, [])

  // Update Markers (Sites + Competitors + Complements)
  useEffect(() => {
    const m = map.current
    if (!m || sites.length === 0) return
    const markers: maplibregl.Marker[] = []
    const bounds = new maplibregl.LngLatBounds()

    // 1. Candidate Site Markers
    sites.forEach((s, i) => {
      bounds.extend([s.lon, s.lat])

      const isSelected = selectedSiteId === s.id
      const markerEl = document.createElement('div')
      markerEl.className = `site-pin rank-${i + 1} ${isSelected ? 'is-selected' : ''}`
      markerEl.innerHTML = `<span class="pin-number">#${i + 1}</span>`
      markerEl.title = `${s.address}`

      if (onSelectSite) {
        markerEl.addEventListener('click', (ev) => {
          ev.stopPropagation()
          onSelectSite(s.id)
        })
      }

      const odds = s.sim
        ? `${Math.round(s.sim.pProfitableBy12 * 100)}% profit odds by Month 12`
        : 'Simulation pending'
      const rent = s.rentMonthly ? `$${Math.round(s.rentMonthly).toLocaleString()}/mo` : 'Rent unlisted'

      const popupHtml = `
        <div class="map-popup site-popup">
          <div class="popup-top-badge">
            <span class="badge-dot">●</span> Candidate #${i + 1}
          </div>
          <h4 class="popup-address">${s.address}</h4>
          <div class="popup-specs">
            <span class="spec-rent">${rent}</span>
            <span class="spec-sep">·</span>
            <span class="spec-size">${s.sizeSqft.toLocaleString()} sq ft</span>
          </div>
          <div class="popup-odds-box">
            <span class="odds-spark">✦</span>
            <span>${odds}</span>
          </div>
        </div>
      `

      const popup = new maplibregl.Popup({ offset: 24, closeButton: false }).setHTML(popupHtml)
      const marker = new maplibregl.Marker({ element: markerEl })
        .setLngLat([s.lon, s.lat])
        .setPopup(popup)
        .addTo(m)

      markers.push(marker)
    })

    // 2. Competitors & Complements from all sites
    const seenComp = new Set<string>()
    const allComps: { comp: Competitor; siteAddress: string }[] = []

    sites.forEach((site) => {
      site.competitors?.forEach((c) => {
        const key = `${c.name}_${c.lat.toFixed(4)}_${c.lon.toFixed(4)}`
        if (!seenComp.has(key)) {
          seenComp.add(key)
          allComps.push({ comp: c, siteAddress: site.address })
        }
      })
    })

    allComps.forEach(({ comp, siteAddress }) => {
      const isComp = comp.kind === 'competitor'
      const isCompl = comp.kind === 'complement'

      if (isComp && !showCompetitors) return
      if (isCompl && !showComplements) return
      if (!isComp && !isCompl) return

      const markerEl = document.createElement('div')
      markerEl.className = `comp-pin ${isComp ? 'comp-pin-competitor' : 'comp-pin-complement'}`
      markerEl.title = `${comp.name} (${comp.kind})`

      const ratingText = comp.rating
        ? `★ ${comp.rating.toFixed(1)}${comp.reviewCount ? ` (${comp.reviewCount} reviews)` : ''}`
        : 'Rating unlisted'

      const kindLabel = isComp ? 'Direct Competitor' : 'Complementary Magnet'

      const popupHtml = `
        <div class="map-popup comp-popup ${isComp ? 'is-competitor' : 'is-complement'}">
          <span class="popup-tag ${isComp ? 'tag-comp' : 'tag-compl'}">${kindLabel}</span>
          <h5 class="popup-comp-name">${comp.name}</h5>
          <div class="popup-meta">${ratingText}</div>
          <div class="popup-sub">${comp.distanceMi.toFixed(2)} mi from ${siteAddress}</div>
        </div>
      `

      const popup = new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(popupHtml)
      const marker = new maplibregl.Marker({ element: markerEl })
        .setLngLat([comp.lon, comp.lat])
        .setPopup(popup)
        .addTo(m)

      markers.push(marker)
    })

    if (!bounds.isEmpty()) {
      m.fitBounds(bounds, { padding: 90, maxZoom: 14 })
    }

    return () => {
      markers.forEach((mk) => mk.remove())
    }
  }, [sites, showCompetitors, showComplements, selectedSiteId, onSelectSite])

  return (
    <div className="map-wrapper" style={{ position: 'absolute', inset: 0 }}>
      <div ref={el} style={{ width: '100%', height: '100%' }} />

      {/* Map Legend and Filter Controls */}
      <div className="map-legend-card editorial-card">
        <div className="legend-title">
          <span className="legend-spark">✦</span> Map Layers
        </div>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-icon site-icon">#1</span>
            <span className="legend-label">Candidate Sites ({sites.length})</span>
          </div>
          <label className="legend-item checkbox-label">
            <input
              type="checkbox"
              checked={showCompetitors}
              onChange={(e) => setShowCompetitors(e.target.checked)}
            />
            <span className="legend-icon comp-icon" />
            <span className="legend-label">Competitors</span>
          </label>
          <label className="legend-item checkbox-label">
            <input
              type="checkbox"
              checked={showComplements}
              onChange={(e) => setShowComplements(e.target.checked)}
            />
            <span className="legend-icon compl-icon" />
            <span className="legend-label">Complements (Schools/Transit)</span>
          </label>
        </div>
      </div>
    </div>
  )
}
