import argparse
import json
import os
import time
from datetime import datetime
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
    path = f"configs/{scenario_id}.yaml"
    if os.path.exists(path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return ScenarioConfig(**data)
    else:
        # Fallback to default
        return ScenarioConfig(scenario_id=scenario_id, pv_size_kw=1000)

def run_scenario(scenario_id: str, force_randomize: bool = False):
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
    
    # Introduce stochastic noise if requested (simulating real-world conditions)
    if force_randomize:
        noise = np.random.normal(1.0, 0.08, len(pv_pu)) # +/- 8% noise
        pv_pu = np.clip(pv_pu * noise, 0.0, 1.0)
        # Randomize load shapes slightly too
        for key in shapes:
            shapes[key] = shapes[key] * np.random.normal(1.0, 0.05, len(shapes[key]))
    
    # State tracking
    thermal_state = {'transformer_temp': 25.0} # Assume ambient start
    action_log = []
    plant_severity_sum = 0.0
    
    # ---------------------------------------------------------
    # MASSIVE PERFORMANCE BOOST:
    # Instead of running 96 steps (every 15 mins), run 24 steps (hourly).
    # This reduces calculation time by 75%, making the UI return in seconds instead of minutes.
    # ---------------------------------------------------------
    steps = 24
    stride = 96 // steps
    
    print(f"Running scenario {scenario_id} for {steps} steps (Hourly)...")
    
    for t in range(steps):
        idx = t * stride
        
        # --- A. Step Plant ---
        # Apply Weather/Load to Plant
        # PV
        pv_capacity_kw = cfg.pv_size_kw / len(plant_net.bus)
        plant_net.sgen.p_mw = pv_pu[idx] * (pv_capacity_kw / 1000.0)
        
        # Load
        for i, load_idx in enumerate(plant_net.load.index):
            ltype = plant_net.load.type.at[load_idx] if 'type' in plant_net.load else 'Residential'
            shape = shapes.get(ltype, shapes['Residential'])[idx]
            min_f = cfg.min_load_fraction
            scaled = min_f + shape * (1.0 - min_f)
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
                temp = compute_hotspot(25.0, load_pu, thermal_state)
                thermal_state['transformer_temp'] = temp
        except Exception as e:
            # Plant collapsed
            print(f"Plant collapsed at step {t}: {e}")
            plant_severity_sum += 1000.0
            
        # --- B. Generate Telemetry ---
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        hr = int(idx * 15 // 60)
        mn = int((idx * 15) % 60)
        time_str = f"{today_str}T{hr:02d}:{mn:02d}:00Z"
        telemetry = generate_telemetry(plant_net, cfg, step=idx, current_time_str=time_str)
        
        # --- C. Step Twin ---
        twin_result = orchestrator.tick(telemetry, step=idx)
        
        # --- D. Closed Loop Action ---
        action = twin_result.get('recommended_action')
        if action:
            # Apply to Plant
            action.apply(plant_net, {})
            # Also apply to Twin's belief
            action.apply(orchestrator.net, {})
            
            action_log.append({
                'step': hr, # Show hour in the UI
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
