"""Tests for risk factor extraction (Dev 2 Hours 3–4.5)."""
from app.config import BUSINESS_PROFILES
from app.models import Aerial, Competitor, Demographics, RiskFactor, Site
from app.sim.risk import extract_risk_factors


def test_extract_risk_factors_top_three():
    site = Site(
        id="L123-S456",
        listingId=123,
        propertyId=456,
        address="1000 Main St, Houston, TX",
        lat=29.75,
        lon=-95.36,
        sizeSqft=1500,
        serviceType="TripleNet",
        spaceUse="Retail",
        rentMonthly=6500,  # high rent
        competitors=[
            Competitor(
                name="Tea Land",
                kind="competitor",
                lat=29.751,
                lon=-95.361,
                distanceMi=0.3,
                rating=4.5,
                reviewCount=250,
                isNew=False,
                attractiveness=3.5,
                source="yelp",
            ),
            Competitor(
                name="Quick Boba",
                kind="competitor",
                lat=29.752,
                lon=-95.362,
                distanceMi=0.4,
                rating=4.2,
                reviewCount=120,
                isNew=True,
                attractiveness=2.8,
                source="yelp",
            ),
        ],
        demographics=Demographics(
            population=12000,
            densityPerSqMi=2200,
            tract="48201",
        ),
        aerial=Aerial(
            parcelWkt="POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
            visibilityScore=2,
            visibilityReason="Tree canopy obstructs storefront visibility from street",
            imageUrl="/api/sites/L123/aerial.jpg",
        ),
    )

    profile = BUSINESS_PROFILES["boba"]
    sim_data = {
        "rent_share": 0.22,  # > 15% max
        "expected_customers": 95,
        "break_even_customers": 120,  # break even > expected
    }
    people = {"residents": 12000, "workers": 2100}

    risks = extract_risk_factors(site, profile, sim_data, people_nearby=people)

    assert isinstance(risks, list)
    assert len(risks) == 3
    for r in risks:
        assert isinstance(r, RiskFactor)
        assert r.impact > 0
        assert len(r.text) > 0

    factors = [r.factor for r in risks]
    # Check that duplicates are prevented
    assert len(set(factors)) == len(factors)


def test_extract_risk_factors_minimal_site():
    site = Site(
        id="L999",
        listingId=999,
        propertyId=888,
        address="Rural Rd",
        lat=29.7,
        lon=-95.3,
        sizeSqft=1000,
        serviceType="Gross",
        spaceUse="Retail",
        rentMonthly=1200,
    )
    profile = BUSINESS_PROFILES["coffee"]
    risks = extract_risk_factors(site, profile)

    assert isinstance(risks, list)
    assert len(risks) <= 3
