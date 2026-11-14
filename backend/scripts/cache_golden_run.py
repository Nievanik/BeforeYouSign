"""Cache all external API responses for the golden run.

Run from backend/:
    python -m scripts.cache_golden_run

Once cached, every tool and the full application runs 100% offline with OFFLINE=1.
"""
import json
from pathlib import Path
import time

from app.models import Site
from app.tools import census, matterport, osm, vexcel

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"


def main():
    golden_path = FIXTURES / "golden_run.json"
    if not golden_path.exists():
        print(f"Error: {golden_path} not found")
        return

    data = json.loads(golden_path.read_text())
    sites = [Site(**s) for s in data.get("sites", [])]

    print(f"Caching external responses for {len(sites)} golden run sites...\n")

    for i, s in enumerate(sites, start=1):
        print(f"[{i}/{len(sites)}] Processing: {s.address} ({s.id})")
        t0 = time.time()

        # 1. Census Demographics
        try:
            demo = census.demographics(s.lat, s.lon)
            print(f"  ✓ Census: tract {demo.tract}, pop {demo.population:,}")
        except Exception as e:
            print(f"  ✕ Census error: {e}")

        # 2. OpenStreetMap Competitors
        try:
            comps = osm.competitors(s.lat, s.lon, "boba")
            print(f"  ✓ OSM: {len(comps)} competitors & complements found")
        except Exception as e:
            print(f"  ✕ OSM error: {e}")

        # 3. Vexcel Aerial Imagery (parcel, ortho, oblique photos, parking)
        try:
            p = vexcel.parcel(s.lat, s.lon)
            wkt = p["wkt"]
            print(f"  ✓ Vexcel parcel: {wkt[:40]}...")

            # Parking detection
            rows = vexcel.detect_parking(wkt)
            print(f"  ✓ Vexcel parking rows: {len(rows)} detected")

            # Ortho image
            ortho = vexcel.ortho_jpeg(wkt, rows)
            print(f"  ✓ Vexcel ortho jpeg: {len(ortho):,} bytes")

            # Oblique photos
            dirs = vexcel.oblique_directions(wkt)
            print(f"  ✓ Vexcel oblique dirs: {dirs}")
            for d in dirs:
                ob = vexcel.oblique_jpeg(wkt, d)
                print(f"    - {d}: {len(ob):,} bytes")
        except Exception as e:
            print(f"  ✕ Vexcel error: {e}")

        # 4. Matterport 3D Interior
        if s.matterportModelId:
            try:
                interior = matterport.interior(s.matterportModelId, s.sizeSqft)
                print(f"  ✓ Matterport {s.matterportModelId}: {interior.floorAreaSqft:,.0f} sqft, ~{interior.estSeats} seats")
            except Exception as e:
                print(f"  ✕ Matterport error: {e}")

        print(f"  Done in {time.time() - t0:.1f}s\n")

    # Summary
    if CACHE_DIR.exists():
        cached_files = list(CACHE_DIR.rglob("*.json"))
        total_kb = sum(f.stat().st_size for f in cached_files) / 1024.0
        print("========================================")
        print(f"Success! {len(cached_files)} files cached ({total_kb:,.1f} KB total)")
        print(f"Cache location: {CACHE_DIR}")
        print("You can now run completely offline with OFFLINE=1")
        print("========================================")


if __name__ == "__main__":
    main()
