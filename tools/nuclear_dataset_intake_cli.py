from __future__ import annotations

"""Nuclear dataset intake CLI (v408).

This CLI imports an external dataset into the repo-local registry directory:

    data/nuclear_datasets/<dataset_id>.json
    data/nuclear_datasets/<dataset_id>.md

It is intentionally simple and deterministic.

Examples
--------
1) Import a dataset JSON:

    python tools/nuclear_dataset_intake_cli.py --json path/to/dataset.json

2) Import from metadata JSON + sigma-removal CSV:

    python tools/nuclear_dataset_intake_cli.py \
        --metadata path/to/meta.json \
        --sigma-csv path/to/sigma.csv \
        --spectrum 0.65,0.2,0.08,0.04,0.02,0.01 \
        --tbrw 1,0.9,0.6,0.3,0.15,0.05
"""

import argparse
from pathlib import Path

from src.nuclear_data.intake import (
    dataset_from_json,
    dataset_from_metadata_and_csv,
    canonical_dataset_json,
)
from src.nuclear_data.registry import save_external_dataset, build_dataset_evidence_card_md, external_dataset_dir


def _parse_vec(s: str) -> list[float]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return [float(p) for p in parts]


def main() -> int:
    ap = argparse.ArgumentParser(description="SHAMS v408 nuclear dataset intake")
    ap.add_argument("--json", type=str, default="", help="Dataset JSON file (full schema)")
    ap.add_argument("--metadata", type=str, default="", help="Metadata JSON file")
    ap.add_argument("--sigma-csv", type=str, default="", help="Sigma removal CSV file")
    ap.add_argument("--spectrum", type=str, default="", help="Spectrum fractions (comma-separated)")
    ap.add_argument("--tbrw", type=str, default="", help="TBR response weights (comma-separated)")
    args = ap.parse_args()

    if args.json:
        ds = dataset_from_json(Path(args.json).read_text(encoding="utf-8"))
    else:
        if not (args.metadata and args.sigma_csv and args.spectrum and args.tbrw):
            ap.error("Provide either --json OR (--metadata --sigma-csv --spectrum --tbrw)")
        ds = dataset_from_metadata_and_csv(
            metadata_json_text=Path(args.metadata).read_text(encoding="utf-8"),
            sigma_removal_csv_text=Path(args.sigma_csv).read_text(encoding="utf-8"),
            spectrum_frac_fw=_parse_vec(args.spectrum),
            tbr_response_weight=_parse_vec(args.tbrw),
        )

    # Save JSON
    p = save_external_dataset(ds)
    # Save evidence card
    md = build_dataset_evidence_card_md(ds)
    (p.parent / f"{ds.dataset_id}.md").write_text(md, encoding="utf-8")

    print(f"Saved dataset: {ds.dataset_id}")
    print(f"Registry dir: {external_dataset_dir().as_posix()}")
    print(f"JSON: {p.as_posix()}")
    print(f"Evidence card: {(p.parent / f'{ds.dataset_id}.md').as_posix()}")
    print(f"sha256: {ds.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
