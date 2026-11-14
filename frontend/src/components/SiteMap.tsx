import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import type { Competitor, Site } from '../types'

maplibregl.setWorkerUrl(workerUrl)

const HOUSTON: [number, number] = [-95.3698, 29.7604]

function milesBetween(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const r = Math.PI / 180
  const h =
    Math.sin(((b.lat - a.lat) * r) / 2) ** 2 +
    Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lon - a.lon) * r) / 2) ** 2
  return 3958.8 * 2 * Math.asin(Math.sqrt(h))
}

const esc = (t: string) => t.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`)
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
  const sitePins = useRef(new Map<string, HTMLElement>())
  const fittedKey = useRef('')
  const selectedRef = useRef(selectedSiteId)
  selectedRef.current = selectedSiteId // redrawn pins read the current selection

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
      markerEl.className = `site-pin rank-${i + 1} ${selectedRef.current === s.id ? 'is-selected' : ''}`
      sitePins.current.set(s.id, markerEl)
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
          <strong>${esc(s.address)}</strong>
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
    const allComps: Competitor[] = []

    sites.forEach((site) => {
      site.competitors?.forEach((c) => {
        const key = `${c.name}_${c.lat.toFixed(4)}_${c.lon.toFixed(4)}`
        if (!seenComp.has(key)) {
          seenComp.add(key)
          allComps.push(c)
        }
      })
    })

    allComps.forEach((comp) => {
      // distance from the nearest candidate on the map, so the number matches what the user sees
      const near = sites
        .map((s, i) => ({ i, s, d: milesBetween(s, comp) }))
        .reduce((a, b) => (b.d < a.d ? b : a))
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
          <strong>${esc(comp.name)}</strong>
          <div class="popup-meta">${comp.address ? esc(comp.address) : `${comp.lat.toFixed(5)}, ${comp.lon.toFixed(5)}`}</div>
          <div class="popup-meta">${ratingText}</div>
          <div class="popup-sub">${near.d.toFixed(2)} mi from #${near.i + 1} ${esc(near.s.address)}</div>
        </div>
      `

      const popup = new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(popupHtml)
      const marker = new maplibregl.Marker({ element: markerEl })
        .setLngLat([comp.lon, comp.lat])
        .setPopup(popup)
        .addTo(m)

      markers.push(marker)
    })

    // refit only when the set of candidates changes, not on every streamed update or selection
    const key = sites.map((s) => s.id).join(',')
    if (!bounds.isEmpty() && key !== fittedKey.current) {
      fittedKey.current = key
      m.fitBounds(bounds, { padding: 90, maxZoom: 14 })
    }

    const pins = sitePins.current
    return () => {
      markers.forEach((mk) => mk.remove())
      pins.clear()
    }
  }, [sites, showCompetitors, showComplements, onSelectSite])

  // selection (from a card or a pin): highlight the pin and move the map to it
  useEffect(() => {
    sitePins.current.forEach((pin, id) => pin.classList.toggle('is-selected', id === selectedSiteId))
    const s = sites.find((x) => x.id === selectedSiteId)
    if (s && map.current) map.current.flyTo({ center: [s.lon, s.lat], zoom: 15, essential: true })
  }, [selectedSiteId]) // only on a new selection, not on every streamed update

  // every shown site's competitor lookup failed (OpenStreetMap servers down): say so instead of an empty map
  const noCompetitorData =
    sites.length > 0 && sites.every((s) => s.gaps.some((g) => g.startsWith('no competitors')))

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
            {noCompetitorData && <span className="legend-note">(lookup failed, try again)</span>}
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
