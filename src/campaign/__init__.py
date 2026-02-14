"""Campaign Pack (v363.0).

Deterministic, audit-safe campaign exports and batch evaluation helpers.

External optimizers provide *inputs* only. SHAMS remains the sole evaluator.

© 2026 Afshin Arjhangmehr
"""

from .spec import CampaignSpec, CampaignVariable, load_campaign_spec, validate_campaign_spec
from .generate import generate_candidates
from .export import export_campaign_bundle
from .eval import evaluate_campaign_candidates

__all__ = [
    "CampaignSpec",
    "CampaignVariable",
    "load_campaign_spec",
    "validate_campaign_spec",
    "generate_candidates",
    "export_campaign_bundle",
    "evaluate_campaign_candidates",
]
