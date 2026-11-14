"""Matterport 3D scans: floor area, rooms, seat estimate, written summary, floor plan."""
import base64

from app import config, http
from app.cache import cached
from app.models import Interior, Room

GRAPH = "https://api.matterport.com/api/models/graph"
QUERY = """query($id: ID!) { model(id: $id) {
  floors { dimensions { areaFloor units } }
  rooms { label dimensions { areaFloor width depth units } }
  generatedDescription { summary } } }"""
BACK_OF_HOUSE = ("kitchen", "storage", "restroom", "bathroom", "toilet", "utility", "closet", "mechanical", "warehouse")
SQFT_PER_SEAT = 15
M2_TO_SQFT = 10.7639


BUILDING_SCAN_RATIO = 1.5  # scan > 1.5x the listed suite = scan of the whole building


def is_building_scan(floor_sqft: float, listed_sqft: float) -> bool:
    return floor_sqft > BUILDING_SCAN_RATIO * listed_sqft


def _model(model_id: str, query: str) -> dict:
    r = http.request("POST", GRAPH, auth=(config.MATTERPORT_API_KEY, config.MATTERPORT_API_TOKEN),
                     json={"query": query, "variables": {"id": model_id}})
    r.raise_for_status()
    body = r.json()
    if body.get("errors") or not body.get("data", {}).get("model"):
        raise RuntimeError(f"matterport {model_id}: {body.get('errors')}")
    return body["data"]["model"]


FLOORPLAN_QUERY = "query($id: ID!) { model(id: $id) { assets { floorplans { format url } } } }"


def floorplan_jpeg(model_id: str) -> bytes | None:
    """Floor plan image bytes. Matterport's URLs expire within hours, so the bytes are cached, not the URL."""
    def fetch():
        plans = _model(model_id, FLOORPLAN_QUERY)["assets"]["floorplans"] or []
        url = next((p["url"] for p in plans if p["format"] == "jpg"), None)
        if not url:
            return None
        r = http.request("GET", url)
        r.raise_for_status()
        return base64.b64encode(r.content).decode()

    b64 = cached("matterport-floorplan", {"id": model_id}, fetch)
    return base64.b64decode(b64) if b64 else None


def interior(model_id: str, listed_sqft: float) -> Interior:
    """Scanned floor area and rooms. Seats come from the listed suite when the scan covers the whole building."""
    m = cached("matterport", {"id": model_id, "query": QUERY}, lambda: _model(model_id, QUERY))

    def sqft(d: dict) -> float:
        return d["areaFloor"] * (1 if d.get("units") == "imperial" else M2_TO_SQFT)

    floor = sum(sqft(f["dimensions"]) for f in m.get("floors", []) if f.get("dimensions"))
    rooms = [Room(label=r["label"], areaSqft=round(sqft(r["dimensions"]), 1),
                  widthFt=round(r["dimensions"].get("width") or 0, 1), depthFt=round(r["dimensions"].get("depth") or 0, 1))
             for r in m.get("rooms", []) if r.get("label") and r.get("dimensions")]  # unlabeled/unmeasured rooms are skipped
    if is_building_scan(floor, listed_sqft):
        front = 0.6 * listed_sqft  # the scan's rooms belong to other tenants too
    elif rooms:
        front = floor - sum(r.areaSqft for r in rooms if any(w in r.label.lower() for w in BACK_OF_HOUSE))
    else:
        front = 0.6 * floor
    return Interior(floorAreaSqft=round(floor, 1), rooms=rooms, estSeats=max(0, int(front / SQFT_PER_SEAT)),
                    tourUrl=f"https://my.matterport.com/show/?m={model_id}",
                    summary=(m.get("generatedDescription") or {}).get("summary"))
