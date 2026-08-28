"""
Run the offline Chakaria analysis pipeline end-to-end.

By default uses demo data (no GEE auth required). Pass --gee to extract
real Global Pasture Watch uGPP first.

Usage (from chakaria_mangrove_productivity/):
  python run_pipeline.py
  python run_pipeline.py --gee --project YOUR_GCP_PROJECT
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    print("\n>>>", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chakaria uGPP analysis pipeline")
    parser.add_argument(
        "--gee",
        action="store_true",
        help="Extract real uGPP from Earth Engine instead of demo data",
    )
    parser.add_argument("--project", default=None, help="GCP EE project id")
    args = parser.parse_args()

    py = sys.executable

    # Ensure a study-area GeoJSON exists (provisional unless user copied theirs)
    boundary = ROOT / "data" / "chakaria_boundary.geojson"
    if not boundary.exists():
        run([py, "scripts/make_provisional_boundary.py"])

    if args.gee:
        cmd = [py, "scripts/01_extract_gee.py", "--boundary", str(boundary)]
        if args.project:
            cmd += ["--project", args.project]
        run(cmd)
    else:
        run([py, "scripts/make_demo_data.py"])

    run([py, "scripts/02_temporal_metrics.py"])
    run([py, "scripts/03_statistics.py"])
    run([py, "scripts/04_figures.py"])
    print("\nPipeline complete. See outputs/tables and outputs/figures.")


if __name__ == "__main__":
    main()
