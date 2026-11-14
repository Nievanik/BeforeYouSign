"""Site simulation: people nearby -> Huff share -> daily customers -> 1,000 x 24-month P&L. See docs/simulation.md."""
import numpy as np

from app.models import Band, MonthBand, PeopleNearby, RiskFactor, SimResult, Site
from app.sim import huff, montecarlo
from app.sim.risk import extract_risk_factors

PROFILE_FIELDS = {
    "typicalDailyCustomers", "ticket", "ticketSd", "cogsMin", "cogsMax", "laborFixedMonthly", "laborVariablePct",
    "otherFixedMonthly", "daysOpen", "rampMin", "rampMax", "startupCost", "radiusMi", "lambda", "workerWeight",
    "newCompetitorRatePerYear", "rentShareMax",
}
SWITCHES = {"newCompetitors", "accessPenalty"}  # True (default) = factor on
OVERRIDE_KEYS = PROFILE_FIELDS | SWITCHES | {"rentMonthly"}
SEED = 7
DRIVE_HEAVY, POOR_ACCESS, ACCESS_PENALTY = 0.85, 2, 0.85
NEW_WINDOW_YEARS = 0.5  # shortcut: Yelp "hot and new" ~ last 6 months; label the rate as an estimate
BUCKETS = 5
# random input -> (direction that hurts, label); +1 = higher is worse
RISKS = {
    "customers": (-1, "fewer customers than expected"),
    "ticket": (-1, "lower spend per visit"),
    "rampMonths": (1, "slow ramp-up"),
    "cogs": (1, "high cost of goods"),
    "newCompetitors": (1, "new competitors opening"),
}


def _worker_points(lon: float):
    from app.tools.costar import _workers
    try:
        return _workers("CA" if lon < -110 else "TX")  # the kit only covers Houston and Los Angeles
    except Exception:
        return []


def check_overrides(overrides: dict) -> None:
    """Reject unknown keys, so an agent typo fails loudly instead of silently changing nothing."""
    unknown = set(overrides) - OVERRIDE_KEYS
    if unknown:
        raise ValueError(f"unknown override(s) {sorted(unknown)}; allowed: {sorted(OVERRIDE_KEYS)}")


def simulate(site: Site, profile: dict, overrides: dict | None = None, seed: int = SEED) -> SimResult:
    """Odds of profit for one site.

    site: needs lat/lon, rentMonthly, competitors, demographics, aerial (visibility/road access).
    profile: one BUSINESS_PROFILES entry (fields in PROFILE_FIELDS).
    overrides: what-if changes on top of profile and site, e.g. {"rentMonthly": 5200}, {"newCompetitors": False}.
    Same seed -> same result, so a what-if difference comes only from the override.
    SimResult.assumptions = every input actually used (profile + overrides + rentMonthly), so the UI can edit
    them and send changes back as overrides.
    """
    overrides = overrides or {}
    check_overrides(overrides)
    p = {**profile, **{k: v for k, v in overrides.items() if k in PROFILE_FIELDS}}
    rent = overrides.get("rentMonthly", site.rentMonthly) or 0
    notes = []

    density = (site.demographics.densityPerSqMi if site.demographics else None) or 0
    if not density:
        notes.append("no Census density: residents counted as 0")
    x, y, people, residents, workers = huff.grid(site.lat, site.lon, p["radiusMi"], density,
                                                 _worker_points(site.lon), p["workerWeight"])

    comps = [c for c in site.competitors if c.kind == "competitor"]
    cx, cy = huff.store_xy(site.lat, site.lon, [(c.lat, c.lon) for c in comps])
    a_comp = np.array([c.attractiveness for c in comps])
    a_median = float(np.median(a_comp)) if comps else 1.0

    a = site.aerial
    visibility = 0.8 + 0.1 * (a.visibilityScore - 1) if a and a.visibilityScore else 1.0
    drive = site.demographics.driveShare if site.demographics else None
    poor_access = bool(drive is not None and drive >= DRIVE_HEAVY and a and a.roadAccessScore
                       and a.roadAccessScore <= POOR_ACCESS)
    access = ACCESS_PENALTY if poor_access and overrides.get("accessPenalty", True) else 1.0
    a_site = a_median * visibility * access

    def pulls(extra_x=(), extra_y=(), extra_a=()):
        """People-weighted pull of every store; column 0 is our site."""
        sx, sy = np.r_[0.0, cx, extra_x], np.r_[0.0, cy, extra_y]
        return (people[:, None] * huff.shares(x, y, sx, sy, np.r_[a_site, a_comp, extra_a], p["lambda"])).sum(axis=0)

    def site_pull(*extra):
        return float(pulls(*extra)[0])

    all_pulls = pulls()
    pull = float(all_pulls[0])
    if people.sum() == 0:
        mean_site = 0.0
    elif comps:
        # calibrate visits per person so the median competitor (in the market with us open) serves a typical day
        mean_site = p["typicalDailyCustomers"] / float(np.median(all_pulls[1:])) * pull
    else:
        # shortcut: nothing to calibrate against, so assume a typical store; upgrade with a city-wide visit rate
        mean_site = float(p["typicalDailyCustomers"])
        notes.append("competitor data missing: typical demand assumed" if any(g.startswith("no competitors") for g in site.gaps)
                     else "no competitors nearby: typical demand assumed")

    hot_new = sum(c.isNew for c in comps)
    rate = hot_new / NEW_WINDOW_YEARS if hot_new else p["newCompetitorRatePerYear"]
    # demand kept when one median-strength shop opens at each distance bucket (placed due east: shortcut)
    dists = np.linspace(0.1, p["radiusMi"], BUCKETS)
    cuts = np.array([site_pull([d], [0.0], [a_median]) / pull if pull else 1.0 for d in dists])

    r = montecarlo.run(mean_site, p, rent, rate, cuts, seed, overrides.get("newCompetitors", True))
    profit = r["profit"]
    m = montecarlo.MONTHS
    first = np.where((profit[:, :m] >= 0).any(axis=1), (profit[:, :m] >= 0).argmax(axis=1) + 1, np.inf)
    cum = profit.cumsum(axis=1)
    paid = np.where((cum >= p["startupCost"]).any(axis=1), (cum >= p["startupCost"]).argmax(axis=1) + 1, np.inf)
    band = lambda v: Band(p10=float(np.percentile(v, 10)), p50=float(np.percentile(v, 50)),
                          p90=float(np.percentile(v, 90)))
    med = lambda v: None if np.isinf(np.median(v)) else int(np.median(v))

    margin = p["ticket"] * (1 - (p["cogsMin"] + p["cogsMax"]) / 2 - p["laborVariablePct"]) * p["daysOpen"]
    fixed = p["laborFixedMonthly"] + rent + p["otherFixedMonthly"]
    revenue = mean_site * p["ticket"] * p["daysOpen"]
    rent_share = rent / revenue if revenue else float("inf")

    risks = []
    if rent_share > p["rentShareMax"]:
        risks.append(RiskFactor(factor="rent", impact=round(rent_share / p["rentShareMax"], 2),
                                text=f"rent is {rent_share:.0%} of expected revenue (healthy: under {p['rentShareMax']:.0%})"))
    losing = profit[:, 11] < 0
    if losing.any() and not losing.all():
        scored = []
        for k, (sign, label) in RISKS.items():
            v = r[k]
            if v.std() > 0:
                scored.append((sign * (v[losing].mean() - v.mean()) / v.std(), k, label))
        risks += [RiskFactor(factor=k, impact=round(float(s), 2), text=label)
                  for s, k, label in sorted(scored, reverse=True) if s > 0]

    return SimResult(
        pProfitableBy12=float((profit[:, 11] >= 0).mean()),
        medianMonthProfitable=med(first),
        profitM12=band(profit[:, 11]),
        monthlyBands=[MonthBand(month=i + 1, **band(profit[:, i]).model_dump()) for i in range(m)],
        expectedCustomers=round(mean_site, 1),
        breakEvenCustomers=round(fixed / margin, 1) if margin > 0 else float("inf"),
        rentShare=round(rent_share, 3),
        paybackMonths=med(paid),
        peopleNearby=PeopleNearby(residents=round(residents), workers=round(workers)),
        riskFactors=risks[:3],
        assumptions={**p, "rentMonthly": rent, "newCompetitorRatePerYear": rate, "visibility": round(visibility, 2),
                     "access": access, "notes": notes},
        seed=seed,
    )


__all__ = [
    "PROFILE_FIELDS",
    "SWITCHES",
    "OVERRIDE_KEYS",
    "check_overrides",
    "simulate",
    "extract_risk_factors",
]
