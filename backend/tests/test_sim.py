"""Simulation validation suite (docs/simulation.md Section 8).

Validates reproducibility, edge cases (zero demand, zero rent), calibration, and runtime performance.
"""
import time

from app.config import BUSINESS_PROFILES
from app.models import Competitor, Demographics, Site
from app.sim.huff import estimate_huff_demand
from app.sim.montecarlo import simulate_site


def _make_sample_site(rent=2500, competitors=None, population=25000):
    return Site(
        id="L100-S100",
        listingId=100,
        propertyId=200,
        address="123 Test St",
        lat=29.75,
        lon=-95.36,
        sizeSqft=1500,
        serviceType="TripleNet",
        spaceUse="Retail",
        rentMonthly=rent,
        competitors=competitors or [],
        demographics=Demographics(
            population=population,
            densityPerSqMi=4000,
            tract="48201",
        ),
    )


def test_simulation_reproducibility():
    """Same seed produces identical results."""
    site = _make_sample_site()
    profile = BUSINESS_PROFILES["boba"]

    res1 = simulate_site(site, profile, seed=42)
    res2 = simulate_site(site, profile, seed=42)

    assert res1.pProfitableBy12 == res2.pProfitableBy12
    assert res1.profitM12.p50 == res2.profitM12.p50
    assert res1.expectedCustomers == res2.expectedCustomers


def test_zero_people_zero_profit():
    """Zero people nearby guarantees 0% chance of profitability."""
    site = _make_sample_site(population=0)
    profile = BUSINESS_PROFILES["coffee"]

    res = simulate_site(site, profile, workers_count=0.0, residents_count=0.0)

    assert res.pProfitableBy12 == 0.0
    assert res.expectedCustomers == 0.0
    assert res.profitM12.p50 < 0


def test_zero_rent_no_competitors_high_profit():
    """Rent $0, no competitors, and high demand produces near 100% odds."""
    site = _make_sample_site(rent=0, competitors=[], population=60000)
    profile = BUSINESS_PROFILES["boba"]

    res = simulate_site(site, profile, workers_count=10000.0, residents_count=60000.0)

    assert res.pProfitableBy12 >= 0.85
    assert res.profitM12.p50 > 0


def test_calibration_matches_typical():
    """Site identical to the median competitor gets exactly typicalDailyCustomers."""
    # Competitor sharing the same trade location and median attractiveness
    comp = Competitor(
        name="Median Shop",
        kind="competitor",
        lat=29.75,
        lon=-95.36,
        distanceMi=0.0,
        rating=4.0,
        reviewCount=20,
        isNew=False,
        attractiveness=3.04,
        source="osm",
    )
    site = _make_sample_site(competitors=[comp])
    profile = BUSINESS_PROFILES["boba"]

    cust, _ = estimate_huff_demand(site, profile, workers_count=5000.0, residents_count=25000.0)
    typical = profile["typicalDailyCustomers"]

    # Identical store gets exactly the calibrated typical benchmark
    assert cust == typical


def test_simulation_performance():
    """1,000 runs complete in well under 1 second."""
    site = _make_sample_site()
    profile = BUSINESS_PROFILES["fast_casual"]

    t0 = time.perf_counter()
    res = simulate_site(site, profile, num_runs=1000, seed=123)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.5  # must run fast (< 500 ms)
    assert len(res.monthlyBands) == 24
