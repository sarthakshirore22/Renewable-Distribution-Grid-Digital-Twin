from typing import Dict, Any

def check_limits(net, cfg, thermal_state=None) -> Dict[str, Any]:
    """
    Check voltage, line loading, transformer loading, hot-spot and physical absurdity.
    Returns a dict with violations and a scalar severity.
    """
    violations = []
    severity = 0.0
    
    # 1. Physical absurdity (Collapse)
    # If not converged or any VM < 0.8 pu
    if not net.get("converged", True):
        violations.append("COLLAPSE: Power flow did not converge")
        return {"violations": violations, "severity": 1000.0}
        
    if net.res_bus.vm_pu.min() < 0.8:
        violations.append(f"COLLAPSE: Voltage below 0.8 pu ({net.res_bus.vm_pu.min():.3f})")
        return {"violations": violations, "severity": 1000.0}
        
    # 2. Voltage
    v_min = cfg.voltage_min_pu
    v_max = cfg.voltage_max_pu
    v_band = v_max - v_min
    
    for bus_id, vm in net.res_bus.vm_pu.items():
        if vm < v_min:
            violations.append(f"Under-voltage at bus {bus_id}: {vm:.3f} pu")
            severity += (v_min - vm) / v_band
        elif vm > v_max:
            violations.append(f"Over-voltage at bus {bus_id}: {vm:.3f} pu")
            severity += (vm - v_max) / v_band
            
    # 3. Line loading
    for line_id, load_pct in net.res_line.loading_percent.items():
        if load_pct > 100.0:
            violations.append(f"Line {line_id} overloaded: {load_pct:.1f}%")
            severity += (load_pct - 100.0) / 100.0
            
    # 4. Transformer loading (includes reverse flow natively in pandapower res_trafo)
    for trafo_id, load_pct in net.res_trafo.loading_percent.items():
        if load_pct > 100.0:
            violations.append(f"Transformer {trafo_id} overloaded: {load_pct:.1f}%")
            severity += (load_pct - 100.0) / 100.0
            
    # 5. Hot-spot (if provided)
    if thermal_state is not None:
        hotspot = thermal_state.get('hotspot_c', 20.0)
        if hotspot > 140.0:
            violations.append(f"CRITICAL: Transformer hot-spot: {hotspot:.1f}C")
            severity += (hotspot - 120.0) / 120.0 * 10
        elif hotspot > 120.0:
            violations.append(f"LIMIT: Transformer hot-spot: {hotspot:.1f}C")
            severity += (hotspot - 120.0) / 120.0
        elif hotspot > 100.0:
            violations.append(f"WARN: Transformer hot-spot: {hotspot:.1f}C")
            # warning does not strictly add physical severity to limit breaches unless required,
            # but we can add a tiny fraction
            severity += (hotspot - 100.0) / 100.0 * 0.1

    return {
        "violations": violations,
        "severity": severity
    }
