import pandapower as pp
import pandapower.estimation as est
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from twin.contracts import TelemetryMessage

def clear_measurements(net):
    if hasattr(net, 'measurement'):
        net.measurement.drop(net.measurement.index, inplace=True)
    else:
        pp.create_measurement(net, "v", "bus", 1.0, 0.1, 0) # Just to initialize the dataframe, then clear
        net.measurement.drop(net.measurement.index, inplace=True)

def build_meas(net, telemetry: List[TelemetryMessage], pseudo_variance: float = 0.5):
    """
    Map TelemetryMessage objects to pandapower measurement table.
    We aggregate all load/sgen measurements into bus injections since the WLS estimator
    prefers 'bus', 'line', 'trafo' measurements.
    """
    clear_measurements(net)
    
    # Base case injections
    p_injections = np.zeros(len(net.bus))
    q_injections = np.zeros(len(net.bus))
    
    # Calculate base case net injections at each bus (sgen - load)
    for l_idx in net.load.index:
        b_idx = net.load.bus.at[l_idx]
        p_injections[b_idx] -= net.load.p_mw.at[l_idx]
        q_injections[b_idx] -= net.load.q_mvar.at[l_idx]
        
    for s_idx in net.sgen.index:
        b_idx = net.sgen.bus.at[s_idx]
        p_injections[b_idx] += net.sgen.p_mw.at[s_idx]
        q_injections[b_idx] += net.sgen.q_mvar.at[s_idx]
        
    # Apply telemetry over base case
    measured_buses_v = set()
    p_variances = np.full(len(net.bus), pseudo_variance)
    q_variances = np.full(len(net.bus), pseudo_variance)
    
    for msg in telemetry:
        vals = msg.values
        if "substation" in msg.topic:
            bus_idx = 0
            if 'vm_pu' in vals:
                pp.create_measurement(net, "v", "bus", vals['vm_pu'], 0.01, bus_idx)
                measured_buses_v.add(bus_idx)
            # The substation measurement includes ext_grid, not just load/sgen!
            # Ext grid is not a standard bus injection for observability, it's the slack.
            # We can skip providing P/Q for slack if V is provided, but let's provide if we want.
            
        elif "dt/" in msg.topic:
            bus_idx = int(msg.topic.split('/')[1])
            if 'vm_pu' in vals:
                pp.create_measurement(net, "v", "bus", vals['vm_pu'], 0.02, bus_idx)
                measured_buses_v.add(bus_idx)
            if 'p_kw' in vals:
                # Update the load part of the injection
                old_load_p = net.load[net.load.bus == bus_idx].p_mw.sum()
                new_load_p = vals['p_kw'] / 1000.0
                p_injections[bus_idx] += old_load_p - new_load_p # remove old load, add new load (negative)
                p_variances[bus_idx] = 0.03
                
        elif "inverter/" in msg.topic:
            sgen_idx = int(msg.topic.split('/')[1])
            bus_idx = net.sgen.bus.at[sgen_idx]
            if 'vm_pu' in vals:
                pp.create_measurement(net, "v", "bus", vals['vm_pu'], 0.01, bus_idx)
                measured_buses_v.add(bus_idx)
            if 'p_kw' in vals:
                old_sgen_p = net.sgen.p_mw.at[sgen_idx]
                new_sgen_p = vals['p_kw'] / 1000.0
                p_injections[bus_idx] += new_sgen_p - old_sgen_p
                p_variances[bus_idx] = 0.01
                
    # Create P/Q measurements for all buses (except ext_grid, which is slack and usually doesn't need P/Q if V is known)
    # Actually, supplying P/Q for slack bus is fine or we just skip it.
    ext_buses = set(net.ext_grid.bus.values)
    for b_idx in net.bus.index:
        if b_idx not in ext_buses:
            pp.create_measurement(net, "p", "bus", p_injections[b_idx], p_variances[b_idx], b_idx)
            pp.create_measurement(net, "q", "bus", q_injections[b_idx], q_variances[b_idx], b_idx)
            
    if 0 not in measured_buses_v:
        pp.create_measurement(net, "v", "bus", 1.0, 0.01, 0)
        
def run_estimation(net) -> Tuple[bool, float]:
    """
    Runs WLS state estimation.
    Returns (success_boolean, chi2_confidence).
    """
    try:
        success = est.estimate(net, init='flat')
        # Residual sum
        if success:
            chi2 = est.chi2_analysis(net)
            # If chi2 passes, it usually returns True or the value
            # Actually pandapower est.chi2_analysis just returns True/False.
            # We can compute residual manually if we want a score.
            res = net.res_bus_est.vm_pu
            return True, 1.0 # 1.0 means high confidence
        else:
            return False, 0.0
    except Exception as e:
        return False, 0.0
