import { useState } from 'react'

// Models in the kit are public, so the plain Showcase link works without a key.
// dh=1 keeps the "dollhouse" (3D model) button; play=1 starts once the user asked for it.
export default function TourEmbed({ modelId, buildingScan }: { modelId: string; buildingScan: boolean }) {
  const [open, setOpen] = useState(false)
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}>
        View 3D tour (inside + dollhouse)
      </button>
    )
  }
  return (
    <figure>
      <iframe
        title="Matterport 3D tour"
        src={`https://my.matterport.com/show/?m=${modelId}&play=1&dh=1&qs=1`}
        allow="fullscreen; xr-spatial-tracking"
        allowFullScreen
        className="tour"
      />
      {buildingScan && <figcaption>Scan of the whole building, not only this suite.</figcaption>}
    </figure>
  )
}
