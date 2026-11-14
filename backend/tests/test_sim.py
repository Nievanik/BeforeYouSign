import time

import pytest

from app import sim
from app.models import Competitor, Demographics, Site

BOBA = {"typicalDailyCustomers": 110, "ticket": 8.0, "ticketSd": 1.25, "cogsMin": 0.25, "cogsMax": 0.35,
        "laborFixedMonthly": 7000, "laborVariablePct": 0, "otherFixedMonthly": 1500, "daysOpen": 30,
        "rampMin": 3, "rampMax": 9, "startupCost": 110_000, "radiusMi": 1, "lambda": 2, "workerWeight": 0.5,
        "newCompetitorRatePerYear": 0.3, "rentShareMax": 0.15}
LAT, LON = 29.70, -95.48


@pytest.fixture(autouse=True)
def no_workers(monkeypatch):
    monkeypatch.setattr(sim, "_worker_points", lambda lon: [])


def comp(dlat, dlon, a=3.0):
    return Competitor(name="c", kind="competitor", lat=LAT + dlat, lon=LON + dlon, distanceMi=0.5,
                      rating=None, reviewCount=None, isNew=False, attractiveness=a, source="osm")


def site(density=10_000, rent=3000.0, comps=()):
    return Site(id="s", listingId=1, propertyId=1, address="a", lat=LAT, lon=LON, sizeSqft=1200,
                rentMonthly=rent, rentPsfYear=None, serviceType="", spaceUse="", photoUrl=None,
                matterportModelId=None, aerial=None, interior=None, competitors=list(comps),
                demographics=Demographics(population=5000, tract="t", densityPerSqMi=density), sim=None, gaps=[])


def test_same_seed_same_odds():
    s = site(comps=[comp(0.005, 0), comp(-0.008, 0.004)])
    assert sim.simulate(s, BOBA).pProfitableBy12 == sim.simulate(s, BOBA).pProfitableBy12


def test_zero_people_zero_odds():
    assert sim.simulate(site(density=0, comps=[comp(0.005, 0)]), BOBA).pProfitableBy12 == 0


def test_free_rent_no_competitors_dense_area_near_certain():
    r = sim.simulate(site(density=20_000, rent=0), BOBA, {"newCompetitors": False})
    assert r.pProfitableBy12 > 0.95


def test_site_like_median_competitor_gets_typical_customers():
    # site and one competitor mirrored around the centre of the grid: same pull, so typical customers
    s = site(comps=[comp(0, 0)])
    assert sim.simulate(s, BOBA).expectedCustomers == pytest.approx(BOBA["typicalDailyCustomers"], rel=0.02)


def test_what_if_changes_only_the_override():
    s = site(rent=6000, comps=[comp(0.005, 0)])
    base, cheaper = sim.simulate(s, BOBA), sim.simulate(s, BOBA, {"rentMonthly": 2000})
    assert cheaper.pProfitableBy12 > base.pProfitableBy12
    assert cheaper.expectedCustomers == base.expectedCustomers


def test_unknown_override_rejected():
    with pytest.raises(ValueError):
        sim.simulate(site(), BOBA, {"rent": 1})


def test_fast_enough():
    s = site(comps=[comp(0.005 * i, 0.003) for i in range(1, 8)])
    t = time.perf_counter()
    sim.simulate(s, BOBA)
    assert time.perf_counter() - t < 1
