"""Vexcel aerial imagery: parcel and top-down image (scored by tools/vision.py).

No parking count: elements/detect missed most empty stalls in one snapshot (6003 Bellaire: ~40 visible,
3-11 detected). Car dependence now comes from Census; site access from the vision road-access score.
"""
import base64

from shapely.geometry import shape

from app import config, http
from app.cache import cached
from app.geo import square_around
from app.models import Aerial

API = "https://api.vexcelgroup.com/v2"
LAYERS = "urban,urban-r,wide-area,urban-g"
NO_PARCEL_HALF_M = 40  # 80 m square when there is no parcel at the point
BUFFER_M = 30  # context around the lot: driveways, shared lot, frontage
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


def aerial(site_id: str, lat: float, lon: float) -> Aerial:
    """Parcel + image URL. Visibility and road access are filled in later by tools/vision.py."""
    p = parcel(lat, lon)
    return Aerial(parcelWkt=p["wkt"], collection=p["collection"], imageUrl=f"/api/sites/{site_id}/aerial.jpg")
