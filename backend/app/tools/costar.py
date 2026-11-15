"""CoStar kit (local JSONL): candidate spaces and daytime workers nearby. No network."""
import csv
import json
from functools import lru_cache

from app import config
from app.geo import miles
from app.models import BusinessBrief, Site

LEASE_TYPES = {14, 16, 17, 20}  # direct/park/shopping-center lease, lease assignment (19 = sublease, excluded)
RETAIL_SPACE_USES = {3: "OfficeRetail", 5: "Retail"}
GENERAL_RETAIL = 6  # PropertyType
CITY_TO_STATE = {"Houston": "TX", "Los Angeles": "CA"}


@lru_cache
def _enums() -> dict:
    return json.loads((config.COSTAR_DIR / "schemas" / "enums.json").read_text())


@lru_cache
def _listings() -> list[dict]:
    with open(config.COSTAR_DIR / "data" / "commercial-listing-summary.jsonl") as f:
        return [json.loads(line) for line in f]


@lru_cache
def _matterport_ids() -> dict[int, str]:
    with open(config.COSTAR_DIR / "commercial-properties.csv") as f:
        return {int(r["PropertyId"]): r["MatterportModelId"] for r in csv.DictReader(f) if r["MatterportModelId"]}


@lru_cache
def _properties() -> dict[int, dict]:
    """Parking and building facts per propertyId (commercial-property.jsonl)."""
    kinds = _enums()["ParkingType"]
    out = {}
    with open(config.COSTAR_DIR / "data" / "commercial-property.jsonl") as f:
        for line in f:
            d = json.loads(line)
            park = d.get("parking") or []
            spaces = sum(p.get("totalSpaces") or 0 for p in park)
            built = [e["year"] for e in d.get("constructionEvents") or [] if e.get("eventType") == 2 and e.get("year")]
            out[d["id"]] = dict(
                parkingAvailable=True if park else None,  # an empty list means "not recorded", not "none"
                parkingSpaces=spaces or None,
                parkingTypes=sorted({kinds.get(str(p.get("parkingType")), "Unknown") for p in park} - {"Unknown"}),
                buildingClass={1: "A", 2: "B", 3: "C", 4: "F"}.get(d.get("buildingClass")),
                yearBuilt=min(built) if built else None,
            )
    return out


@lru_cache
def _workers(state: str) -> list[tuple[float, float, int]]:
    """(lat, lon, employees) for every company location in the state."""
    out = []
    with open(config.COSTAR_DIR / "data" / "company-detail.jsonl") as f:
        for line in f:
            c = json.loads(line)
            a, n = c.get("address") or {}, c.get("numEmployees") or 0
            if n > 0 and a.get("state") == state and a.get("latitude") and a.get("longitude"):
                out.append((a["latitude"], a["longitude"], n))
    return out


def normalize_rent(space: dict) -> tuple[float | None, float | None]:
    """(rentMonthly, rentPsfYear) from a lease space. Rate 0 means "not given" -> (None, None)."""
    rate = space.get("rateLow") or space.get("rateHigh")
    size = space.get("squareFeetMax") or 0
    if not rate or not size:
        return None, None
    psf_year = rate * 12 if space.get("rateBasis") == 1 else rate  # 1 = Monthly, 2 = Yearly
    return round(psf_year * size / 12, 2), round(psf_year, 2)


def _photo(listing: dict) -> str | None:
    atts = listing.get("attachments") or []
    for t in (3, 4):  # PrimaryPhoto, then BuildingPhoto
        for a in atts:
            if a.get("attachmentType") == t and a.get("attachmentUri"):
                return a["attachmentUri"].replace("/112/", "/113/")  # 1,400 px version
    return None


def find_candidates(brief: BusinessBrief) -> list[Site]:
    """Active retail lease spaces in the brief's city that fit rent and size. Unranked."""
    enums, mp = _enums(), _matterport_ids()
    sites, seen = [], set()
    for lst in _listings():
        a = lst.get("address") or {}
        if lst.get("listingStatus") != 1 or lst.get("listingType") not in LEASE_TYPES or a.get("city") != brief.city:
            continue
        if not a.get("latitude") or not a.get("longitude"):
            continue
        for sp in (lst.get("forLeaseSummary") or {}).get("spaces", []):
            if sp.get("isLeasePending"):
                continue
            if sp.get("spaceUse") not in RETAIL_SPACE_USES and lst.get("propertyType") != GENERAL_RETAIL:
                continue
            size = sp.get("squareFeetMax") or 0
            if (brief.sizeSqftMin and size < brief.sizeSqftMin) or (brief.sizeSqftMax and size > brief.sizeSqftMax):
                continue
            facts = _properties().get(lst["propertyId"], {})
            if brief.parkingRequired and not facts.get("parkingAvailable"):
                continue
            rent, psf = normalize_rent(sp)
            if rent is not None and rent > brief.maxRentMonthly:
                continue
            key = (lst["propertyId"], size, psf)  # the data repeats identical suites
            if key in seen:
                continue
            seen.add(key)
            gaps = [] if rent is not None else ["no rent given"]
            model_id = mp.get(lst["propertyId"])
            if not model_id:
                gaps.append("no 3D scan")
            if not facts.get("parkingAvailable"):
                gaps.append("parking not recorded")
            sites.append(Site(
                id=f"L{lst['id']}-S{sp['id']}",
                listingId=lst["id"],
                propertyId=lst["propertyId"],
                address=" ".join(str(a[k]) for k in ("streetNumber", "streetName", "streetType") if a.get(k)),
                lat=a["latitude"],
                lon=a["longitude"],
                sizeSqft=size,
                rentMonthly=rent,
                rentPsfYear=psf,
                serviceType=enums["ServiceType"].get(str(sp.get("serviceType")), "Unknown"),
                spaceUse=enums["SpaceUse"].get(str(sp.get("spaceUse")), "Unknown"),
                photoUrl=_photo(lst),
                matterportModelId=model_id,
                gaps=gaps,
                **facts,
            ))
    return sites


def workers_nearby(lat: float, lon: float, radius_mi: float, city: str = "Houston") -> int:
    """Employees at company locations within radius_mi (CoStar company-detail)."""
    return sum(n for la, lo, n in _workers(CITY_TO_STATE[city]) if miles(lat, lon, la, lo) <= radius_mi)


def get_site(site_id: str, city: str = "Houston") -> Site | None:
    """Look up one candidate by id ("L{listingId}-S{spaceId}"), ignoring rent/size filters."""
    try:
        brief = BusinessBrief(businessType="any", city=city, maxRentMonthly=float("inf"))
        site = next((s for s in find_candidates(brief) if s.id == site_id), None)
        if site:
            return site
    except (FileNotFoundError, KeyError):
        pass

    # Fallback for demo datasets / golden fixtures when raw CoStar JSONL is not on disk
    for path in [config.DEMO_DIR / "restaurant.json", config.DEMO_DIR / "salon.json", config.DEMO_DIR.parents[0] / "fixtures" / "golden_run.json"]:
        if path.exists():
            data = json.loads(path.read_text())
            s_list = data.get("result", {}).get("sites", []) or data.get("sites", [])
            for s in s_list:
                if s.get("id") == site_id:
                    return Site(**s)
    return None
