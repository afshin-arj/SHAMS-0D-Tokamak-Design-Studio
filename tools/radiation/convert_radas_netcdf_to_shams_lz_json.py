"""Convert RADAS NetCDF output to SHAMS Lz(Te) JSON.

This script is intentionally optional: it is not required to run SHAMS.
It enables the 'authoritative radiation tier' by producing a deterministic,
hashable JSON that SHAMS can load via radiation_db='radas_openadas_v1'.

Usage:
  python tools/radiation/convert_radas_netcdf_to_shams_lz_json.py \
      --input path/to/radas_output.nc \
      --output src/data/radiation/lz_tables_radas_openadas_v1.json \
      --species C NE AR W

Notes:
- Requires xarray + netcdf4 (or h5netcdf) installed in your environment.
- SHAMS records SHA256 of the JSON in artifacts; reviewers can reproduce exactly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="RADAS NetCDF file")
    ap.add_argument("--output", required=True, help="Output JSON path")
    ap.add_argument("--species", nargs="+", default=["C"], help="Species symbols to export")
    args = ap.parse_args()

    try:
        import xarray as xr  # type: ignore
    except Exception as e:
        raise SystemExit(f"xarray is required for this converter: {e}")

    ds = xr.open_dataset(args.input)

    out: Dict[str, object] = {
        "meta": {
            "source": "RADAS/OpenADAS-derived",
            "input": str(Path(args.input).resolve()),
            "notes": "Converted for SHAMS authoritative radiation tier.",
        },
        "species": {},
    }

    # Heuristic: RADAS datasets typically include Te and Lz for each species.
    # We try a few common variable names.
    te_keys = [k for k in ["Te", "Te_eV", "Te_keV", "temperature"] if k in ds.variables]
    if len(te_keys) == 0:
        raise SystemExit("Could not find temperature coordinate in NetCDF (expected one of Te, Te_eV, Te_keV, temperature).")

    te_var = te_keys[0]
    te = ds[te_var].values

    # Convert Te to keV
    if "eV" in te_var.lower():
        te_keV = (te / 1e3).tolist()
    elif "kev" in te_var.lower():
        te_keV = te.tolist()
    else:
        # assume eV if values look like 1..1e5
        te_keV = (te / 1e3).tolist() if float(max(te)) > 100.0 else te.tolist()

    for sp in args.species:
        spu = sp.upper()
        # Candidate names for Lz variable
        cand = [f"Lz_{spu}", f"lz_{spu}", f"Lz_{spu.lower()}", "Lz"]
        lk = next((c for c in cand if c in ds.variables), None)
        if lk is None:
            continue
        lz = ds[lk].values.tolist()
        out["species"][spu] = {"Te_keV": te_keV, "Lz_W_m3": lz}

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
