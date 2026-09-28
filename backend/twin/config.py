
import yaml
from pydantic import BaseModel


class DeviceAccuracyConfig(BaseModel):
    feeder_head_voltage: float = 0.5
    feeder_head_power: float = 0.5
    dt_meter_voltage: float = 1.0
    dt_meter_power: float = 2.0
    inverter_power: float = 1.0
    temperature: float = 2.0
    pyranometer: float = 5.0
    battery_soc: float = 3.0

class CommDelayConfig(BaseModel):
    dt_meter_late_minutes: float = 5.0
    dt_meter_loss_percent: float = 5.0

class MismatchConfig(BaseModel):
    line_impedance_error_percent: float = 2.0
    load_deviation_percent: float = 5.0
    hidden_pv_kw: float = 0.0

class HardwareConfig(BaseModel):
    meter_coverage_percent: float = 100.0
    accuracy: DeviceAccuracyConfig = DeviceAccuracyConfig()
    delay: CommDelayConfig = CommDelayConfig()
    mismatch: MismatchConfig = MismatchConfig()
    faults: list[dict] = []

class ScenarioConfig(BaseModel):
    scenario_id: str
    pv_size_kw: float
    pv_placement: str = "uniform"  # uniform, end, etc.
    inverter_ratio: float = 1.1
    min_load_fraction: float = 0.4
    voltage_min_pu: float = 0.95
    voltage_max_pu: float = 1.05
    substation_voltage_pu: float = 1.0
    curtailment_cap_percent: float = 20.0
    curtailment_cap_per_day: bool = True
    battery_mw: float = 1.0
    battery_mwh: float = 2.0
    cost_weights: dict[str, float] = {
        "curtailed_kwh": 1.0,
        "switch_ops": 10.0,
        "battery_throughput_kwh": 0.5,
        "extra_losses_kwh": 0.1,
        "gini": 100.0,
        "latency_penalty": 50.0
    }
    weather_location: dict[str, float] = {"lat": 21.15, "lon": 79.09}
    seed: int = 42
    hardware: HardwareConfig = HardwareConfig()

    @classmethod
    def load_yaml(cls, path: str) -> "ScenarioConfig":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)
