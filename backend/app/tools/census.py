"""US Census: tract from lat/lon (geocoder, no key) + ACS 5-year stats (needs CENSUS_API_KEY)."""
from app import config, http
from app.cache import cached
from app.models import Demographics

GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
ACS = "https://api.census.gov/data/2023/acs/acs5"


def _num(v: str) -> float | None:
    x = float(v)
    return None if x < 0 else x  # ACS uses large negatives (e.g. -666666666) for "not available"


def demographics(lat: float, lon: float) -> Demographics:
    if not config.CENSUS_API_KEY:
        raise RuntimeError("CENSUS_API_KEY missing (free: api.census.gov/data/key_signup.html)")

    def tract():
        r = http.request("GET", GEOCODER, params=dict(x=lon, y=lat, benchmark="Public_AR_Current",
                                                      vintage="Current_Current", format="json"))
        r.raise_for_status()
        t = r.json()["result"]["geographies"]["Census Tracts"][0]
        return {k: t[k] for k in ("STATE", "COUNTY", "TRACT", "GEOID")}

    t = cached("census-tract", {"lat": round(lat, 6), "lon": round(lon, 6)}, tract)

    def acs():
        r = http.request("GET", ACS, params={"get": "B01003_001E,B19013_001E,B01002_001E",
                                             "for": f"tract:{t['TRACT']}",
                                             "in": f"state:{t['STATE']} county:{t['COUNTY']}",
                                             "key": config.CENSUS_API_KEY})
        r.raise_for_status()
        return r.json()[1]  # row 0 is the header

    pop, income, age = cached("census-acs", {"geoid": t["GEOID"]}, acs)[:3]
    return Demographics(population=int(float(pop)), medianIncome=_num(income), medianAge=_num(age), tract=t["GEOID"])
