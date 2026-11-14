"""Site simulation: people nearby -> Huff share -> daily customers -> 1,000 x 24-month P&L. See docs/simulation.md."""
from app.models import SimResult, Site

PROFILE_FIELDS = {
    "typicalDailyCustomers", "ticket", "ticketSd", "cogsMin", "cogsMax", "laborFixedMonthly", "laborVariablePct",
    "otherFixedMonthly", "daysOpen", "rampMin", "rampMax", "startupCost", "radiusMi", "lambda", "workerWeight",
    "newCompetitorRatePerYear", "rentShareMax",
}
SWITCHES = {"newCompetitors", "accessPenalty"}  # True (default) = factor on
OVERRIDE_KEYS = PROFILE_FIELDS | SWITCHES | {"rentMonthly"}
RUNS, MONTHS, SEED = 1000, 24, 7


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
    check_overrides(overrides or {})
    raise NotImplementedError("Dev 1, hours 0.5-3: sim/huff.py + sim/montecarlo.py")
