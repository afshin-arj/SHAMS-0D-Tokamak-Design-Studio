from __future__ import annotations

"""External nuclear dataset intake utilities (v408).

Purpose
-------
Provide a deterministic, audit-friendly pathway to import multi-group screening
datasets into the SHAMS registry.

Hard constraints
----------------
- Intake is *not* part of plasma truth evaluation.
- No MC/transport solvers are introduced.
- Strict schema validation.
- Canonical payload SHA-256 pinning.

Supported inputs
----------------
1) Single JSON file matching the NuclearDataset schema.
2) Metadata JSON + sigma_removal CSV table (materials x groups).

The canonical persisted artifact is always the JSON schema.
"""

from dataclasses import dataclass
from io import StringIO
from typing import Dict, List, Tuple
import csv
import json

from .datasets import NuclearDataset
from .group_structures import get_group_structure


@dataclass(frozen=True)
class DatasetMetadata:
    dataset_id: str
    source_label: str
    source_version: str
    processing_notes: str
    group_structure_id: str


def _require_nonempty_str(x: object, field: str) -> str:
    s = str(x).strip()
    if not s:
        raise ValueError(f"'{field}' must be a non-empty string")
    return s


def parse_metadata_json(text: str) -> DatasetMetadata:
    payload = json.loads(text)
    required = {"dataset_id", "source_label", "source_version", "processing_notes", "group_structure_id"}
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise ValueError(f"Metadata JSON missing keys: {missing}")
    return DatasetMetadata(
        dataset_id=_require_nonempty_str(payload["dataset_id"], "dataset_id"),
        source_label=_require_nonempty_str(payload["source_label"], "source_label"),
        source_version=_require_nonempty_str(payload["source_version"], "source_version"),
        processing_notes=_require_nonempty_str(payload["processing_notes"], "processing_notes"),
        group_structure_id=_require_nonempty_str(payload["group_structure_id"], "group_structure_id"),
    )


def parse_sigma_removal_csv(text: str, n_groups: int) -> Dict[str, List[float]]:
    """Parse a materials x groups CSV.

Expected columns:
    material,g1,g2,...,gN

Numbers are interpreted as 1/m.
"""
    reader = csv.reader(StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("sigma_removal CSV is empty")

    header = [h.strip() for h in rows[0]]
    if len(header) != (1 + n_groups):
        raise ValueError(
            f"sigma_removal CSV header must have {1+n_groups} columns (material + {n_groups} groups). Got {len(header)}"
        )
    if header[0].lower() not in {"material", "mat"}:
        raise ValueError("sigma_removal CSV first column must be 'material'")

    out: Dict[str, List[float]] = {}
    for i, r in enumerate(rows[1:], start=2):
        if not r or all((c.strip() == "" for c in r)):
            continue
        if len(r) != (1 + n_groups):
            raise ValueError(f"Row {i}: expected {1+n_groups} columns, got {len(r)}")
        mat = _require_nonempty_str(r[0], f"row {i} material")
        vals: List[float] = []
        for j in range(n_groups):
            try:
                vals.append(float(r[1 + j]))
            except Exception as e:
                raise ValueError(f"Row {i}, group {j+1}: could not parse float: {r[1+j]!r}") from e
        out[mat] = vals
    if not out:
        raise ValueError("sigma_removal CSV contained no data rows")
    return out


def validate_vector(name: str, v: List[float], n_groups: int, must_sum_to_one: bool = False) -> None:
    if len(v) != n_groups:
        raise ValueError(f"{name} must have length {n_groups}; got {len(v)}")
    if any((not (x == x) for x in v)):
        raise ValueError(f"{name} contains NaN")
    if any((x < 0.0 for x in v)):
        raise ValueError(f"{name} contains negative values")
    if must_sum_to_one:
        s = sum(v)
        if s <= 0:
            raise ValueError(f"{name} sum must be > 0")
        # Normalize tolerance, do not silently renormalize.
        if abs(s - 1.0) > 1e-6:
            raise ValueError(f"{name} must sum to 1.0 within 1e-6; got {s}")


def dataset_from_json(text: str) -> NuclearDataset:
    payload = json.loads(text)
    required = {
        "dataset_id",
        "source_label",
        "source_version",
        "processing_notes",
        "group_structure_id",
        "sigma_removal_1_m",
        "spectrum_frac_fw",
        "tbr_response_weight",
    }
    missing = sorted(required - set(payload.keys()))
    extra = sorted(set(payload.keys()) - required)
    if missing:
        raise ValueError(f"Dataset JSON missing keys: {missing}")
    if extra:
        raise ValueError(f"Dataset JSON has unknown keys: {extra}")

    gs = get_group_structure(str(payload["group_structure_id"]))
    n = gs.n_groups

    spectrum = list(payload["spectrum_frac_fw"])
    tbrw = list(payload["tbr_response_weight"])
    validate_vector("spectrum_frac_fw", spectrum, n_groups=n, must_sum_to_one=True)
    validate_vector("tbr_response_weight", tbrw, n_groups=n, must_sum_to_one=False)

    sigma = dict(payload["sigma_removal_1_m"])
    if not sigma:
        raise ValueError("sigma_removal_1_m must contain at least one material")
    for k, v in sigma.items():
        vv = list(v)
        validate_vector(f"sigma_removal_1_m[{k}]", vv, n_groups=n, must_sum_to_one=False)
        sigma[str(k)] = vv

    ds = NuclearDataset(
        dataset_id=_require_nonempty_str(payload["dataset_id"], "dataset_id"),
        source_label=_require_nonempty_str(payload["source_label"], "source_label"),
        source_version=_require_nonempty_str(payload["source_version"], "source_version"),
        processing_notes=_require_nonempty_str(payload["processing_notes"], "processing_notes"),
        group_structure_id=gs.group_structure_id,
        sigma_removal_1_m=sigma,
        spectrum_frac_fw=spectrum,
        tbr_response_weight=tbrw,
    )
    return ds


def dataset_from_metadata_and_csv(
    metadata_json_text: str,
    sigma_removal_csv_text: str,
    spectrum_frac_fw: List[float],
    tbr_response_weight: List[float],
) -> NuclearDataset:
    md = parse_metadata_json(metadata_json_text)
    gs = get_group_structure(md.group_structure_id)
    n = gs.n_groups

    validate_vector("spectrum_frac_fw", spectrum_frac_fw, n_groups=n, must_sum_to_one=True)
    validate_vector("tbr_response_weight", tbr_response_weight, n_groups=n, must_sum_to_one=False)

    sigma = parse_sigma_removal_csv(sigma_removal_csv_text, n_groups=n)
    return NuclearDataset(
        dataset_id=md.dataset_id,
        source_label=md.source_label,
        source_version=md.source_version,
        processing_notes=md.processing_notes,
        group_structure_id=md.group_structure_id,
        sigma_removal_1_m=sigma,
        spectrum_frac_fw=list(spectrum_frac_fw),
        tbr_response_weight=list(tbr_response_weight),
    )


def canonical_dataset_json(dataset: NuclearDataset) -> str:
    payload = {
        "dataset_id": dataset.dataset_id,
        "source_label": dataset.source_label,
        "source_version": dataset.source_version,
        "processing_notes": dataset.processing_notes,
        "group_structure_id": dataset.group_structure_id,
        "sigma_removal_1_m": dataset.sigma_removal_1_m,
        "spectrum_frac_fw": dataset.spectrum_frac_fw,
        "tbr_response_weight": dataset.tbr_response_weight,
    }
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
