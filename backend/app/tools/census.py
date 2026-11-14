"""US Census: tract from lat/lon (geocoder, no key) + ACS 5-year stats (needs CENSUS_API_KEY).

Besides people and income, ACS says how residents get around. That replaces the aerial parking count,
which was one snapshot and missed most empty stalls.
"""
from app import config, http
from app.cache import cached
from app.models import Demographics

GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
ACS = "https://api.census.gov/data/2023/acs/acs5"
VARS = {
    "population": "B01003_001E",
    "medianIncome": "B19013_001E",
    "medianAge": "B01002_001E",
    "commuters": "B08301_001E",      # workers 16+ by means of transportation to work
    "byCar": "B08301_002E",          # car, truck or van
    "byTransit": "B08301_010E",      # public transportation
    "walked": "B08301_019E",
    "households": "B08201_001E",
    "noVehicle": "B08201_002E",      # households with no vehicle available
}
SQM_PER_SQMI = 2_589_988


def _num(v) -> float | None:
    x = float(v)
    return None if x < 0 else x  # ACS uses large negatives (e.g. -666666666) for "not available"


def _share(part: float | None, whole: float | None) -> float | None:
    return round(part / whole, 3) if part is not None and whole else None


def demographics(lat: float, lon: float) -> Demographics:
    if not config.CENSUS_API_KEY:
        raise RuntimeError("CENSUS_API_KEY missing (free: api.census.gov/data/key_signup.html)")

    def tract():
        r = http.request("GET", GEOCODER, params=dict(x=lon, y=lat, benchmark="Public_AR_Current",
                                                      vintage="Current_Current", format="json"))
        r.raise_for_status()
        t = r.json()["result"]["geographies"]["Census Tracts"][0]
        return {k: t[k] for k in ("STATE", "COUNTY", "TRACT", "GEOID", "AREALAND")}

    t = cached("census-tract", {"lat": round(lat, 6), "lon": round(lon, 6)}, tract)

    def acs():
        r = http.request("GET", ACS, params={"get": ",".join(VARS.values()),
                                             "for": f"tract:{t['TRACT']}",
                                             "in": f"state:{t['STATE']} county:{t['COUNTY']}",
                                             "key": config.CENSUS_API_KEY})
        r.raise_for_status()
        if not r.headers.get("content-type", "").startswith("application/json"):
            raise RuntimeError(f"census: unexpected reply ({r.url})")  # e.g. invalid key page
        return dict(zip(VARS, r.json()[1]))  # row 0 is the header

    v = {k: _num(x) for k, x in cached("census-acs", {"geoid": t["GEOID"], "vars": list(VARS.values())}, acs).items()}
    pop = int(v["population"] or 0)
    walk_transit = (v["walked"] or 0) + (v["byTransit"] or 0) if v["commuters"] else None
    return Demographics(
        population=pop,
        medianIncome=v["medianIncome"],
        medianAge=v["medianAge"],
        tract=t["GEOID"],
        densityPerSqMi=round(pop / (t["AREALAND"] / SQM_PER_SQMI)) if t["AREALAND"] else None,
        driveShare=_share(v["byCar"], v["commuters"]),
        walkTransitShare=_share(walk_transit, v["commuters"]),
        noVehicleShare=_share(v["noVehicle"], v["households"]),
    )
