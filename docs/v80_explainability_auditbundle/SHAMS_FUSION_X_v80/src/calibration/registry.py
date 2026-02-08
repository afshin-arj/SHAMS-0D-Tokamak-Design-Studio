from __future__ import annotations

"""Calibration registry.

A calibration is a *transparent multiplicative factor* applied to a named proxy,
with explicit provenance, validity ranges, and uncertainty.

This is inspired by PROCESS practice (aligning simplified models to reference data),
but implemented as a SHAMS-native, artifact-recorded registry.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Tuple
import time
import json
from pathlib import Path


@dataclass(frozen=True)
class CalibrationFactor:
    key: str                       # e.g. 'confinement'
    factor: float = 1.0            # multiplicative
    sigma: float = 0.0             # 1-sigma relative uncertainty (fraction)
    source: str = ""               # citation / dataset / run id
    created_unix: float = 0.0
    valid_ranges: Dict[str, Tuple[float, float]] = None  # e.g. {'R0_m': (2, 8)}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["valid_ranges"] = dict(self.valid_ranges or {})
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CalibrationFactor":
        vr = {}
        for k, v in (d.get("valid_ranges") or {}).items():
            try:
                vr[str(k)] = (float(v[0]), float(v[1]))
            except Exception:
                pass
        return CalibrationFactor(
            key=str(d.get("key", "")),
            factor=float(d.get("factor", 1.0)),
            sigma=float(d.get("sigma", 0.0)),
            source=str(d.get("source", "")),
            created_unix=float(d.get("created_unix", 0.0)),
            valid_ranges=vr,
        )


@dataclass
class CalibrationRegistry:
    name: str = "default"
    created_unix: float = 0.0
    factors: Dict[str, CalibrationFactor] = None  # key -> factor

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_unix": float(self.created_unix),
            "factors": {k: v.to_dict() for k, v in (self.factors or {}).items()},
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CalibrationRegistry":
        facs = {}
        for k, v in (d.get("factors") or {}).items():
            facs[str(k)] = CalibrationFactor.from_dict(v)
        return CalibrationRegistry(
            name=str(d.get("name", "default")),
            created_unix=float(d.get("created_unix", 0.0)),
            factors=facs,
        )

    def select_factors(self, inputs_dict: Dict[str, Any]) -> Dict[str, float]:
        """Return key->factor for factors that are within validity ranges (if specified)."""
        out: Dict[str, float] = {}
        for k, f in (self.factors or {}).items():
            ok = True
            for var, (lo, hi) in (f.valid_ranges or {}).items():
                try:
                    x = float(inputs_dict.get(var))
                    if x < float(lo) or x > float(hi):
                        ok = False
                        break
                except Exception:
                    # if variable not present, be conservative and still allow
                    continue
            if ok:
                out[k] = float(f.factor)
        return out


def load_registry(path: str | Path) -> CalibrationRegistry:
    p = Path(path)
    d = json.loads(p.read_text(encoding="utf-8"))
    reg = CalibrationRegistry.from_dict(d)
    return reg


def save_registry(path: str | Path, reg: CalibrationRegistry) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def default_registry() -> CalibrationRegistry:
    return CalibrationRegistry(
        name="default",
        created_unix=time.time(),
        factors={
            "confinement": CalibrationFactor(key="confinement", factor=1.0, sigma=0.05, source="default", created_unix=time.time()),
            "divertor": CalibrationFactor(key="divertor", factor=1.0, sigma=0.10, source="default", created_unix=time.time()),
            "bootstrap": CalibrationFactor(key="bootstrap", factor=1.0, sigma=0.05, source="default", created_unix=time.time()),
        },
    )
