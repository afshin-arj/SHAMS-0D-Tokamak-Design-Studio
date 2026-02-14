from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
import math
import time

try:
    from ..models.inputs import PointInputs  # type: ignore
except Exception:
    try:
        from models.inputs import PointInputs  # type: ignore
    except Exception:
        from models.inputs import PointInputs  # type: ignore
try:
    # Preferred when imported as `src.*`
    from ..physics.hot_ion import hot_ion_point  # type: ignore
    from ..calibration.calibration import apply_calibration  # type: ignore
    from ..provenance.model_cards import model_cards_index  # type: ignore
except Exception:
    # Back-compat for entrypoints that add `<repo>/src` to sys.path
    from physics.hot_ion import hot_ion_point  # type: ignore
    from calibration.calibration import apply_calibration  # type: ignore
    from provenance.model_cards import model_cards_index  # type: ignore
from .derivatives import get_derivative
from .cache_key import sha256_cache_key


@dataclass
class EvalResult:
    """Result from evaluating the SHAMS physics/model stack."""

    inp: PointInputs
    out: Dict[str, float]
    elapsed_s: float
    ok: bool = True
    message: str = ""


class Evaluator:
    """PROCESS-inspired evaluator interface.

    This wraps `physics.hot_ion.hot_ion_point` and applies transparent calibration.
    It also includes a small deterministic memoization cache used by Systems Mode
    (precheck/scout/atlas) and other iterative routines.

    Cache is an acceleration feature only; it must not change numerical results.
    """

    def __init__(self, *, label: str = "hot_ion_point", cache_enabled: bool = True, cache_max: int = 256):
        self.label = str(label)
        self._cache_enabled = bool(cache_enabled)
        self._cache_max = int(cache_max)

        # Memoization cache keyed by sha256(canonical_json(PointInputs))
        # (stable across Python processes and hash seeds)
        self._cache: dict[str, EvalResult] = {}
        self._cache_order: list[str] = []

        # Simple stats for debugging/telemetry
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0

    def cache_stats(self) -> Dict[str, Any]:
        return {
            "enabled": bool(getattr(self, "_cache_enabled", True)),
            "max": int(getattr(self, "_cache_max", 0) or 0),
            "size": int(len(getattr(self, "_cache", {}) or {})),
            "hits": int(getattr(self, "_cache_hits", 0) or 0),
            "misses": int(getattr(self, "_cache_misses", 0) or 0),
            "evictions": int(getattr(self, "_cache_evictions", 0) or 0),
        }

    def reset_cache_stats(self) -> None:
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0


    
    def evaluate(self, inp: PointInputs) -> EvalResult:
            """
            Evaluate the reactor point model with transparent calibration + provenance.

            This method is intentionally 'boring':
            - inputs are hashed for caching
            - physics proxy lives in physics.hot_ion.hot_ion_point
            - calibration factors are explicit (defaults = 1.0)
            - model cards are attached for auditability
            """
            t0 = time.perf_counter()

            # Deterministic cache key (canonical JSON -> SHA-256) for caching
            cache_key = sha256_cache_key(inp)
            cache = getattr(self, "_cache", {})
            if bool(getattr(self, "_cache_enabled", True)) and cache_key in cache:
                self._cache_hits = int(getattr(self, "_cache_hits", 0) or 0) + 1
                return cache[cache_key]
            self._cache_misses = int(getattr(self, "_cache_misses", 0) or 0) + 1

            ok = True
            msg = ""
            out: Dict[str, Any] = {}
            try:
                out = hot_ion_point(inp)

                # Transparent reference calibration registry (defaults are 1.0 => unchanged behavior)
                calib = {
                    "name": str(getattr(inp, "calibration_registry_name", "inline")),
                    "created_unix": float(getattr(inp, "calibration_registry_created_unix", 0.0) or 0.0),
                    "factors": {
                        "confinement": {
                            "key": "confinement",
                            "factor": float(getattr(inp, "calib_confinement", 1.0)),
                            "sigma": float(getattr(inp, "calib_confinement_sigma", 0.0)),
                            "source": str(getattr(inp, "calib_confinement_source", "inline")),
                            "created_unix": float(getattr(inp, "calib_confinement_created_unix", 0.0) or 0.0),
                            "valid_ranges": {},
                        },
                        "bootstrap": {
                            "key": "bootstrap",
                            "factor": float(getattr(inp, "calib_bootstrap", 1.0)),
                            "sigma": float(getattr(inp, "calib_bootstrap_sigma", 0.0)),
                            "source": str(getattr(inp, "calib_bootstrap_source", "inline")),
                            "created_unix": float(getattr(inp, "calib_bootstrap_created_unix", 0.0) or 0.0),
                            "valid_ranges": {},
                        },
                    },
                }

                # Provide inputs for downstream validity-range selection (if used)
                out["_inputs"] = dict(getattr(inp, "__dict__", {}))

                # Apply transparent calibration factors (defaults are 1.0)
                out = apply_calibration(out, calib)

                # Model cards (auditability / provenance) + validity checks
                try:
                    mc_index = model_cards_index()
                except Exception:
                    mc_index = {}
                out["model_cards"] = mc_index

                try:
                    from provenance.model_cards import check_model_card_validity
                    out["model_cards_validity"] = check_model_card_validity(
                        mc_index, out.get("_inputs", {}), out
                    )
                except Exception:
                    out["model_cards_validity"] = {}

            except Exception as e:
                out = {}
                ok = False
                msg = f"exception: {e}"

            elapsed = time.perf_counter() - t0
            res = EvalResult(inp=inp, out=out, elapsed_s=float(elapsed), ok=ok, message=msg)

            # Update cache with simple LRU eviction
            if ok and bool(getattr(self, "_cache_enabled", True)):
                if not hasattr(self, "_cache"):
                    self._cache = {}
                if not hasattr(self, "_cache_order"):
                    self._cache_order = []
                self._cache[cache_key] = res
                self._cache_order.append(cache_key)
                if len(self._cache_order) > int(getattr(self, "_cache_max", 256)):
                    self._cache_evictions = int(getattr(self, "_cache_evictions", 0) or 0) + 1
                    old = self._cache_order.pop(0)
                    try:
                        del self._cache[old]
                    except Exception:
                        pass

            return res
    def get(self, inp: PointInputs, key: str, default: float = float("nan")) -> float:
        """Convenience: evaluate and fetch a single output key."""
        res = self.evaluate(inp)
        try:
            v = float(res.out.get(key, default))
        except Exception:
            v = default
        return v

    @staticmethod
    def residuals(out: Dict[str, float], targets: Dict[str, float]) -> Dict[str, float]:
        """Compute residuals (out - target) for selected keys."""
        r: Dict[str, float] = {}
        for k, tgt in targets.items():
            try:
                r[k] = float(out.get(k, float("nan"))) - float(tgt)
            except Exception:
                r[k] = float("nan")
        return r

    @staticmethod
    def residual_norm(residuals: Dict[str, float]) -> float:
        s = 0.0
        n = 0
        for v in residuals.values():
            if math.isfinite(v):
                s += float(v) * float(v)
                n += 1
        if n == 0:
            return float("inf")
        return math.sqrt(s / max(n, 1))

    def jacobian_targets(
        self,
        base: PointInputs,
        *,
        targets: list[str],
        variables: list[str],
        step_frac: float = 1e-4,
    ) -> list[list[float]]:
        """Hybrid Jacobian: analytic where registered, otherwise finite-difference.

        Returns J with shape (len(targets), len(variables)).
        """
        base_res = self.evaluate(base)
        y0 = {k: float(base_res.out.get(k, float("nan"))) for k in targets}
        J = [[0.0 for _ in variables] for __ in targets]

        for j, var in enumerate(variables):
            # analytic partials if available
            used_any_analytic = False
            for i, t in enumerate(targets):
                fn = get_derivative(t, var)
                if fn is not None:
                    used_any_analytic = True
                    try:
                        J[i][j] = float(fn(base, base_res.out))
                    except Exception:
                        J[i][j] = 0.0
            if used_any_analytic:
                continue

            # finite diff fallback
            try:
                x0 = float(getattr(base, var))
            except Exception:
                x0 = float("nan")
            h = step_frac * max(abs(x0), 1.0) if math.isfinite(x0) else step_frac
            if h == 0.0:
                h = step_frac
            d = base.to_dict()
            d[var] = (x0 + h) if math.isfinite(x0) else h
            inp1 = PointInputs.from_dict(d)
            y1 = self.evaluate(inp1).out
            for i, t in enumerate(targets):
                J[i][j] = (float(y1.get(t, float("nan"))) - y0[t]) / h
        return J
