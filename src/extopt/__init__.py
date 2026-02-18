"""SHAMS External Optimization SDK (firewalled).

The ExtOpt SDK exposes deterministic batch evaluation for concept families.
It is designed for *external* optimizers and batch concept studies.

Key invariants:
- Same inputs -> same outputs (deterministic)
- No hidden iteration / no internal optimization
- Constraints are explicit and returned as a ledger

Author: © 2026 Afshin Arjhangmehr
"""

from .family import ConceptFamily, load_concept_family
from .batch import BatchEvalConfig, BatchEvalResult, evaluate_concept_family
from .cache import DiskCache
from .evidence import export_evidence_pack
from .bundle import BundleCandidate, BundleProvenance, export_bundle_zip
from .orchestrator import OptimizerJob, run_optimizer_job
from .orchestrator_v385 import OrchestratorRunSpec, OrchestratorRunResult, run_orchestrator_v385_from_concept_family

__all__ = [
    "ConceptFamily",
    "load_concept_family",
    "BatchEvalConfig",
    "BatchEvalResult",
    "evaluate_concept_family",
    "DiskCache",
    "export_evidence_pack",
    "BundleCandidate",
    "BundleProvenance",
    "export_bundle_zip",
    "OptimizerJob",
    "run_optimizer_job",
    "OrchestratorRunSpec",
    "OrchestratorRunResult",
    "run_orchestrator_v385_from_concept_family",
]
