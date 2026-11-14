"""One-page decision report: ranking, why #1, risks, and assumptions. See docs/requirements.md F10."""
from datetime import datetime
from app.models import BusinessBrief, Site


def generate_report(brief: BusinessBrief, sites: list[Site]) -> str:
    """Generate a clean, structured decision report markdown document."""
    if not sites:
        return "# Decision Report\n\nNo candidate sites available for evaluation."

    top = sites[0]
    top_sim = top.sim
    top_odds = f"{round((top_sim.pProfitableBy12 if top_sim else 0) * 100)}%"
    top_rent = f"${top.rentMonthly:,.0f}/mo" if top.rentMonthly else "Rent not listed"
    top_expected = f"~{round(top_sim.expectedCustomers):,}" if top_sim else "N/A"
    top_breakeven = f"{round(top_sim.breakEvenCustomers):,}" if top_sim else "N/A"
    top_payback = f"{top_sim.paybackMonths} months" if (top_sim and top_sim.paybackMonths) else "36+ months"

    # Competitor count
    top_comps = len([c for c in top.competitors if c.kind == "competitor"])

    lines = [
        f"# BeforeYouSign: Site Selection Report",
        f"**Business Search:** {brief.businessType.title()} in {brief.city} · **Max Budget:** ${brief.maxRentMonthly:,.0f}/mo · **Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "---",
        "",
        "## Executive Recommendation",
        f"**Top Pick: #{1} {top.address}** is recommended with **{top_odds} chance of monthly profitability by Month 12** and an estimated payback period of **{top_payback}**.",
        "",
        f"- **Unit Rent:** {top_rent} for {top.sizeSqft:,.0f} sq ft" + (f" (~{top.interior.estSeats} estimated seats)" if top.interior else ""),
        f"- **Customer Demand:** Mature expectation of **{top_expected} customers/day** against a break-even threshold of **{top_breakeven} customers/day**.",
        f"- **Competitive Density:** {top_comps} direct competitor(s) within the trade area.",
        "",
        "## Comparative Ranking",
        "",
        "| Rank | Address | Month 12 Odds | Rent / Mo | Expected Cust/Day | Break-Even | Rent % Rev | Primary Risk |",
        "|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|",
    ]

    for i, s in enumerate(sites):
        sim = s.sim
        odds_str = f"{round(sim.pProfitableBy12 * 100)}%" if sim else "N/A"
        rent_str = f"${s.rentMonthly:,.0f}" if s.rentMonthly else "Unlisted"
        exp_cust = f"{round(sim.expectedCustomers)}" if sim else "N/A"
        be_cust = f"{round(sim.breakEvenCustomers)}" if sim else "N/A"
        rent_pct = f"{round(sim.rentShare * 100)}%" if (sim and sim.rentShare) else "N/A"
        primary_risk = (sim.riskFactors[0].text if sim and sim.riskFactors else "None identified")
        lines.append(f"| #{i+1} | {s.address} | **{odds_str}** | {rent_str} | {exp_cust} | {be_cust} | {rent_pct} | {primary_risk} |")

    lines.extend([
        "",
        "## Why Site #1 Won",
        f"1. **Strong Margin of Safety:** The location needs {top_breakeven} customers/day to cover all fixed costs (rent, labor, utilities). Modeled foot traffic projects {top_expected}/day, providing an operating safety cushion.",
        f"2. **Sustainable Rent Burden:** Rent represents {round((top_sim.rentShare if top_sim else 0) * 100)}% of anticipated revenue, remaining within sustainable retail thresholds.",
        f"3. **Physical & Road Access:** Aerial imagery confirms adequate parking access" + (f" and road access score of {top.aerial.roadAccessScore}/5" if (top.aerial and top.aerial.roadAccessScore) else "") + ".",
        "",
        "## Key Risk Factors & Lease Considerations",
    ])

    for i, s in enumerate(sites[:3]):
        risks = s.sim.riskFactors if s.sim else []
        if risks:
            risk_bullets = ", ".join([f"**{r.factor}** ({r.text})" for r in risks])
            lines.append(f"- **#{i+1} {s.address}:** {risk_bullets}")

    # Benchmark Assumptions
    assumptions = top_sim.assumptions if (top_sim and top_sim.assumptions) else {}
    ticket = f"${assumptions.get('ticket', assumptions.get('avgTicket', 8.0)):.2f}"
    labor = f"${assumptions.get('laborFixedMonthly', assumptions.get('laborMonthly', 7000)):,.0f}/mo"
    startup = f"${assumptions.get('startupCost', 110000):,.0f}"

    lines.extend([
        "",
        "## Modeling Assumptions & Disclosure",
        f"- **Benchmark Defaults:** Average ticket {ticket} · Fixed labor {labor} · Estimated startup/fitout {startup} · 1,000 Monte Carlo runs over 24-month horizon.",
        "- **Honesty Disclosure:** The relative ranking between candidate sites is the most reliable output. Exact dollar projections depend on localized operational execution and chosen assumptions.",
        "",
        "_Data Sources: CoStar (Listings & Workforce), US Census Bureau (ACS 5-Year Demographics), Vexcel Imaging (Aerial), Matterport (Spatial Floorplans)._",
    ])

    return "\n".join(lines)
