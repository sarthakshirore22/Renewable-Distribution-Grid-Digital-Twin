import numpy as np
import time
from typing import List, Dict, Any
from twin.contracts import TelemetryMessage, QualityEnum

class TelemetryBuffer:
    def __init__(self):
        self.buffer = []
        
    def add(self, message: TelemetryMessage, delay_minutes: float, drop: bool = False):
        if drop:
            return
        
        # We store the message and the time it becomes available
        # But wait, ts in message is usually step index or string.
        # Let's say ts is just the step index (t).
        # delay in steps = delay_minutes / 15
        release_t = message.seq + (delay_minutes / 15.0)
        self.buffer.append((release_t, message))
        
    def get_messages(self, current_t: int) -> List[TelemetryMessage]:
        ready = []
        keep = []
        for release_t, msg in self.buffer:
            if current_t >= release_t:
                ready.append(msg)
            else:
                keep.append((release_t, msg))
        self.buffer = keep
        return ready

def generate_telemetry(net, cfg, step: int, current_time_str: str) -> List[TelemetryMessage]:
    """
    Generates noisy telemetry from the converged network state.
    """
    messages = []
    
    acc = cfg.hardware.accuracy
    
    # 1. Substation meter (bus 0, ext_grid)
    if not net.res_ext_grid.empty:
        p_sub = net.res_ext_grid.p_mw.iloc[0] * 1000
        q_sub = net.res_ext_grid.q_mvar.iloc[0] * 1000
        v_sub = net.res_bus.vm_pu.iloc[0]
        
        # Add noise
        v_noise = np.random.normal(0, acc.feeder_head_voltage / 100.0 * v_sub)
        p_noise = np.random.normal(0, acc.feeder_head_power / 100.0 * abs(p_sub) + 1e-3)
        
        msg = TelemetryMessage(
            topic="substation/meter",
            ts=current_time_str,
            seq=step,
            quality=QualityEnum.good,
            values={"vm_pu": v_sub + v_noise, "p_kw": p_sub + p_noise, "q_kvar": q_sub}
        )
        messages.append(msg)
        
    # 2. DT meters (Loads)
    coverage = cfg.hardware.meter_coverage_percent / 100.0
    for load_id in net.load.index:
        if np.random.rand() > coverage:
            continue
            
        bus_id = net.load.bus.at[load_id]
        v_bus = net.res_bus.vm_pu.at[bus_id]
        p_load = net.res_load.p_mw.at[load_id] * 1000
        
        v_noise = np.random.normal(0, acc.dt_meter_voltage / 100.0 * v_bus)
        p_noise = np.random.normal(0, acc.dt_meter_power / 100.0 * abs(p_load) + 1e-3)
        
        msg = TelemetryMessage(
            topic=f"dt/{bus_id}/meter",
            ts=current_time_str,
            seq=step,
            quality=QualityEnum.good,
            values={"vm_pu": v_bus + v_noise, "p_kw": p_load + p_noise}
        )
        messages.append(msg)
        
    # 3. Inverter telemetry
    for sgen_id in net.sgen.index:
        bus_id = net.sgen.bus.at[sgen_id]
        v_bus = net.res_bus.vm_pu.at[bus_id]
        p_sgen = net.res_sgen.p_mw.at[sgen_id] * 1000
        
        p_noise = np.random.normal(0, acc.inverter_power / 100.0 * abs(p_sgen) + 1e-3)
        
        msg = TelemetryMessage(
            topic=f"inverter/{sgen_id}/meter",
            ts=current_time_str,
            seq=step,
            quality=QualityEnum.good,
            values={"vm_pu": v_bus, "p_kw": p_sgen + p_noise} # Inverter voltage usually highly accurate or identical
        )
        messages.append(msg)
        
    return messages
