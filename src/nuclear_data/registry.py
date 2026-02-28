from __future__ import annotations

"""Nuclear dataset registry (v408).

v407 introduced a small built-in dataset registry for deterministic screening.
v408 extends this with *external dataset intake* while preserving the frozen-truth
discipline:

- No transport solvers.
- No spectral iteration.
- Datasets are explicit, validated, and SHA-256 pinned.
- External datasets are loaded from a repo-local data directory so they can be
  packaged into evidence/reviewer packs.

External datasets are stored as JSON under:

    data/nuclear_datasets/<dataset_id>.json

The JSON format matches :class:`~src.nuclear_data.datasets.NuclearDataset`.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional
import json

from .datasets import NuclearDataset, DATASETS as BUILTIN_DATASETS


def _repo_root() -> Path:
    # This file is at src/nuclear_data/registry.py
    return Path(__file__).resolve().parents[2]


def external_dataset_dir(repo_root: Optional[Path] = None) -> Path:
    root = repo_root or _repo_root()
    return root / "data" / "nuclear_datasets"


def _load_dataset_json(path: Path) -> NuclearDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Strict key presence; unknown keys are rejected by construction.
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
        raise ValueError(f"Dataset JSON missing keys: {missing} (file: {path.name})")
    if extra:
        raise ValueError(f"Dataset JSON has unknown keys: {extra} (file: {path.name})")
    return NuclearDataset(
        dataset_id=str(payload["dataset_id"]),
        source_label=str(payload["source_label"]),
        source_version=str(payload["source_version"]),
        processing_notes=str(payload["processing_notes"]),
        group_structure_id=str(payload["group_structure_id"]),
        sigma_removal_1_m=dict(payload["sigma_removal_1_m"]),
        spectrum_frac_fw=list(payload["spectrum_frac_fw"]),
        tbr_response_weight=list(payload["tbr_response_weight"]),
    )


def load_external_datasets(repo_root: Optional[Path] = None) -> Dict[str, NuclearDataset]:
    ddir = external_dataset_dir(repo_root)
    if not ddir.exists():
        return {}

    out: Dict[str, NuclearDataset] = {}
    for p in sorted(ddir.glob("*.json")):
        ds = _load_dataset_json(p)
        if ds.dataset_id in out:
            raise ValueError(f"Duplicate external dataset_id '{ds.dataset_id}' in {ddir}")
        out[ds.dataset_id] = ds
    return out


def get_all_datasets(repo_root: Optional[Path] = None) -> Dict[str, NuclearDataset]:
    all_ds: Dict[str, NuclearDataset] = dict(BUILTIN_DATASETS)
    ext = load_external_datasets(repo_root)
    # External may override built-in only if the ID differs; disallow shadowing.
    overlap = sorted(set(all_ds.keys()) & set(ext.keys()))
    if overlap:
        raise ValueError(
            "External datasets must not shadow built-in IDs. Overlap: " + ", ".join(overlap)
        )
    all_ds.update(ext)
    return all_ds


def list_dataset_ids(repo_root: Optional[Path] = None) -> List[str]:
    return sorted(get_all_datasets(repo_root).keys())


def get_dataset(dataset_id: str, repo_root: Optional[Path] = None) -> NuclearDataset:
    all_ds = get_all_datasets(repo_root)
    if dataset_id in all_ds:
        return all_ds[dataset_id]
    raise KeyError(f"Unknown nuclear dataset_id: {dataset_id}")


def save_external_dataset(dataset: NuclearDataset, repo_root: Optional[Path] = None) -> Path:
    """Persist a dataset JSON under data/nuclear_datasets.

    This is a build-time / user-intake utility (v408). It does not mutate truth.
    """
    ddir = external_dataset_dir(repo_root)
    ddir.mkdir(parents=True, exist_ok=True)
    path = ddir / f"{dataset.dataset_id}.json"

    # Stable JSON on disk.
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
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_dataset_evidence_card_md(dataset: NuclearDataset) -> str:
    """Human-readable provenance card for reviewer packs (deterministic)."""
    lines = []
    lines.append(f"# Nuclear Dataset Evidence Card — {dataset.dataset_id}")
    lines.append("")
    lines.append("## Provenance")
    lines.append(f"- **dataset_id:** {dataset.dataset_id}")
    lines.append(f"- **sha256 (canonical payload):** `{dataset.sha256}`")
    lines.append(f"- **source_label:** {dataset.source_label}")
    lines.append(f"- **source_version:** {dataset.source_version}")
    lines.append(f"- **group_structure_id:** {dataset.group_structure_id}")
    lines.append("")
    lines.append("## Processing Notes")
    lines.append(dataset.processing_notes)
    lines.append("")
    lines.append("## Contents")
    lines.append(f"- Materials in sigma_removal_1_m: {len(dataset.sigma_removal_1_m)}")
    lines.append(f"- Spectrum fractions length: {len(dataset.spectrum_frac_fw)}")
    lines.append(f"- TBR response weight length: {len(dataset.tbr_response_weight)}")
    lines.append("")
    lines.append("## Determinism Contract")
    lines.append(
        "This dataset is used only in deterministic algebraic screening proxies. "
        "No transport solver, no Monte Carlo, and no spectral iteration are executed in SHAMS truth."
    )
    lines.append("")
    return "\n".join(lines)
