"""Auto mode: when the agent goes over budget or the model fails, finish the run with the same tools in a fixed order."""
import time


def finish(run) -> None:
    """Find sites if needed, simulate each one not yet simulated, rank by odds, write a templated report."""
    run.calls, run.started = 0, time.monotonic()  # fresh budget: at most 1 search + SHORTLIST sims
    tools = {t.__name__: t for t in run.tools()}
    if not run.sites:
        tools["find_candidates"]()
    for s in list(run.sites.values()):
        if not s.sim:
            tools["simulate"](s.id)
    done = sorted((s for s in run.sites.values() if s.sim), key=lambda s: s.sim.pProfitableBy12, reverse=True)
    run.ranking = [s.id for s in done]
    if not done:
        run.report = "Auto mode found no sites it could simulate. Try a higher rent limit or a wider size range."
        return
    lines = [f"{i}. **{s.address}**: {s.sim.pProfitableBy12:.0%} chance of profit by month 12, "
             f"~{s.sim.expectedCustomers:.0f} customers/day vs {s.sim.breakEvenCustomers:.0f} needed, "
             f"${s.rentMonthly:,.0f}/mo" + (f". Gaps: {', '.join(s.gaps)}" if s.gaps else "")
             for i, s in enumerate(done, 1)]
    run.report = ("## Ranking (auto mode)\n\nThe agent stopped early, so sites are ranked by simulated odds only.\n\n"
                  + "\n".join(lines) + "\n\nCompare sites with these numbers; don't bank on the dollars.")
