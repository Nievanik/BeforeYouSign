import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import type { Site } from '../types'

// Vite pre-bundling breaks MapLibre's relative worker path, so point at the worker file directly
maplibregl.setWorkerUrl(workerUrl)

const HOUSTON: [number, number] = [-95.3698, 29.7604]

export default function SiteMap({ sites }: { sites: Site[] }) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)

  useEffect(() => {
    const m = new maplibregl.Map({
      container: el.current!,
      // free, keyless vector tiles; "liberty" extrudes buildings in 3D when zoomed in
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: HOUSTON,
      zoom: 12,
      pitch: 45,
    })
    m.addControl(new maplibregl.NavigationControl())
    m.on('error', (e) => console.error('map error', e.error))
    map.current = m
    return () => m.remove()
  }, [])

  useEffect(() => {
    const m = map.current
    if (!m || sites.length === 0) return
    const markers = sites.map((s, i) => {
      const odds = s.sim ? `${Math.round(s.sim.pProfitableBy12 * 100)}% odds of profit by month 12` : 'not simulated'
      const popup = new maplibregl.Popup({ offset: 25 }).setText(`#${i + 1} ${s.address}: ${odds}`)
      return new maplibregl.Marker().setLngLat([s.lon, s.lat]).setPopup(popup).addTo(m)
    })
    const bounds = new maplibregl.LngLatBounds()
    sites.forEach((s) => bounds.extend([s.lon, s.lat]))
    m.fitBounds(bounds, { padding: 80, maxZoom: 14 })
    return () => markers.forEach((mk) => mk.remove())
  }, [sites])

  return <div ref={el} style={{ position: 'absolute', inset: 0 }} />
}
