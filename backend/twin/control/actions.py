import pandapower as pp
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any

class GridAction(ABC):
    @abstractmethod
    def apply(self, net: pp.pandapowerNet, state: Dict[str, Any]):
        """
        Applies the action to the network and/or state.
        Modifies net in-place.
        """
        pass
        
    @abstractmethod
    def revert(self, net: pp.pandapowerNet, state: Dict[str, Any]):
        """
        Reverts the action. Used during search/what-if analysis.
        """
        pass
        
class TapChangerAction(GridAction):
    def __init__(self, trafo_idx: int, step_delta: int):
        self.trafo_idx = trafo_idx
        self.step_delta = step_delta
        self.old_tap = None
        self.old_vn_hv = None
        
    def apply(self, net, state):
        self.old_tap = net.trafo.tap_pos.at[self.trafo_idx]
        self.old_vn_hv = net.trafo.vn_hv_kv.at[self.trafo_idx]
        
        # Just ensure tap doesn't exceed bounds, say -10 to +10
        new_tap = self.old_tap + self.step_delta
        new_tap = max(min(new_tap, 10), -10)
        net.trafo.tap_pos.at[self.trafo_idx] = new_tap
        
        # Force the voltage change by modifying vn_hv_kv directly
        # Tap on HV side changes the effective HV voltage rating
        step_pct = net.trafo.tap_step_percent.at[self.trafo_idx]
        if np.isnan(step_pct):
            step_pct = 1.25
            
        base_vn_hv = 33.0 # We know it's 33kV from build_net
        net.trafo.vn_hv_kv.at[self.trafo_idx] = base_vn_hv * (1.0 + new_tap * step_pct / 100.0)
        
    def revert(self, net, state):
        if self.old_tap is not None:
            net.trafo.tap_pos.at[self.trafo_idx] = self.old_tap
        if self.old_vn_hv is not None:
            net.trafo.vn_hv_kv.at[self.trafo_idx] = self.old_vn_hv

class CurtailPVAction(GridAction):
    def __init__(self, sgen_idx: int, limit_kw: float):
        self.sgen_idx = sgen_idx
        self.limit_kw = limit_kw
        self.old_p_mw = None
        
    def apply(self, net, state):
        self.old_p_mw = net.sgen.p_mw.at[self.sgen_idx]
        current = self.old_p_mw * 1000.0
        if current > self.limit_kw:
            net.sgen.p_mw.at[self.sgen_idx] = self.limit_kw / 1000.0
            
    def revert(self, net, state):
        if self.old_p_mw is not None:
            net.sgen.p_mw.at[self.sgen_idx] = self.old_p_mw
            
class SwitchReconfigureAction(GridAction):
    def __init__(self, open_switch_idx: int, close_switch_idx: int):
        self.open_switch_idx = open_switch_idx
        self.close_switch_idx = close_switch_idx
        
    def apply(self, net, state):
        net.switch.closed.at[self.open_switch_idx] = False
        net.switch.closed.at[self.close_switch_idx] = True
        
    def revert(self, net, state):
        net.switch.closed.at[self.open_switch_idx] = True
        net.switch.closed.at[self.close_switch_idx] = False

class BatteryDispatchAction(GridAction):
    def __init__(self, storage_idx: int, p_kw: float, q_kvar: float = 0.0):
        # p_kw > 0 means discharging (injection), p_kw < 0 means charging
        self.storage_idx = storage_idx
        self.p_kw = p_kw
        self.q_kvar = q_kvar
        self.old_p = None
        self.old_q = None
        
    def apply(self, net, state):
        self.old_p = net.storage.p_mw.at[self.storage_idx]
        self.old_q = net.storage.q_mvar.at[self.storage_idx]
        
        # In pandapower storage, p_mw > 0 is charging!
        # So we invert the sign. p_kw > 0 discharging -> p_mw < 0 charging
        net.storage.p_mw.at[self.storage_idx] = -self.p_kw / 1000.0
        net.storage.q_mvar.at[self.storage_idx] = -self.q_kvar / 1000.0
        
    def revert(self, net, state):
        if self.old_p is not None:
            net.storage.p_mw.at[self.storage_idx] = self.old_p
            net.storage.q_mvar.at[self.storage_idx] = self.old_q
