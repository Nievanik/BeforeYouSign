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

    // 1. Site Markers
    sites.forEach((s, i) => {
      bounds.extend([s.lon, s.lat])

      const markerEl = document.createElement('div')
      markerEl.className = `site-pin rank-${i + 1} ${selectedSiteId === s.id ? 'is-selected' : ''}`
      markerEl.innerHTML = `<span>#${i + 1}</span>`
      markerEl.title = `${s.address}`

      if (onSelectSite) {
        markerEl.addEventListener('click', (ev) => {
          ev.stopPropagation()
          onSelectSite(s.id)
        })
      }

      const odds = s.sim
        ? `${Math.round(s.sim.pProfitableBy12 * 100)}% odds of profit by month 12`
        : 'Not simulated'
      const rent = s.rentMonthly ? `$${Math.round(s.rentMonthly).toLocaleString()}/mo` : 'Rent unlisted'

      const popupHtml = `
        <div class="map-popup site-popup">
          <div class="popup-rank">Candidate Site #${i + 1}</div>
          <strong>${s.address}</strong>
          <div class="popup-rent">${rent} · ${s.sizeSqft.toLocaleString()} sq ft</div>
          <div class="popup-odds">${odds}</div>
        </div>
      `

      const popup = new maplibregl.Popup({ offset: 20, closeButton: false }).setHTML(popupHtml)
      const marker = new maplibregl.Marker({ element: markerEl })
        .setLngLat([s.lon, s.lat])
        .setPopup(popup)
        .addTo(m)

      markers.push(marker)
    })

    // 2. Competitors & Complements from all sites (deduplicated by coords + name)
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
      if (!isComp && !isCompl) return // skip unclassified neutral

      const markerEl = document.createElement('div')
      markerEl.className = `comp-pin ${isComp ? 'comp-pin-competitor' : 'comp-pin-complement'}`
      markerEl.title = `${comp.name} (${comp.kind})`

      const ratingText = comp.rating
        ? `★ ${comp.rating.toFixed(1)}${comp.reviewCount ? ` (${comp.reviewCount} reviews)` : ''}`
        : 'Rating unlisted'

      const kindLabel = isComp ? 'Competitor' : 'Complement (Traffic Draw)'

      const popupHtml = `
        <div class="map-popup comp-popup">
          <span class="popup-tag ${isComp ? 'tag-comp' : 'tag-compl'}">${kindLabel}</span>
          <strong>${comp.name}</strong>
          <div class="popup-meta">${ratingText}</div>
          <div class="popup-sub">${comp.distanceMi.toFixed(2)} mi from ${siteAddress}</div>
        </div>
      `

      const popup = new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(popupHtml)
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
      <div className="map-legend-card">
        <div className="legend-title">Map Layers</div>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-icon site-icon">#1</span>
            <span>Candidate Sites ({sites.length})</span>
          </div>
          <label className="legend-item checkbox-label">
            <input
              type="checkbox"
              checked={showCompetitors}
              onChange={(e) => setShowCompetitors(e.target.checked)}
            />
            <span className="legend-icon comp-icon" />
            <span>Competitors</span>
          </label>
          <label className="legend-item checkbox-label">
            <input
              type="checkbox"
              checked={showComplements}
              onChange={(e) => setShowComplements(e.target.checked)}
            />
            <span className="legend-icon compl-icon" />
            <span>Complements (Schools/Transit)</span>
          </label>
        </div>
      </div>
    </div>
  )
}
