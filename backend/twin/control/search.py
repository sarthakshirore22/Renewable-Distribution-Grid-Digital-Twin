import copy
import pandapower as pp
import numpy as np
from typing import List, Dict, Any, Tuple
from twin.control.actions import GridAction, TapChangerAction, CurtailPVAction, SwitchReconfigureAction, BatteryDispatchAction
from twin.grid.limits import check_limits
from twin.grid.topology import is_radial_ok

def generate_candidate_actions(net, cfg) -> List[GridAction]:
    """
    Generates a list of candidate actions to try.
    Order in list acts as a tie-breaker, but we will rank them by cost.
    """
    actions = []
    
    # 1. Switch Reconfiguration
    # Try swapping adjacent switches (e.g., normally open vs normally closed)
    # Just a few predefined ones for case33bw
    # Normally open: 33, 34, 35, 36, 37
    # For a simple search space, try closing one of these and opening a nearby one.
    if len(net.switch) >= 37:
        actions.append(SwitchReconfigureAction(open_switch_idx=7, close_switch_idx=33))
        actions.append(SwitchReconfigureAction(open_switch_idx=11, close_switch_idx=34))
        
    # 2. Tap Changer
    if not net.trafo.empty:
        actions.append(TapChangerAction(trafo_idx=0, step_delta=-1))
        actions.append(TapChangerAction(trafo_idx=0, step_delta=1))
        
    # 3. Battery Dispatch
    if not net.storage.empty:
        # Full discharge
        actions.append(BatteryDispatchAction(storage_idx=0, p_kw=net.storage.max_p_mw.at[0] * 1000.0))
        # Full charge
        actions.append(BatteryDispatchAction(storage_idx=0, p_kw=-net.storage.max_p_mw.at[0] * 1000.0))
        
    # 4. PV Curtailment (Largest nodes)
    # Curtail the largest PV by 50%
    if not net.sgen.empty:
        max_idx = net.sgen.p_mw.idxmax()
        p_val = net.sgen.p_mw.at[max_idx]
        if p_val > 0:
            actions.append(CurtailPVAction(sgen_idx=max_idx, limit_kw=p_val * 1000.0 * 0.5))
            
    return actions

def get_action_cost(action: GridAction) -> float:
    """
    Ranking from GUIDE: Reconfigure (0) > Tap (1) > Battery (10) > Curtail (100)
    """
    if isinstance(action, SwitchReconfigureAction):
        return 0.0
    elif isinstance(action, TapChangerAction):
        return 1.0
    elif isinstance(action, BatteryDispatchAction):
        return 10.0
    elif isinstance(action, CurtailPVAction):
        return 100.0
    return 1000.0

def find_best_action(net, forecast: Dict[str, Any], cfg, current_state: Dict[str, Any] = None) -> GridAction:
    """
    Finds the cheapest action that resolves limit violations in the worst-case future step.
    If none resolve fully, returns the one that minimizes severity.
    """
    if forecast is None or forecast['steps'] == 0:
        return None
        
    candidates = generate_candidate_actions(net, cfg)
    if not candidates:
        return None
        
    # Find worst step in forecast (just sum of severity)
    # For speed, we just test the step with max PV and step with max load
    pv_sums = np.sum(forecast['pv']['p90'], axis=1)
    load_sums = np.sum(forecast['load']['p90'], axis=1)
    
    worst_pv_step = np.argmax(pv_sums)
    worst_load_step = np.argmax(load_sums)
    
    steps_to_test = list(set([worst_pv_step, worst_load_step]))
    
    best_action = None
    best_cost = float('inf')
    best_severity = float('inf')
    
    for action in candidates:
        action_severity = 0.0
        
        # Test the action
        for t in steps_to_test:
            net_copy = copy.deepcopy(net)
            
            # Apply forecast loading
            net_copy.sgen.p_mw = forecast['pv']['p90'][t]
            net_copy.load.p_mw = forecast['load']['p90'][t]
            
            # Apply action
            action.apply(net_copy, current_state)
            
            if not is_radial_ok(net_copy):
                action_severity += 10000.0
                continue
                
            try:
                pp.runpp(net_copy, numba=False)
                res = check_limits(net_copy, cfg)
                action_severity += res['severity']
            except Exception:
                action_severity += 1000.0 # Did not converge
                
        # Compare
        if action_severity == 0.0:
            # Resolves completely, check cost
            cost = get_action_cost(action)
            if cost < best_cost or best_severity > 0.0:
                best_cost = cost
                best_severity = 0.0
                best_action = action
        elif action_severity < best_severity:
            # Reduces severity but doesn't resolve completely
            best_severity = action_severity
            best_action = action
            best_cost = get_action_cost(action)
            
    # If no action reduces severity below the baseline (do nothing), return None
    # We should calculate baseline severity
    baseline_severity = 0.0
    for t in steps_to_test:
        net_copy = copy.deepcopy(net)
        net_copy.sgen.p_mw = forecast['pv']['p90'][t]
        net_copy.load.p_mw = forecast['load']['p90'][t]
        try:
            pp.runpp(net_copy, numba=False)
            res = check_limits(net_copy, cfg)
            baseline_severity += res['severity']
        except Exception:
            baseline_severity += 1000.0
            
    if best_action and best_severity < baseline_severity:
        return best_action
        
    return None
