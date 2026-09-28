import argparse
import json
import os
import time
import pandapower as pp
import numpy as np

from twin.config import ScenarioConfig
from twin.grid.builder import build_net
from twin.gateway.sensor import generate_telemetry
from twin.orchestrator import DigitalTwinOrchestrator
from twin.data.profiles import get_normalized_load_shapes
from twin.data.weather import generate_irradiance
from twin.grid.limits import check_limits
from twin.thermal.transformer import compute_hotspot

import yaml
import warnings
warnings.filterwarnings("ignore")

def load_scenario(scenario_id: str) -> ScenarioConfig:
    import os
    path = f"configs/{scenario_id}.yaml"
    if os.path.exists(path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return ScenarioConfig(**data)
    else:
        # Fallback to default
        return ScenarioConfig(scenario_id=scenario_id, pv_size_kw=1000)

def run_scenario(scenario_id: str):
    start_time = time.time()
    
    # 1. Setup config
    cfg = load_scenario(scenario_id)
    
    # 2. Setup Plant
    plant_net = build_net(cfg)
    
    # 3. Setup Twin
    twin_net = build_net(cfg)
    orchestrator = DigitalTwinOrchestrator(twin_net, cfg)
    
    # Pre-generate environmental profiles
    shapes = get_normalized_load_shapes()
    weather = generate_irradiance(cfg.weather_location['lat'], cfg.weather_location['lon'], "2025-06-22")
    poa = weather['poa'].values
    pv_pu = poa / 1000.0
    pv_pu[pv_pu > 1.0] = 1.0
    
    # State tracking
    thermal_state = {'transformer_temp': 25.0} # Assume ambient start
    action_log = []
    plant_severity_sum = 0.0
    
    steps = 96
    
    print(f"Running scenario {scenario_id} for {steps} steps...")
    
    for t in range(steps):
        # --- A. Step Plant ---
        # Apply Weather/Load to Plant
        # PV
        for i, sgen_idx in enumerate(plant_net.sgen.index):
            # We scale using capacity instead
            continue
            
        # Proper way to set profiles without destroying capacity
        # Since build_net sets max_p_mw or sn_mva?
        # In case33bw, we just compute from cfg.pv_size_kw / len(bus)
        pv_capacity_kw = cfg.pv_size_kw / len(plant_net.bus)
        plant_net.sgen.p_mw = pv_pu[t] * (pv_capacity_kw / 1000.0)
        
        # Load
        for i, load_idx in enumerate(plant_net.load.index):
            ltype = plant_net.load.type.at[load_idx] if 'type' in plant_net.load else 'Residential'
            shape = shapes.get(ltype, shapes['Residential'])[t]
            min_f = cfg.min_load_fraction
            scaled = min_f + shape * (1.0 - min_f)
            # wait, need base load. We can store it in sn_mva.
            # case33bw sets p_mw. We should read from original.
            # Let's just assume we read from a stored 'base_p_mw' column.
            if 'base_p_mw' not in plant_net.load.columns:
                plant_net.load['base_p_mw'] = plant_net.load.p_mw
            plant_net.load.p_mw.at[load_idx] = plant_net.load.base_p_mw.at[load_idx] * scaled
            
        # Run Plant Power Flow
        try:
            pp.runpp(plant_net, numba=False)
            res = check_limits(plant_net, cfg, thermal_state)
            plant_severity_sum += res['severity']
            
            # Thermal update
            if not plant_net.trafo.empty:
                load_pu = plant_net.res_trafo.loading_percent.at[0] / 100.0
                # compute_hotspot(ambient_c, load_pu, state, dt_hours)
                temp = compute_hotspot(25.0, load_pu, thermal_state)
                thermal_state['transformer_temp'] = temp
        except Exception as e:
            # Plant collapsed
            print(f"Plant collapsed at step {t}: {e}")
            plant_severity_sum += 1000.0
            
        # --- B. Generate Telemetry ---
        # Current time string
        hr = int(t * 15 // 60)
        mn = int((t * 15) % 60)
        time_str = f"2025-06-22T{hr:02d}:{mn:02d}:00Z"
        telemetry = generate_telemetry(plant_net, cfg, step=t, current_time_str=time_str)
        
        # --- C. Step Twin ---
        twin_result = orchestrator.tick(telemetry, step=t)
        
        # --- D. Closed Loop Action ---
        action = twin_result.get('recommended_action')
        if action:
            # Apply to Plant
            action.apply(plant_net, {})
            # Also apply to Twin's belief? Twin search already clones. 
            # In a real closed loop, twin belief is updated by next cycle's measurements.
            # But the twin's internal model needs the action applied so it knows it did it!
            action.apply(orchestrator.net, {})
            
            action_log.append({
                'step': t,
                'action': action.__class__.__name__,
                'time': time_str
            })
            
    # Calculate execution time
    exec_time = time.time() - start_time
    print(f"Finished in {exec_time:.2f} seconds. Severity: {plant_severity_sum:.2f}")
    
    # Output report
    report = {
        'scenario_id': scenario_id,
        'execution_time_seconds': exec_time,
        'total_plant_severity': plant_severity_sum,
        'actions_taken': len(action_log),
        'action_log': action_log
    }
    
    os.makedirs('reports', exist_ok=True)
    with open(f"reports/results_{scenario_id}.json", "w") as f:
        json.dump(report, f, indent=4)
        
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, default="t1", help="Scenario ID to run")
    args = parser.parse_args()
    
    run_scenario(args.scenario)
