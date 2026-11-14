# Backend API

Base URL: `http://localhost:8000/api`. JSON in and out. Types are defined in [data-schema.md](data-schema.md).

## Flow

```
POST /analyze            → { runId }
GET  /runs/{runId}/events  (SSE)  step… step… result
GET  /runs/{runId}         → full RunResult (after "done", or to reload)
```

## `POST /analyze`

Starts one analysis run.

```json
// request
{ "query": "Boba shop in Houston, max $6k/month rent, needs parking" }

// response 202
{ "runId": "r_8f2c1a" }
```

Optional: `"brief": BusinessBrief` overrides the parsed brief (used when the user edits the parsed values).

Errors: `400` empty query · `422` brief fails validation.

## `GET /runs/{runId}/events` (Server-Sent Events)

One `event:` per message, `data:` is JSON.

| event | data | When |
|---|---|---|
| `brief` | `BusinessBrief` | Request parsed, and again whenever the agent relaxes a limit |
| `plan` | `{ "todos": [{ "title": "...", "status": "pending" \| "in_progress" \| "completed" }] }` | The agent writes or updates its plan |
| `step` | `{ "id": "s3", "tool": "vexcel", "siteId": "L123", "message": "Reading the aerial image of 9700 Tanner Rd", "status": "running" \| "done" \| "error" }` | Each tool call starts and ends |
| `site` | `Site` | A site's evidence is complete (cards appear one by one) |
| `sim` | `{ "siteId": "L123", "result": SimResult }` | Simulation finished for a site |
| `report` | `{ "markdown": "..." }` | Final recommendation written |
| `done` | `{ "runId": "r_8f2c1a" }` | Stream ends |
| `error` | `{ "message": "...", "fatal": true }` | Fatal = run stopped. Non-fatal errors arrive as `step` with `status: "error"` |

A tool failure on one site never kills the run: that site's card shows a "data missing" note.

## `GET /runs/{runId}`

Returns `RunResult` (brief, sites with sim results, report). `404` if the id is unknown.

## `GET /sites/{siteId}/aerial.jpg`

Cached Vexcel ortho image with the parcel outline drawn on it. The key stays server-side; the browser only sees this proxy.

## `GET /sites/{siteId}/oblique/{direction}.jpg`

Cached Vexcel angled photo (`north`/`east`/`south`/`west`, newest capture), parcel outlined. `oblique-north` = camera **facing** north, so it shows the building's south side. `404` if that direction isn't available.

## `GET /sites/{id}/floorplan.jpg`

Cached Matterport floor plan of the site's 3D scan. `404` if the site has no scan or no floor plan.

## `GET /health`

`{ "ok": true, "offline": false }`

## Frontend notes

- Matterport tour: iframe `https://my.matterport.com/show/?m={matterportModelId}&play=1&dh=1&qs=1`. The kit's models are public, so no key is needed in the browser (the SDK key is only for SDK control). It loads only when the user clicks, because it's heavy.
- Matterport also returns downloadable `.obj` meshes (`model.assets.meshes`, 50k/500k, defurnished). Not used yet; an option for a 3D view on the map.
- No auth: local demo only.
