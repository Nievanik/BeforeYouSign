"""People nearby on a grid, and the Huff model: how they split between the shops within reach."""
import math
from typing import Any, Optional

import numpy as np

from app.models import Competitor, Site

CELL_M = 200
SQMI_PER_CELL = (CELL_M / 1609.344) ** 2
MIN_DIST_MI = 0.05
MI_PER_DEG_LAT = 69.055


def _offsets_mi(lat: float, dlat, dlon):
    return np.asarray(dlon) * MI_PER_DEG_LAT * math.cos(math.radians(lat)), np.asarray(dlat) * MI_PER_DEG_LAT


def grid(lat: float, lon: float, radius_mi: float, density_per_sqmi: float,
         workers: list[tuple[float, float, int]], worker_weight: float):
    """Demand points every 200 m within the radius.

    Returns (x, y) in miles from the site, people per point, total residents, total workers.
    shortcut: every cell uses the site tract's density; upgrade to per-cell tracts if time allows.
    """
    step = CELL_M / 1609.344
    n = int(radius_mi / step)
    gx, gy = np.meshgrid(np.arange(-n, n + 1) * step, np.arange(-n, n + 1) * step)
    inside = np.hypot(gx, gy) <= radius_mi
    x, y = gx[inside], gy[inside]
    residents = np.full(x.shape, density_per_sqmi * SQMI_PER_CELL)

    jobs = np.zeros(x.shape)
    if workers:
        w = np.asarray(workers, dtype=float)
        wx, wy = _offsets_mi(lat, w[:, 0] - lat, w[:, 1] - lon)
        near = np.hypot(wx, wy) <= radius_mi
        if near.any():
            # snap each company to its nearest cell
            idx = np.argmin((x[None, :] - wx[near, None]) ** 2 + (y[None, :] - wy[near, None]) ** 2, axis=1)
            np.add.at(jobs, idx, w[near, 2])
    return x, y, residents + worker_weight * jobs, float(residents.sum()), float(jobs.sum())


def shares(x, y, sx, sy, attract, lam: float):
    """P(point i -> store j): (A_j / d_ij^lam) / sum_k (A_k / d_ik^lam). Shape (points, stores)."""
    d = np.maximum(np.hypot(x[:, None] - np.asarray(sx)[None, :], y[:, None] - np.asarray(sy)[None, :]), MIN_DIST_MI)
    u = np.asarray(attract)[None, :] / d ** lam
    return u / u.sum(axis=1, keepdims=True)


def store_xy(lat: float, lon: float, points: list[tuple[float, float]]):
    lats, lons = zip(*points) if points else ((), ())
    return _offsets_mi(lat, np.subtract(lats, lat), np.subtract(lons, lon))


def competitor_attractiveness(c: Competitor, beta: float = 2.0) -> float:
    """Attractiveness score based on Yelp / OSM reputation."""
    rating = c.rating if c.rating is not None else 4.0
    reviews = c.reviewCount if c.reviewCount is not None else 20
    score = ((rating / 4.0) ** beta) * math.log(1.0 + max(0, reviews))
    return max(0.1, score)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    mid = len(values) // 2
    return values[mid] if len(values) % 2 != 0 else (values[mid - 1] + values[mid]) / 2.0


def site_attractiveness(site: Site, competitors: list[Competitor], default: float = 3.5) -> float:
    """Attractiveness for the new site: starts at competitor median, modified by visibility & access."""
    comp_a = [competitor_attractiveness(c) for c in competitors if c.kind == "competitor"]
    base_a = _median(comp_a) if comp_a else default

    vis_mod = 1.0
    if site.aerial and site.aerial.visibilityScore:
        vis_mod = 0.8 + 0.1 * (site.aerial.visibilityScore - 1)

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
    """Calculate mature daily customer visits (mean_site) and total people nearby using Huff model."""
    radius = float(profile.get("radiusMi", 1.0))
    decay_lambda = float(profile.get("lambda", 2.0))
    worker_weight = float(profile.get("workerWeight", 0.5))
    typical_daily = float(profile.get("typicalDailyCustomers", 110))

    if residents_count is None:
        residents_count = float(site.demographics.population) if site.demographics else 25000.0

    total_people = residents_count + worker_weight * workers_count
    if total_people <= 0:
        return 0.0, 0.0

    comps = [c for c in (site.competitors or []) if c.kind == "competitor"]
    site_a = site_attractiveness(site, comps)

    if not comps:
        return float(typical_daily), total_people

    ring_fractions = [0.25, 0.5, 0.75, 1.0]
    ring_weights = [0.10, 0.25, 0.35, 0.30]

    site_pull = 0.0
    comp_pulls = [0.0] * len(comps)

    for dist_frac, weight in zip(ring_fractions, ring_weights):
        pop_slice = total_people * weight
        d_site = max(0.05, radius * dist_frac)

        u_site = site_a / (d_site ** decay_lambda)
        u_comps = []
        for c in comps:
            d_comp = max(0.05, math.sqrt(d_site ** 2 + c.distanceMi ** 2))
            a_c = competitor_attractiveness(c)
            u_comps.append(a_c / (d_comp ** decay_lambda))

        total_u = u_site + sum(u_comps)
        p_site = u_site / total_u if total_u > 0 else 0.5
        site_pull += pop_slice * p_site

        for idx, u_c in enumerate(u_comps):
            comp_pulls[idx] += pop_slice * (u_c / total_u if total_u > 0 else 0.0)

    median_comp_pull = _median(comp_pulls)
    if median_comp_pull > 0:
        visit_rate = typical_daily / median_comp_pull
        mean_site = visit_rate * site_pull
    else:
        mean_site = float(typical_daily)

    return max(1.0, round(mean_site, 1)), total_people
