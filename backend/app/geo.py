import math


def miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # shortcut: equirectangular approximation, accurate to <0.1% at city scale
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    return 3958.8 * math.hypot(x, math.radians(lat2 - lat1))


def square_around(lat: float, lon: float, half_m: float) -> str:
    """WKT square centered on lat/lon, half_m meters from center to edge."""
    dlat = half_m / 111_320
    dlon = half_m / (111_320 * math.cos(math.radians(lat)))
    w, e, s, n = lon - dlon, lon + dlon, lat - dlat, lat + dlat
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
