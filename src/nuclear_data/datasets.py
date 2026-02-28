from __future__ import annotations

"""Nuclear dataset registry (v407).

This registry is designed for *auditability* and *deterministic screening*
proxies. It is intentionally conservative and small.

Hard rules
----------
- No Monte Carlo.
- No spectral iteration.
- No depletion chains.
- Dataset provenance is explicit and SHA-256 pinned.

Important
---------
The default dataset shipped with v407 is a *screening proxy* table. It is
NOT a claim of ENDF/TENDL accuracy. Its purpose is deterministic sensitivity
ranking and provenance pinning.
"""

from dataclasses import dataclass
from typing import Dict, List
import hashlib
import json


def _canonical_json_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class NuclearDataset:
    dataset_id: str
    source_label: str
    source_version: str
    processing_notes: str
    group_structure_id: str

    # Macroscopic removal coefficients per material [1/m], keyed by material name,
    # with a list length = n_groups.
    sigma_removal_1_m: Dict[str, List[float]]

    # Default incident spectrum fractions at FW (length = n_groups, normalized)
    spectrum_frac_fw: List[float]

    # Screening response weights for a bounded TBR proxy (length = n_groups)
    tbr_response_weight: List[float]

    @property
    def sha256(self) -> str:
        payload = {
            "dataset_id": self.dataset_id,
            "source_label": self.source_label,
            "source_version": self.source_version,
            "processing_notes": self.processing_notes,
            "group_structure_id": self.group_structure_id,
            "sigma_removal_1_m": self.sigma_removal_1_m,
            "spectrum_frac_fw": self.spectrum_frac_fw,
            "tbr_response_weight": self.tbr_response_weight,
        }
        return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


# Default v407 dataset: deterministic screening proxy.
# Coefficients are order-of-magnitude placeholders for envelope ranking.
# They are NOT a claim of nuclear data fidelity.
SCREENING_PROXY_V407 = NuclearDataset(
    dataset_id="SCREENING_PROXY_V407",
    source_label="SHAMS_SCREENING_PROXY_NOT_ENDF",
    source_version="v1",
    processing_notes=(
        "Deterministic screening coefficients for multi-group attenuation and response. "
        "Not ENDF/TENDL-derived. Use for sensitivity ranking and provenance pinning only."
    ),
    group_structure_id="G6_V407",
    sigma_removal_1_m={
        # Materials commonly used in v403 default stack.
        "W":     [1.8, 1.6, 1.3, 1.0, 0.7, 0.4],
        "SS316": [1.2, 1.1, 0.9, 0.7, 0.5, 0.3],
        "H2O":   [0.6, 0.7, 0.8, 0.9, 1.1, 1.4],
        "B4C":   [1.0, 1.1, 1.2, 1.3, 1.5, 1.7],
        "LiPb":  [0.8, 0.7, 0.6, 0.5, 0.4, 0.3],
        "FLiBe": [0.7, 0.7, 0.7, 0.7, 0.7, 0.7],
        "Be":    [0.5, 0.55, 0.6, 0.7, 0.8, 0.9],
        "C":     [0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
        "Vacuum": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "Air":   [0.02, 0.02, 0.02, 0.02, 0.02, 0.02],
    },
    spectrum_frac_fw=[0.65, 0.20, 0.08, 0.04, 0.02, 0.01],
    tbr_response_weight=[1.0, 0.9, 0.6, 0.3, 0.15, 0.05],
)


DATASETS: Dict[str, NuclearDataset] = {
    SCREENING_PROXY_V407.dataset_id: SCREENING_PROXY_V407,
}


def get_dataset(dataset_id: str) -> NuclearDataset:
    """Return a dataset by ID.

    v408 extends the registry with external datasets stored under
    ``data/nuclear_datasets``. This function delegates to the dynamic registry
    loader, while keeping the v407 built-in ``DATASETS`` constant available for
    programmatic inspection.
    """

    from .registry import get_dataset as _get  # local import to avoid cycles

    return _get(dataset_id)


# Back-compat alias (some callers may use this naming)
get_nuclear_dataset = get_dataset
