import pandapower as pp
import numpy as np
from typing import Dict, Any

def time_series_loop(net, cfg, num_steps=96, pv_profiles=None, load_profiles=None, state=None):
    """
    Custom sequential time-series loop for 96 steps.
    Carries state (battery SoC, etc.) and executes passive inverter trips.
    pv_profiles: array of shape (96, num_sgen)
    load_profiles: dict with 'p_mw' and 'q_mvar' arrays of shape (96, num_load)
    """
    if state is None:
        state = {
            'soc_percent': 50.0,
            'tap_pos': 0,
            'switch_states': net.switch.closed.copy().values,
            'thermal': {'hotspot': 20.0} # placeholder for Part 3
        }
        
    results = []
    
    for t in range(num_steps):
        # Apply load and PV
        if load_profiles is not None:
            net.load.p_mw = load_profiles['p_mw'][t]
            net.load.q_mvar = load_profiles['q_mvar'][t]
            
        if pv_profiles is not None:
            net.sgen.p_mw = pv_profiles[t]
            net.sgen.in_service = True # Reset trips
            
        # Passive inverter trip loop (up to 3 iterations)
        tripped_energy_kwh = 0.0
        
        for iteration in range(3):
            # Run power flow
            try:
                pp.runpp(net, numba=False)
            except Exception:
                # Did not converge
                net['converged'] = False
                break
                
            net['converged'] = True
            
            # Check for overvoltage > 1.1 pu
            v_pu = net.res_bus.vm_pu
            tripped_any = False
            for sgen_id in net.sgen.index:
                if net.sgen.in_service.at[sgen_id]:
                    bus_id = net.sgen.bus.at[sgen_id]
                    if v_pu.at[bus_id] > 1.1:
                        # Trip
                        net.sgen.at[sgen_id, 'in_service'] = False
                        tripped_energy_kwh += net.sgen.p_mw.at[sgen_id] * 1000 * 0.25 # 15 mins = 0.25h
                        tripped_any = True
                        
            if not tripped_any:
                break
                
        # Record results
        if net['converged']:
            losses = net.res_line.pl_mw.sum() * 1000 + net.res_trafo.pl_mw.sum() * 1000
            gen = net.res_sgen.p_mw.sum() * 1000 + net.res_ext_grid.p_mw.sum() * 1000
            load = net.res_load.p_mw.sum() * 1000
            balance = gen - load - losses
            
            from twin.thermal.transformer import compute_hotspot
            if 'thermal' in state:
                trafo_load = net.res_trafo.loading_percent.iloc[0] / 100.0
                compute_hotspot(ambient_c=30.0, load_pu=trafo_load, state=state['thermal'], dt_hours=0.25)
        else:
            balance = np.nan
            
        res_step = {
            't': t,
            'converged': net['converged'],
            'tripped_energy_kwh': tripped_energy_kwh,
            'balance': balance,
            'vm_pu_min': net.res_bus.vm_pu.min() if net['converged'] else np.nan,
            'vm_pu_max': net.res_bus.vm_pu.max() if net['converged'] else np.nan,
            'vm_pu': net.res_bus.vm_pu.copy().values if net['converged'] else np.full(len(net.bus), np.nan)
        }
        results.append(res_step)
        
    return results, state
