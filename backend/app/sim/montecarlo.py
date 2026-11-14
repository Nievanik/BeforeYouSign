"""1,000 runs x 36 months of P&L. Months 1-24 feed the odds and bands; 25-36 only the payback."""
import numpy as np

RUNS, MONTHS, PAYBACK_MONTHS = 1000, 24, 36
CUSTOMER_SIGMA = 0.35
RAMP_START = 0.4


def run(mean_customers: float, p: dict, rent: float, entrant_rate: float, cut_by_bucket: np.ndarray,
        seed: int, new_competitors: bool = True) -> dict:
    """Random draws per run and the monthly profit matrix. cut_by_bucket[k] = demand kept after one entrant
    opens in distance bucket k (5 buckets from 0.1 mi to the radius)."""
    rng = np.random.default_rng(seed)
    n, T = RUNS, PAYBACK_MONTHS
    customers = mean_customers * rng.lognormal(0, CUSTOMER_SIGMA, n)
    ticket = np.maximum(rng.normal(p["ticket"], p["ticketSd"], n), 0.5 * p["ticket"])
    ramp_months = rng.uniform(p["rampMin"], p["rampMax"], n)
    cogs = rng.uniform(p["cogsMin"], p["cogsMax"], n)

    m = np.arange(1, T + 1)
    ramp = np.minimum(1, RAMP_START + (1 - RAMP_START) * (m[None, :] - 1) / np.maximum(ramp_months[:, None], 1))

    entrants = rng.poisson(entrant_rate * MONTHS / 12, n) if new_competitors else np.zeros(n, int)
    comp_cut = np.ones((n, T))
    for r in np.nonzero(entrants)[0]:
        for _ in range(entrants[r]):
            month = rng.integers(0, MONTHS)  # opens at month index `month`, hurts from then on
            comp_cut[r, month:] *= cut_by_bucket[rng.integers(0, len(cut_by_bucket))]

    revenue = customers[:, None] * ramp * comp_cut * ticket[:, None] * p["daysOpen"]
    profit = (revenue * (1 - cogs[:, None] - p["laborVariablePct"])
              - p["laborFixedMonthly"] - rent - p["otherFixedMonthly"])
    return {"customers": customers, "ticket": ticket, "rampMonths": ramp_months, "cogs": cogs,
            "newCompetitors": entrants.astype(float), "profit": profit}
