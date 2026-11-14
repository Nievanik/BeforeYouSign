"""OpenStreetMap Overpass: competitors and complements near a site. No ratings (default attractiveness)."""
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

from app import config, http
from app.cache import cached
from app.geo import miles
from app.models import Competitor

# the main server rate-limits or refuses whole networks at times; mirrors serve the same data
OVERPASS = ["https://overpass.openstreetmap.fr/api/interpreter", "https://overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
            "https://overpass.private.coffee/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
# simulation.md: (rating/4)^2 * log(1+reviews), with 4.0 stars / 20 reviews when unknown
DEFAULT_ATTRACTIVENESS = round(math.log(1 + 20), 3)
_PART = re.compile(r'\["(\w+)"(=|~)"([^"]+)"(,i)?\]')


def matches(filter_: str, tags: dict) -> bool:
    """Python check of an Overpass filter like '["amenity"~"cafe"]["name"~"boba",i]' (all parts must match)."""
    for key, op, val, icase in _PART.findall(filter_):
        v = tags.get(key)
        if v is None:
            return False
        if op == "=" and v != val:
            return False
        if op == "~" and not re.search(val, v, re.I if icase else 0):
            return False
    return True


# words people (or the LLM) use for the preset types
ALIASES = {"restaurant": "fast_casual", "fast_food": "fast_casual", "fast food": "fast_casual", "burger": "fast_casual",
           "sandwich": "fast_casual", "cafe": "coffee", "coffee shop": "coffee", "tea": "boba", "bubble tea": "boba",
           "hair salon": "salon", "barber": "salon", "barbershop": "salon", "clothing": "boutique",
           "clothing store": "boutique"}


def tags_for(business_type: str) -> dict[str, list[str]]:
    """Overpass filters for a business type: a preset, an alias of one, or a generic guess from the type's name."""
    t = business_type.strip().lower()
    t = ALIASES.get(t, t)
    if t in config.OSM_TAGS:
        return config.OSM_TAGS[t]
    # shortcut: OSM tag value = the type (amenity=restaurant, shop=bakery) or the name contains it; no complements
    word = re.sub(r"[^a-z0-9 ]", "", t).strip() or "shop"  # it goes into the query text, so letters only
    value = word.replace(" ", "_")
    return {"competitor": [f'["amenity"="{value}"]', f'["shop"="{value}"]', f'["name"~"{word}",i]'], "complement": []}


def competitors(lat: float, lon: float, business_type: str, radius_mi: float = 1.0) -> list[Competitor]:
    """Competitors/complements around one point (one small query: combined multi-site queries time out)."""
    filters = tags_for(business_type)
    radius_m = round(radius_mi * 1609.34)
    lines = "".join(f"nwr(around:{radius_m},{lat},{lon}){f};" for kind in ("competitor", "complement") for f in filters[kind])
    query = f"[out:json][timeout:25];({lines});out center tags;"

    def ask(url):
        r = http.request("POST", url, retries=0, timeout=60, data={"data": query})
        r.raise_for_status()
        j = r.json()
        # Overpass reports timeouts as 200 + a "remark"; never cache that as "no competitors"
        if "error" in (j.get("remark") or ""):
            raise RuntimeError(j["remark"][:120])
        return j["elements"]

    def fetch():
        """Ask every mirror at once and take the first good answer: most are often down or very slow."""
        errors = []
        pool = ThreadPoolExecutor(len(OVERPASS))
        futures = {pool.submit(ask, url): url for url in OVERPASS}
        try:
            for f in as_completed(futures):
                try:
                    return f.result()
                except Exception as e:
                    errors.append(f"{futures[f].split('/')[2]}: {str(e)[:60]}")
        finally:
            pool.shutdown(wait=False, cancel_futures=True)  # don't wait for the slow ones
        raise RuntimeError("overpass unreachable (" + "; ".join(errors) + ")")

    out = []
    for e in cached("osm", {"q": query}, fetch):
        t = e.get("tags", {})
        la, lo = e.get("lat") or e.get("center", {}).get("lat"), e.get("lon") or e.get("center", {}).get("lon")
        if not t.get("name") or la is None:
            continue
        kind = next((k for k in ("competitor", "complement") if any(matches(f, t) for f in filters[k])), "neutral")
        out.append(Competitor(name=t["name"], kind=kind, lat=la, lon=lo, distanceMi=round(miles(lat, lon, la, lo), 3),
                              attractiveness=DEFAULT_ATTRACTIVENESS, source="osm",
                              address=" ".join(t[k] for k in ("addr:housenumber", "addr:street") if t.get(k)) or None))
    return sorted(out, key=lambda c: c.distanceMi)
