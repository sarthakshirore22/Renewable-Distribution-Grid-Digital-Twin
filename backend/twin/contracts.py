from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QualityEnum(str, Enum):
    good = "good"
    stale = "stale"
    missing = "missing"
    suspect = "suspect"
    substituted = "substituted"

class TelemetryMessage(BaseModel):
    topic: str
    ts: str
    seq: int
    quality: QualityEnum
    values: dict[str, float]
    meta: dict[str, Any] = Field(default_factory=lambda: {"simulated": True})

class ScenarioManifest(BaseModel):
    scenarios: list[dict[str, Any]]

class RunFile(BaseModel):
    meta: dict[str, Any]
    config: dict[str, Any]
    network_topology: dict[str, Any]
    device_registry: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    kpis: dict[str, float]

class WhatIfRequest(BaseModel):
    step: int
    pv_scale: float
    load_scale: float
    cost_weights: dict[str, float]

class InjectRequest(BaseModel):
    fault_type: str
    parameters: dict[str, Any]

def export_schemas(output_dir: str):
    import json
    import os
    os.makedirs(output_dir, exist_ok=True)
    models = {
        "TelemetryMessage": TelemetryMessage,
        "ScenarioManifest": ScenarioManifest,
        "RunFile": RunFile,
        "WhatIfRequest": WhatIfRequest,
        "InjectRequest": InjectRequest
    }
    for name, model in models.items():
        with open(os.path.join(output_dir, f"{name}.json"), "w") as f:
            json.dump(model.model_json_schema(), f, indent=2)

if __name__ == "__main__":
    export_schemas("docs/contracts")
