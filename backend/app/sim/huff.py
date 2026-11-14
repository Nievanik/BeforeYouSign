"""Huff gravity model (docs/simulation.md Section 2 & 3).

Estimates spatial customer choice probabilities between candidate site and competitors,
and calibrates daily visits against industry benchmarks.
"""
import math
from typing import Any, Optional

from app.geo import miles
from app.models import Competitor, Site


def competitor_attractiveness(c: Competitor, beta: float = 2.0) -> float:
    """Attractiveness score based on Yelp / OSM reputation."""
    rating = c.rating if c.rating is not None else 4.0
    reviews = c.reviewCount if c.reviewCount is not None else 20
    # A = (rating / 4.0)^beta * log(1 + reviewCount)
    score = ((rating / 4.0) ** beta) * math.log(1.0 + max(0, reviews))
    return max(0.1, score)


def site_attractiveness(site: Site, competitors: list[Competitor], default: float = 3.5) -> float:
    """Attractiveness for the new site: starts at competitor median, modified by visibility & access."""
    comp_a = [competitor_attractiveness(c) for c in competitors if c.kind == "competitor"]
    if comp_a:
        comp_a.sort()
        mid = len(comp_a) // 2
        base_a = comp_a[mid] if len(comp_a) % 2 != 0 else (comp_a[mid - 1] + comp_a[mid]) / 2.0
    else:
        base_a = default

    # Visibility modifier from Vexcel vision score (1-5 -> 0.8 - 1.2)
    vis_mod = 1.0
    if site.aerial and site.aerial.visibilityScore:
        vis_mod = 0.8 + 0.1 * (site.aerial.visibilityScore - 1)

    # Road access modifier: 0.85 if car-dependent and low road access score
    access_mod = 1.0
    if site.demographics and site.demographics.driveShare and site.demographics.driveShare >= 0.85:
        if site.aerial and site.aerial.roadAccessScore and site.aerial.roadAccessScore <= 2:
            access_mod = 0.85

    return base_a * vis_mod * access_mod


def estimate_huff_demand(
    site: Site,
    profile: dict[str, Any],
    workers_count: float = 5000.0,
    residents_count: Optional[float] = None,
) -> tuple[float, float]:
    """Calculate mature daily customer visits (mean_site) and total people nearby using Huff model.

    Returns:
        (mean_site_daily_customers, total_people_nearby)
    """
    radius = profile.get("radiusMi", 1.0)
    decay_lambda = profile.get("lambda", 2.0)
    worker_weight = profile.get("workerWeight", 0.5)
    typical_daily = profile.get("typicalDailyCustomers", 110)

    # Calculate people nearby
    if residents_count is None:
        residents_count = float(site.demographics.population) if site.demographics else 25000.0

    total_people = residents_count + worker_weight * workers_count
    if total_people <= 0:
        return 0.0, 0.0

    comps = [c for c in (site.competitors or []) if c.kind == "competitor"]
    site_a = site_attractiveness(site, comps)

    if not comps:
        # Monopoly in trade area: captures benchmark typical customers
        return float(typical_daily), total_people

    # Generate representative grid points around site (concentric rings)
    # Ring distances: 0.25, 0.5, 0.75, 1.0 of radius
    ring_fractions = [0.25, 0.5, 0.75, 1.0]
    ring_weights = [0.10, 0.25, 0.35, 0.30]  # area proportional

    site_pull = 0.0
    comp_pulls = [0.0] * len(comps)

    for dist_frac, weight in zip(ring_fractions, ring_weights):
        pop_slice = total_people * weight
        d_site = max(0.05, radius * dist_frac)

        # Attractiveness over distance^lambda
        u_site = site_a / (d_site ** decay_lambda)
        u_comps = []
        for c in comps:
            # Average distance from ring to competitor located at c.distanceMi from site
            d_comp = max(0.05, math.sqrt(d_site ** 2 + c.distanceMi ** 2))
            a_c = competitor_attractiveness(c)
            u_comps.append(a_c / (d_comp ** decay_lambda))

        total_u = u_site + sum(u_comps)
        p_site = u_site / total_u if total_u > 0 else 0.5
        site_pull += pop_slice * p_site

        for idx, u_c in enumerate(u_comps):
            comp_pulls[idx] += pop_slice * (u_c / total_u if total_u > 0 else 0.0)

    # Calibration rate r: typicalDailyCustomers / median_j(pull_j)
    comp_pulls.sort()
    mid = len(comp_pulls) // 2
    median_comp_pull = comp_pulls[mid] if len(comp_pulls) % 2 != 0 else (comp_pulls[mid - 1] + comp_pulls[mid]) / 2.0

    if median_comp_pull > 0:
        visit_rate = typical_daily / median_comp_pull
        mean_site = visit_rate * site_pull
    else:
        mean_site = float(typical_daily)

    return max(1.0, round(mean_site, 1)), total_people
