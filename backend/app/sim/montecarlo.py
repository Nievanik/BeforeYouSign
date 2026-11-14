"""Monte Carlo simulation helpers."""
from typing import Any, Optional

import numpy as np

from app.models import Band, MonthBand, PeopleNearby, SimResult, Site
from app.sim.huff import estimate_huff_demand
from app.sim.risk import extract_risk_factors

RUNS, MONTHS, PAYBACK_MONTHS = 1000, 24, 36
CUSTOMER_SIGMA = 0.6  # first-year sales forecasts routinely miss by 50%+
RAMP_START = 0.4


def run(mean_customers: float, p: dict, rent: float, entrant_rate: float, cut_by_bucket: np.ndarray,
        seed: int, new_competitors: bool = True) -> dict:
    """Random draws per run and the monthly profit matrix."""
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
            month = rng.integers(0, MONTHS)
            comp_cut[r, month:] *= cut_by_bucket[rng.integers(0, len(cut_by_bucket))]

    revenue = customers[:, None] * ramp * comp_cut * ticket[:, None] * p["daysOpen"]
    profit = (
        revenue * (1 - cogs[:, None] - p["laborVariablePct"])
        - p["laborFixedMonthly"]
        - rent
        - p["otherFixedMonthly"]
    )
    return {
        "customers": customers,
        "ticket": ticket,
        "rampMonths": ramp_months,
        "cogs": cogs,
        "newCompetitors": entrants.astype(float),
        "profit": profit,
    }


def simulate_site(
    site: Site,
    profile: dict[str, Any],
    workers_count: float = 5000.0,
    residents_count: Optional[float] = None,
    num_runs: int = RUNS,
    seed: int = 42,
    overrides: Optional[dict[str, Any]] = None,
) -> SimResult:
    """Compatibility wrapper for full-site simulation."""
    profile = {**profile, **(overrides or {})}
    rng = np.random.default_rng(seed)

    mean_site, total_people = estimate_huff_demand(
        site, profile, workers_count=workers_count, residents_count=residents_count
    )

    ticket_mean = float(profile.get("ticket", 8.0))
    ticket_sd = float(profile.get("ticketSd", 1.25))
    days_open = int(profile.get("daysOpen", 30))
    cogs_min = float(profile.get("cogsMin", 0.25))
    cogs_max = float(profile.get("cogsMax", 0.35))
    ramp_min = int(profile.get("rampMin", 3))
    ramp_max = int(profile.get("rampMax", 9))
    labor_fixed = float(profile.get("laborFixedMonthly", 7000.0))
    labor_var_pct = float(profile.get("laborVariablePct", 0.0))
    other_fixed = float(profile.get("otherFixedMonthly", 1500.0))
    startup_cost = float(profile.get("startupCost", 110000.0))
    rent_monthly = float(site.rentMonthly or 0.0)

    if total_people <= 0 or mean_site <= 0:
        fixed = rent_monthly + labor_fixed + other_fixed
        zero_band = Band(p10=-round(fixed, 2), p50=-round(fixed, 2), p90=-round(fixed, 2))
        monthly_bands = [MonthBand(month=m, p10=zero_band.p10, p50=zero_band.p50, p90=zero_band.p90) for m in range(1, 25)]
        return SimResult(
            pProfitableBy12=0.0,
            medianMonthProfitable=None,
            profitM12=zero_band,
            monthlyBands=monthly_bands,
            expectedCustomers=0.0,
            breakEvenCustomers=100.0,
            rentShare=1.0,
            paybackMonths=None,
            peopleNearby=PeopleNearby(residents=0.0, workers=0.0),
            riskFactors=[],
            assumptions=profile,
            seed=seed,
        )

    customers = rng.lognormal(mean=np.log(mean_site), sigma=CUSTOMER_SIGMA, size=num_runs)
    ticket = np.maximum(ticket_mean * 0.5, rng.normal(loc=ticket_mean, scale=ticket_sd, size=num_runs))
    ramp_months = rng.integers(low=ramp_min, high=ramp_max + 1, size=num_runs)
    cogs = rng.uniform(low=cogs_min, high=cogs_max, size=num_runs)

    month_indices = np.arange(1, 25)
    ramp_grid = np.zeros((num_runs, 24))
    for r in range(num_runs):
        m_mat = ramp_months[r]
        for m_idx, m in enumerate(month_indices):
            if m >= m_mat:
                ramp_grid[r, m_idx] = 1.0
            else:
                ramp_grid[r, m_idx] = RAMP_START + (1 - RAMP_START) * (m / m_mat)

    comp_rate = float(profile.get("newCompetitorRatePerYear", 0.3))
    new_comps = rng.poisson(lam=comp_rate * 2.0, size=num_runs)
    comp_cut = np.maximum(0.60, 1.0 - 0.06 * new_comps)
    comp_grid = np.ones((num_runs, 24))
    for r in range(num_runs):
        comp_grid[r, 6:] = comp_cut[r]

    rev = customers[:, None] * ramp_grid * comp_grid * ticket[:, None] * days_open
    net_margin = 1.0 - cogs[:, None] - labor_var_pct
    fixed_overhead = labor_fixed + rent_monthly + other_fixed
    profits = rev * net_margin - fixed_overhead

    m12_profits = profits[:, 11]
    p_profitable_m12 = float(np.mean(m12_profits >= 0))

    first_months = []
    for r in range(num_runs):
        profitable_indices = np.where(profits[r, :] >= 0)[0]
        if len(profitable_indices) > 0:
            first_months.append(profitable_indices[0] + 1)
    median_first_month = int(np.median(first_months)) if first_months and len(first_months) >= num_runs * 0.4 else None

    monthly_bands = [
        MonthBand(
            month=m + 1,
            p10=round(float(np.percentile(profits[:, m], 10)), 2),
            p50=round(float(np.percentile(profits[:, m], 50)), 2),
            p90=round(float(np.percentile(profits[:, m], 90)), 2),
        )
        for m in range(24)
    ]

    avg_cogs = (cogs_min + cogs_max) / 2.0
    contrib_per_cust = ticket_mean * (1.0 - avg_cogs - labor_var_pct)
    be_cust = (fixed_overhead / days_open) / contrib_per_cust if contrib_per_cust > 0 else 100.0

    exp_rev = mean_site * ticket_mean * days_open
    rent_share = rent_monthly / exp_rev if exp_rev > 0 else 0.20

    cum_profits = np.cumsum(profits, axis=1)
    payback_months_list = []
    for r in range(num_runs):
        recovered = np.where(cum_profits[r, :] >= startup_cost)[0]
        if len(recovered) > 0:
            payback_months_list.append(recovered[0] + 1)
    payback_months = int(np.median(payback_months_list)) if len(payback_months_list) >= num_runs * 0.5 else None

    loss_mask = m12_profits < 0
    mc_stats: dict[str, float] = {}
    if np.any(loss_mask) and not np.all(loss_mask):
        def calc_impact(arr: np.ndarray) -> float:
            std = np.std(arr)
            return float(abs(np.mean(arr[loss_mask]) - np.mean(arr)) / std) if std > 0 else 0.1

        mc_stats["customers"] = calc_impact(customers)
        mc_stats["ticket"] = calc_impact(ticket)
        mc_stats["cogs"] = calc_impact(cogs)
        mc_stats["new_competitors"] = calc_impact(new_comps)

    sim_data = {
        "rent_share": rent_share,
        "expected_customers": mean_site,
        "break_even_customers": be_cust,
        "p_profitable": p_profitable_m12,
        "monte_carlo_stats": mc_stats,
    }
    people_dict = {"residents": float(residents_count or 25000), "workers": float(workers_count)}
    risks = extract_risk_factors(site, profile, sim_data, people_nearby=people_dict)

    return SimResult(
        pProfitableBy12=round(p_profitable_m12, 2),
        medianMonthProfitable=median_first_month,
        profitM12=Band(
            p10=round(float(np.percentile(m12_profits, 10)), 2),
            p50=round(float(np.percentile(m12_profits, 50)), 2),
            p90=round(float(np.percentile(m12_profits, 90)), 2),
        ),
        monthlyBands=monthly_bands,
        expectedCustomers=round(float(mean_site), 1),
        breakEvenCustomers=round(float(be_cust), 1),
        rentShare=round(float(rent_share), 3),
        paybackMonths=payback_months,
        peopleNearby=PeopleNearby(residents=float(residents_count or 25000), workers=float(workers_count)),
        riskFactors=risks,
        assumptions={
            "avgTicket": ticket_mean,
            "daysOpen": days_open,
            "startupCost": startup_cost,
            "runs": num_runs,
        },
        seed=seed,
    )
