"""Phase 2 gate: run every tool on 5 real Houston sites for the golden query.

Run from backend/:  .venv/bin/python -m scripts.phase2_gate [--vision]
--vision also scores the first site's aerial image: visibility and road access (1 OpenRouter request).
"""
import sys
import time

from app.models import BusinessBrief
from app.tools import census, costar, matterport, osm, vexcel, vision

GOLDEN = BusinessBrief(businessType="boba", city="Houston", maxRentMonthly=6000,
                       sizeSqftMin=800, sizeSqftMax=2000, mustHaves=["parking"])


def attempt(site, gap, fn):
    try:
        return fn()
    except Exception as e:  # one tool failing never kills the run; it becomes a named gap
        site.gaps.append(f"{gap}: {str(e)[:80]}")
        return None


def main():
    cands = costar.find_candidates(GOLDEN)
    print(f"{len(cands)} candidates for the golden query")
    picked, props = [], set()
    for s in cands:  # 5 priced sites on different properties
        if s.rentMonthly and s.propertyId not in props:
            picked.append(s)
            props.add(s.propertyId)
        if len(picked) == 5:
            break

    for i, s in enumerate(picked):
        t = time.time()
        workers = costar.workers_nearby(s.lat, s.lon, 1.0)
        s.demographics = attempt(s, "no demographics", lambda: census.demographics(s.lat, s.lon))
        s.competitors = attempt(s, "no competitors", lambda: osm.competitors(s.lat, s.lon, GOLDEN.businessType)) or []
        s.aerial = attempt(s, "no aerial", lambda: vexcel.aerial(s.id, s.lat, s.lon))
        if s.matterportModelId:
            s.interior = attempt(s, "no 3D data", lambda: matterport.interior(s.matterportModelId, s.sizeSqft))
            if s.interior and matterport.is_building_scan(s.interior.floorAreaSqft, s.sizeSqft):
                s.gaps.append("3D scan is of the whole building")
        if "--vision" in sys.argv and i == 0 and s.aerial:
            v = attempt(s, "no vision", lambda: vision.score_aerial(vexcel.ortho_jpeg(s.aerial.parcelWkt)))
            if v:
                s.aerial = s.aerial.model_copy(update=v)

        comp = sum(c.kind == "competitor" for c in s.competitors)
        print(f"\n{s.address}  ({s.id}, {time.time() - t:.1f}s)")
        print(f"  rent ${s.rentMonthly:,.0f}/mo ({s.serviceType}), {s.sizeSqft:,.0f} sq ft")
        print(f"  people: {workers:,} workers within 1 mi")
        if d := s.demographics:
            print(f"  census: tract pop {d.population:,}, {d.densityPerSqMi:,.0f}/sq mi, income ${d.medianIncome or 0:,.0f}; "
                  f"{d.driveShare:.0%} drive to work, {d.walkTransitShare:.0%} walk/transit, {d.noVehicleShare:.0%} no car")
        print(f"  competitors: {comp} within 1 mi ({len(s.competitors)} places incl. complements)"
              + (f", nearest {s.competitors[0].name} {s.competitors[0].distanceMi} mi" if s.competitors else ""))
        if s.aerial:
            print(f"  aerial: parcel + image ({s.aerial.collection})")
            if s.aerial.visibilityScore:
                print(f"  vision: visibility {s.aerial.visibilityScore}/5 ({s.aerial.visibilityReason}); "
                      f"access {s.aerial.roadAccessScore}/5 ({s.aerial.roadAccessReason})")
        if s.interior:
            print(f"  interior: {s.interior.floorAreaSqft:,.0f} sq ft scanned, ~{s.interior.estSeats} seats, "
                  f"{len(s.interior.rooms)} measured rooms")
        print(f"  gaps: {s.gaps or 'none'}")


if __name__ == "__main__":
    main()
