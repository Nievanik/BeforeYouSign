import { useState, useRef, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'

// Models in the kit are public, so the plain Showcase link works without a key.
// dh=1 keeps the "dollhouse" (3D model) button; play=1 starts once the user asked for it.
export default function TourEmbed({ modelId, buildingScan }: { modelId: string; buildingScan: boolean }) {
  const [open, setOpen] = useState(false)
  const [isNativeFs, setIsNativeFs] = useState(false)
  const [isPortalFs, setIsPortalFs] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const isFullscreen = isNativeFs || isPortalFs

  // Listen for native fullscreen changes (from Matterport controls, our button, or ESC key)
  useEffect(() => {
    const handleFsChange = () => {
      const fsEl = document.fullscreenElement || (document as unknown as { webkitFullscreenElement?: Element }).webkitFullscreenElement
      const active = Boolean(fsEl && (fsEl === iframeRef.current || fsEl === wrapperRef.current))
      setIsNativeFs(active)
    }

    document.addEventListener('fullscreenchange', handleFsChange)
    document.addEventListener('webkitfullscreenchange', handleFsChange)

    return () => {
      document.removeEventListener('fullscreenchange', handleFsChange)
      document.removeEventListener('webkitfullscreenchange', handleFsChange)
    }
  }, [])

  // Listen for Escape key to exit fallback portal overlay if active
  useEffect(() => {
    if (!isPortalFs) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsPortalFs(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isPortalFs])

  const toggleFullscreen = useCallback(() => {
    const doc = document as unknown as {
      fullscreenElement?: Element
      webkitFullscreenElement?: Element
      exitFullscreen?: () => Promise<void>
      webkitExitFullscreen?: () => void
    }
    const fsEl = doc.fullscreenElement || doc.webkitFullscreenElement

    if (fsEl) {
      if (doc.exitFullscreen) {
        doc.exitFullscreen().catch(() => {})
      } else if (doc.webkitExitFullscreen) {
        doc.webkitExitFullscreen()
      }
      setIsNativeFs(false)
      return
    }

    if (isPortalFs) {
      setIsPortalFs(false)
      return
    }

    // Prefer Native Fullscreen API on the iframe / wrapper to avoid reloading the 3D model
    const target = iframeRef.current || wrapperRef.current
    if (target) {
      const el = target as unknown as {
        requestFullscreen?: () => Promise<void>
        webkitRequestFullscreen?: () => void
      }
      if (el.requestFullscreen) {
        el.requestFullscreen().catch(() => {
          setIsPortalFs(true)
        })
      } else if (el.webkitRequestFullscreen) {
        try {
          el.webkitRequestFullscreen()
        } catch {
          setIsPortalFs(true)
        }
      } else {
        setIsPortalFs(true)
      }
    }
  }, [isPortalFs])

  if (!open) {
    return (
      <button
        type="button"
        className="tour-trigger-btn"
        onClick={(e) => {
          e.stopPropagation()
          setOpen(true)
        }}
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
          <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
          <line x1="12" y1="22.08" x2="12" y2="12" />
        </svg>
        View 3D tour (inside + dollhouse)
      </button>
    )
  }

  const iframeNode = (
    <iframe
      ref={iframeRef}
      title="Matterport 3D tour"
      src={`https://my.matterport.com/show/?m=${modelId}&play=1&dh=1&qs=1`}
      allow="fullscreen; xr-spatial-tracking; gyroscope; accelerometer"
      allowFullScreen
      className="tour"
    />
  )

  return (
    <figure className="tour-figure" onClick={(e) => e.stopPropagation()}>
      <div ref={wrapperRef} className={`tour-wrapper ${isFullscreen ? 'is-fullscreen' : ''}`}>
        {!isPortalFs && iframeNode}
        <button
          type="button"
          className="tour-fs-btn"
          onClick={toggleFullscreen}
          title={isFullscreen ? 'Exit full screen' : 'Full screen'}
          aria-label={isFullscreen ? 'Exit full screen' : 'Full screen'}
        >
          {isFullscreen ? (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
            </svg>
          ) : (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 3h6v6m0-6L14 10M9 21H3v-6m0 6l7-7M3 9V3h6M3 3l7 7m11 11v-6h-6m6 6l-7-7" />
            </svg>
          )}
        </button>
      </div>

      {isPortalFs &&
        createPortal(
          <div className="tour-portal-overlay" role="dialog" aria-modal="true" aria-label="3D Tour Fullscreen">
            {iframeNode}
            <button
              type="button"
              className="tour-portal-close-btn"
              onClick={() => setIsPortalFs(false)}
              title="Exit full screen"
              aria-label="Exit full screen"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>,
          document.body
        )}

      {buildingScan && <figcaption>Scan of the whole building, not only this suite.</figcaption>}
    </figure>
  )
}

