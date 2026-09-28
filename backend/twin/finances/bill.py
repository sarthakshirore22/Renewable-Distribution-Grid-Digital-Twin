import json
import os
from twin.config import ScenarioConfig

def compute_bill(scenario_id: str, cfg: ScenarioConfig = None) -> dict:
    report_path = f"reports/results_{scenario_id}.json"
    if not os.path.exists(report_path):
        return {"error": f"Report not found for {scenario_id}"}
        
    with open(report_path, "r") as f:
        data = json.load(f)
        
    if cfg is None:
        import yaml
        cfg_path = f"configs/{scenario_id}.yaml"
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cdata = yaml.safe_load(f)
            cfg = ScenarioConfig(**cdata)
        else:
            cfg = ScenarioConfig(scenario_id=scenario_id, pv_size_kw=1000)
            
    # Breakdown costs based on action_log
    # Action types: CurtailPVAction, SwitchReconfigureAction, TapChangerAction, BatteryDispatchAction
    
    breakdown = {
        'switch_ops': 0.0,
        'curtailed_kwh': 0.0,
        'battery_throughput_kwh': 0.0,
        'tap_ops': 0.0,
        'unresolved_severity': 0.0
    }
    
    actions = data.get('action_log', [])
    for act in actions:
        atype = act.get('action')
        if atype == 'SwitchReconfigureAction':
            breakdown['switch_ops'] += 1.0 * cfg.cost_weights.get('switch_ops', 10.0)
        elif atype == 'TapChangerAction':
            # Not explicitly in cost_weights in the prompt, but let's give it a small cost
            breakdown['tap_ops'] += 1.0 * 2.0
        elif atype == 'CurtailPVAction':
            # Roughly estimate the kWh curtailed per step. 
            # In a real model, we track exactly how much was curtailed.
            # Assuming 1 step = 15 mins (0.25h). For simplicity, we just count action occurrences * fixed amount
            # or if the report had details, we'd use them.
            breakdown['curtailed_kwh'] += 10.0 * cfg.cost_weights.get('curtailed_kwh', 1.0) # Assume 10 kWh curtailed per action
        elif atype == 'BatteryDispatchAction':
            breakdown['battery_throughput_kwh'] += 25.0 * cfg.cost_weights.get('battery_throughput_kwh', 0.5)
            
    # Penalize unresolved physical severity at the end
    severity = data.get('total_plant_severity', 0.0)
    # Severity is heavily weighted to simulate "repair bill" for transformer aging or penalties
    breakdown['unresolved_severity'] = severity * 1.5 
    
    total = sum(breakdown.values())
    
    formatted_breakdown = {k: f"${v:.2f}" for k, v in breakdown.items() if v > 0}
    
    return {
        'total_bill_usd': total,
        'total_formatted': f"${total:.2f}",
        'breakdown_usd': breakdown,
        'breakdown_formatted': formatted_breakdown
    }
