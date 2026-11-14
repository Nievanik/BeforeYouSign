"""Vexcel aerial imagery: parcel, top-down image (scored by tools/vision.py), parking seen on the parcel.

parkingSeen is DISPLAY ONLY, never used in the odds (one photo; lots may be shared with other tenants).
elements/detect returns one box per parking ROW, not per stall, so stalls are estimated from row length
when the boxes look trustworthy (see estimate_spaces). Car dependence comes from Census and site access
from the vision road-access score.
"""
import base64
import math

from shapely import wkt as shapely_wkt
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


def ortho_jpeg(wkt: str, boxes: list[str] | None = None) -> bytes:
    """Top-down JPEG of the parcel plus a buffer: parcel outlined in gold, optional boxes (WKT) in cyan."""
    drawing = [{"wkt": wkt, "outline-width": 4, "outline-color": "rgb(255,204,0)"}]
    drawing += [{"wkt": b, "outline-width": 2, "outline-color": "rgb(0,229,255)"} for b in boxes or []]

    def fetch():
        r = _call("POST", "ortho/extract", json={
            "wkt": wkt, "srid": 4326, "layer": LAYERS, "buffer-meter": BUFFER_M, "crop": "bounding_box",
            "image-format": "jpeg", "drawing": drawing})
        r.raise_for_status()
        return base64.b64encode(r.content).decode()

    key = {"wkt": wkt, "boxes": boxes} if boxes else {"wkt": wkt}
    return base64.b64decode(cached("vexcel-ortho", key, fetch))


DIRECTIONS = ("oblique-north", "oblique-east", "oblique-south", "oblique-west")


def oblique_directions(wkt: str) -> list[str]:
    """Angled-photo directions available in the newest capture (only the 'urban' layer has obliques)."""
    def fetch():
        r = _call("GET", "oriented/collections", params={"wkt": wkt, "srid": 4326, "layer": "urban",
                                                         "product-type": "oblique",
                                                         "include": "product-type,collection,last-capture-date"})
        if r.status_code == 404:  # no oblique coverage here
            return []
        r.raise_for_status()
        feats = r.json().get("features", [])
        newest = max((f["properties"]["last-capture-date"] for f in feats), default=None)
        have = {f["properties"]["product-type"] for f in feats if f["properties"]["last-capture-date"] == newest}
        return [d for d in DIRECTIONS if d in have]

    return cached("vexcel-oblique-dirs", {"wkt": wkt}, fetch)


def oblique_jpeg(wkt: str, direction: str) -> bytes:
    """Angled photo of the parcel (shows facades and storefront), parcel outlined in gold."""
    def fetch():
        r = _call("POST", "oriented/extract", json={
            "wkt": wkt, "srid": 4326, "layer": "urban", "product-type": direction, "rotation": "natural",
            "buffer-meter": 10, "crop": "bbox", "image-format": "jpeg/png",
            # oriented/extract quirks (vexcel_quickstart.py): bare "r,g,b" colors and an explicit transparent fill
            "drawing": [{"wkt": wkt, "outline-width": 4, "outline-color": "255,204,0",
                         "fill-color": "255,204,0", "transparency": 0}]})
        r.raise_for_status()
        return base64.b64encode(r.content).decode()

    return base64.b64decode(cached("vexcel-oblique", {"wkt": wkt, "direction": direction}, fetch))


DETECTION_THRESHOLD = 0.3


def detect_parking(wkt: str) -> list[str]:
    """WKT boxes of parking spaces detected on the parcel itself (no buffer: spaces the business would get)."""
    def fetch():
        r = _call("POST", "elements/detect", json={
            "wkt": wkt, "srid": 4326, "buffer-meter": 0,
            "images": [{"endpoint": "ortho/extract",
                        "request": {"layer": LAYERS, "srid": 4326, "wkt": wkt, "crop": "bounding_box"}}],
            "model-input": {"elements": [{"label": "parking space", "model": "sam3",
                                          "detection-threshold": DETECTION_THRESHOLD}],
                            "include": ["bbox", "confidence"]}})
        r.raise_for_status()
        return [d["bbox"] for f in r.json().get("features", []) for d in f["properties"].get("detections", [])
                if d.get("bbox")]

    return cached("vexcel-parking", {"wkt": wkt, "threshold": DETECTION_THRESHOLD}, fetch)


STALL_WIDTH_M = 2.75  # 9 ft
ROW_ASPECT = 3  # a box at least 3x longer than wide is one parking row


def _box_m(g) -> tuple[float, float]:
    x0, y0, x1, y1 = g.bounds
    return (x1 - x0) * 111_320 * math.cos(math.radians((y0 + y1) / 2)), (y1 - y0) * 111_320


def estimate_spaces(parcel_wkt: str, boxes: list[str]) -> int | None:
    """Spaces from detected parking rows (length / stall width), or None when the boxes can't be trusted.

    Boxes are axis-aligned: on a diagonal lot they swallow road and building and overlap each other
    (15015 Westheimer gave "785"). So a number is returned only if every box is row-shaped, mostly on
    the parcel, and no two boxes overlap. Verified on 6003 Bellaire: 48 vs ~45 counted by eye.
    Upgrade: use the detector's pixel masks instead of boxes.
    """
    if not boxes:
        return 0
    parcel_g = shapely_wkt.loads(parcel_wkt)
    gs = [shapely_wkt.loads(b) for b in boxes]
    total = 0
    for i, g in enumerate(gs):
        w, h = _box_m(g)
        if min(w, h) == 0 or max(w, h) / min(w, h) < ROW_ASPECT:
            return None
        if g.intersection(parcel_g).area < 0.7 * g.area:
            return None
        if any(g.intersection(o).area > 0.1 * min(g.area, o.area) for o in gs[i + 1:]):
            return None
        total += round(max(w, h) / STALL_WIDTH_M)
    return total


def aerial(site_id: str, lat: float, lon: float) -> Aerial:
    """Parcel + image URL. Visibility and road access are filled in later by tools/vision.py."""
    p = parcel(lat, lon)
    return Aerial(parcelWkt=p["wkt"], collection=p["collection"], parkingSeen=estimate_spaces(p["wkt"], detect_parking(p["wkt"])),
                  imageUrl=f"/api/sites/{site_id}/aerial.jpg",
                  obliqueDirections=[d.removeprefix("oblique-") for d in oblique_directions(p["wkt"])])
