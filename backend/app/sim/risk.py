"""Risk factors extraction: identifies the top 3 risk factors in plain English with site evidence.

Plugs into SimResult (see docs/simulation.md Section 7).
"""
from typing import Any, Optional

from app.models import RiskFactor, Site


def extract_risk_factors(
    site: Site,
    profile: dict[str, Any],
    sim_data: Optional[dict[str, Any]] = None,
    people_nearby: Optional[dict[str, float]] = None,
) -> list[RiskFactor]:
    """Identify and rank the top 3 business risk factors with grounded site evidence.

    Args:
        site: Candidate commercial Site object with demographics, competitors, aerial info.
        profile: Business profile dictionary from config.BUSINESS_PROFILES.
        sim_data: Optional dictionary containing simulation metrics:
            - "rent_share": float (rent ÷ expected monthly revenue)
            - "expected_customers": float (mature customers/day)
            - "break_even_customers": float (customers/day needed for profit=0)
            - "p_profitable": float (0-1 odds)
            - "monte_carlo_stats": dict of {factor_name: impact_score} from losing runs
        people_nearby: Optional {"residents": float, "workers": float}

    Returns:
        list[RiskFactor] with the top 3 drivers sorted by impact descending.
    """
    sim_data = sim_data or {}
    mc_stats = sim_data.get("monte_carlo_stats", {})

    candidates: list[RiskFactor] = []

    # 1. Competitor density & strength
    comps = [c for c in (site.competitors or []) if c.kind == "competitor"]
    comp_count = len(comps)
    radius = profile.get("radiusMi", 1.0)
    b_type = profile.get("businessType", "business")

    if comp_count > 0:
        ratings = [c.rating for c in comps if c.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 4.0
        tot_reviews = sum(c.reviewCount or 0 for c in comps)
        
        # Closest competitors
        close_comps = [c for c in comps if c.distanceMi <= min(0.5, radius)]
        if len(close_comps) > 0 and len(close_comps) < comp_count:
            comp_text = f"{len(close_comps)} {b_type} shop{'s' if len(close_comps) > 1 else ''} within {close_comps[0].distanceMi:.1f} mi ({comp_count} total within {radius} mi)"
        else:
            comp_text = f"{comp_count} established competitor{'s' if comp_count > 1 else ''} within {radius} mi (avg {avg_rating:.1f}★, {tot_reviews}+ reviews)"

        # Determine impact score
        impact = mc_stats.get("competitors")
        if impact is None:
            # Baseline heuristic: normalized by radius & expected market capacity
            impact = min(0.40, 0.12 + 0.04 * comp_count)
            if avg_rating >= 4.3 and tot_reviews > 300:
                impact += 0.06

        candidates.append(RiskFactor(
            factor="competitors",
            impact=round(float(impact), 2),
            text=comp_text,
        ))

    # 2. Rent burden relative to revenue
    rent_share = sim_data.get("rent_share")
    if rent_share is None and site.rentMonthly:
        typical_cust = profile.get("typicalDailyCustomers", 100)
        ticket = profile.get("ticket", 10.0)
        days = profile.get("daysOpen", 30)
        est_monthly_rev = typical_cust * ticket * days
        rent_share = site.rentMonthly / est_monthly_rev if est_monthly_rev > 0 else 0.20

    if rent_share is not None:
        rent_share_max = profile.get("rentShareMax", 0.15)
        rent_pct = int(round(rent_share * 100))
        max_pct = int(round(rent_share_max * 100))

        if rent_share > rent_share_max:
            rent_text = f"Rent is {rent_pct}% of expected revenue (exceeds recommended {max_pct}% ceiling)"
        else:
            rent_text = f"Rent is {rent_pct}% of expected revenue (healthy below {max_pct}%)"

        impact = mc_stats.get("rent")
        if impact is None:
            # Higher impact when rent exceeds the recommended ceiling
            ratio = rent_share / rent_share_max if rent_share_max > 0 else 1.0
            impact = min(0.45, 0.10 * ratio)

        candidates.append(RiskFactor(
            factor="rent",
            impact=round(float(impact), 2),
            text=rent_text,
        ))

    # 3. Customer demand & break-even threshold
    exp_cust = sim_data.get("expected_customers")
    be_cust = sim_data.get("break_even_customers")

    if exp_cust is not None and be_cust is not None:
        if be_cust > exp_cust:
            cust_text = f"Requires {int(round(be_cust))} customers/day to break even vs {int(round(exp_cust))} expected"
            cust_impact = mc_stats.get("customers", 0.35)
        else:
            cust_text = f"Expected {int(round(exp_cust))} customers/day comfortably clears {int(round(be_cust))} break-even"
            cust_impact = mc_stats.get("customers", 0.14)

        candidates.append(RiskFactor(
            factor="customers",
            impact=round(float(cust_impact), 2),
            text=cust_text,
        ))
    elif site.demographics and site.demographics.densityPerSqMi:
        density = site.demographics.densityPerSqMi
        if density < 3000:
            cust_text = f"Low residential density: {int(round(density)):,} people/sq mi in tract {site.demographics.tract}"
            cust_impact = 0.22
        else:
            cust_text = f"Local population density: {int(round(density)):,} people/sq mi in tract {site.demographics.tract}"
            cust_impact = 0.12

        candidates.append(RiskFactor(
            factor="customers",
            impact=round(float(cust_impact), 2),
            text=cust_text,
        ))

    # 4. Daytime worker foot traffic
    workers = None
    if people_nearby and "workers" in people_nearby:
        workers = people_nearby["workers"]

    if workers is not None:
        worker_impact = mc_stats.get("workers")
        if workers < 3000:
            worker_text = f"Only {int(round(workers)):,} daytime workers within {radius} mi"
            if worker_impact is None:
                worker_impact = 0.18
        else:
            worker_text = f"{int(round(workers)):,} daytime workers within {radius} mi bolster midday demand"
            if worker_impact is None:
                worker_impact = 0.09

        candidates.append(RiskFactor(
            factor="workers",
            impact=round(float(worker_impact), 2),
            text=worker_text,
        ))

    # 5. Physical visibility & roadway access
    if site.aerial:
        a = site.aerial
        if a.visibilityScore is not None and a.visibilityScore <= 2:
            vis_text = a.visibilityReason or f"Storefront visibility scored low ({a.visibilityScore}/5) from arterial road"
            candidates.append(RiskFactor(
                factor="visibility",
                impact=round(float(mc_stats.get("visibility", 0.21)), 2),
                text=vis_text,
            ))

        if a.roadAccessScore is not None and a.roadAccessScore <= 2:
            access_text = a.roadAccessReason or f"Vehicle access scored low ({a.roadAccessScore}/5)"
            candidates.append(RiskFactor(
                factor="access",
                impact=round(float(mc_stats.get("access", 0.19)), 2),
                text=access_text,
            ))

    # 6. Newly opened competitors (market entry pressure)
    new_comps = [c for c in (site.competitors or []) if c.isNew]
    if len(new_comps) > 0:
        new_text = f"{len(new_comps)} new competitor{'s' if len(new_comps) > 1 else ''} opened nearby in the last 6 months"
        candidates.append(RiskFactor(
            factor="new_competitors",
            impact=round(float(mc_stats.get("new_competitors", 0.20)), 2),
            text=new_text,
        ))

    # Sort descending by impact, then deduplicate factor types
    candidates.sort(key=lambda r: r.impact, reverse=True)

    seen_factors: set[str] = set()
    top_risks: list[RiskFactor] = []
    for c in candidates:
        if c.factor not in seen_factors:
            seen_factors.add(c.factor)
            top_risks.append(c)
        if len(top_risks) == 3:
            break

    return top_risks
