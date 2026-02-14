
from dataclasses import dataclass
from typing import List, Dict

@dataclass(frozen=True)
class PhysicsModel:
    id: str
    domain: str
    equations: List[str]
    closures: List[str]
    authority: str
    validity: Dict[str, str]

PHYSICS_REGISTRY = {
    "power_balance.v1": PhysicsModel(
        id="power_balance.v1",
        domain="Core plasma power balance",
        equations=[
            "P_fus = n^2 <σv> E_fus V",
            "P_alpha = 0.2 P_fus",
            "P_loss = P_cond + P_rad + P_exh",
        ],
        closures=["H98y2 confinement scaling", "Fixed Zeff radiation proxy"],
        authority="Authoritative",
        validity={"Bt": "2–15 T", "R": "1–10 m", "Ip": "1–25 MA"},
    ),
    "operational_limits.v1": PhysicsModel(
        id="operational_limits.v1",
        domain="Operational limits",
        equations=[
            "β_N = β (%) a B / I_p",
            "n/n_GW = n_e / (I_p / (π a^2))",
        ],
        closures=["Troyon beta limit", "Greenwald density limit"],
        authority="Authoritative",
        validity={"β_N": "< 4", "n/n_GW": "< 1.2"},
    ),
}

MODE_PHYSICS = {
    "Point Designer": list(PHYSICS_REGISTRY.keys()),
    "Systems Mode": list(PHYSICS_REGISTRY.keys()),
    "Scan Lab": list(PHYSICS_REGISTRY.keys()),
    "Pareto Lab": list(PHYSICS_REGISTRY.keys()),
    "Benchmarks": list(PHYSICS_REGISTRY.keys()),
}


import json, hashlib

def physics_registry_hash() -> str:
    payload = {}
    for k, v in PHYSICS_REGISTRY.items():
        payload[k] = {
            "domain": v.domain,
            "equations": v.equations,
            "closures": v.closures,
            "authority": v.authority,
            "validity": v.validity,
        }
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
