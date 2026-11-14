"""Vexcel aerial imagery: parcel, top-down image, parking and car counts."""
import base64

from shapely.geometry import shape

from app import config, http
from app.cache import cached
from app.geo import square_around
from app.models import Aerial

API = "https://api.vexcelgroup.com/v2"
LAYERS = "urban,urban-r,wide-area,urban-g"
NO_PARCEL_HALF_M = 40  # 80 m square when there is no parcel at the point
BUFFER_M = 30  # retail parking is often outside the tenant's parcel
CREDIT = "Imagery © Vexcel Imaging US, Inc."


def _call(method: str, path: str, **kw):
    return http.request(method, f"{API}/{path}", headers={"X-API-KEY": config.VEXCEL_API_KEY}, timeout=300, **kw)


def parcel(lat: float, lon: float) -> dict:
    """{"wkt", "collection"}; falls back to a square when Vexcel has no parcel here."""
    def fetch():
        r = _call("GET", "property/extract", params={"wkt": f"POINT({lon} {lat})", "srid": 4326, "layer": LAYERS,
                                                     "latest": "true", "include": "precomputed", "unit-system": "imperial"})
        if r.status_code == 404:
            return {"wkt": square_around(lat, lon, NO_PARCEL_HALF_M), "collection": None}
        r.raise_for_status()
        f = r.json()["features"][0]
        return {"wkt": shape(f["geometry"]).wkt, "collection": f["properties"].get("metadata.collection")}

    return cached("vexcel-parcel", {"lat": round(lat, 6), "lon": round(lon, 6)}, fetch)


def ortho_jpeg(wkt: str) -> bytes:
    """Top-down JPEG of the parcel plus a buffer, parcel outlined in gold."""
    def fetch():
        r = _call("POST", "ortho/extract", json={
            "wkt": wkt, "srid": 4326, "layer": LAYERS, "buffer-meter": BUFFER_M, "crop": "bounding_box",
            "image-format": "jpeg", "drawing": [{"wkt": wkt, "outline-width": 4, "outline-color": "rgb(255,204,0)"}]})
        r.raise_for_status()
        return base64.b64encode(r.content).decode()

    return base64.b64decode(cached("vexcel-ortho", {"wkt": wkt}, fetch))


# shortcut: sam3 finds cars well but misses most empty painted stalls, so parkingSpaces is a LOWER BOUND
# (6003 Bellaire: ~40 striped stalls visible, 11 detected at 0.3, 3 at 0.5). Lot-area / 30 m2 overcounts
# because lot boxes overlap the building. Upgrade: polygon masks minus building footprint.
DETECTION_THRESHOLD = 0.3


def detect_counts(wkt: str) -> dict[str, int]:
    labels = ("parking space", "car")

    def fetch():
        r = _call("POST", "elements/detect", json={
            "wkt": wkt, "srid": 4326, "buffer-meter": BUFFER_M,
            "images": [{"endpoint": "ortho/extract",
                        "request": {"layer": LAYERS, "srid": 4326, "wkt": wkt, "crop": "bounding_box"}}],
            "model-input": {"elements": [{"label": l, "model": "sam3", "detection-threshold": DETECTION_THRESHOLD} for l in labels],
                            "include": ["bbox", "confidence"]}})
        r.raise_for_status()
        feats = r.json().get("features", [])
        return {l: sum(len(f["properties"].get("detections", [])) for f in feats if f["properties"].get("label") == l)
                for l in labels}

    return cached("vexcel-detect", {"wkt": wkt, "threshold": DETECTION_THRESHOLD}, fetch)


def aerial(site_id: str, lat: float, lon: float) -> Aerial:
    """Parcel + parking/car counts. Visibility and road access are filled in later by tools/vision.py."""
    p = parcel(lat, lon)
    counts = detect_counts(p["wkt"])
    return Aerial(parcelWkt=p["wkt"], parkingSpaces=counts["parking space"], carsSeen=counts["car"],
                  collection=p["collection"], imageUrl=f"/api/sites/{site_id}/aerial.jpg")
