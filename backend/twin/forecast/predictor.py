import numpy as np
from typing import Dict, Any, Tuple
from twin.data.profiles import get_normalized_load_shapes
from twin.data.weather import generate_irradiance

class MockForecaster:
    """
    A mock forecaster that uses the true underlying data generation logic,
    but adds uncertainty bounds for p10 and p90.
    In a real app, this would wrap a trained LightGBM model.
    """
    def __init__(self, cfg, net):
        self.cfg = cfg
        self.net = net
        # (lightgbm blocked by system policy, so we purely mock it)
        
    def predict_window(self, start_step: int, window_steps: int = 24) -> Dict[str, Any]:
        """
        Returns p10, p50, p90 for the next `window_steps`.
        """
        end_step = min(96, start_step + window_steps)
        steps_to_predict = end_step - start_step
        
        if steps_to_predict <= 0:
            return None
            
        # 1. PV
        lat = self.cfg.weather_location['lat']
        lon = self.cfg.weather_location['lon']
        weather = generate_irradiance(lat, lon, "2025-06-22") # Next day or same day
        poa = weather['poa'].values[start_step:end_step]
        pv_pu = poa / 1000.0
        pv_pu[pv_pu > 1.0] = 1.0
        
        pv_p50 = np.zeros((steps_to_predict, len(self.net.sgen)))
        for i, sgen_id in enumerate(self.net.sgen.index):
            capacity = self.net.sgen.p_mw.at[sgen_id]
            pv_p50[:, i] = pv_pu * capacity
            
        # 2. Load
        shapes = get_normalized_load_shapes()
        load_p50 = np.zeros((steps_to_predict, len(self.net.load)))
        for i, load_id in enumerate(self.net.load.index):
            load_type = self.net.load.type.at[load_id] if 'type' in self.net.load else 'Residential'
            shape = shapes.get(load_type, shapes['Residential'])[start_step:end_step]
            
            peak_p = self.net.load.p_mw.at[load_id]
            min_f = self.cfg.min_load_fraction
            scaled = min_f + shape * (1.0 - min_f)
            load_p50[:, i] = scaled * peak_p
            
        # Create bounds
        # PV: uncertainty is proportional to the value (e.g. +/- 20%)
        pv_p10 = pv_p50 * 0.8
        pv_p90 = pv_p50 * 1.2
        
        # Load: +/- 10%
        load_p10 = load_p50 * 0.9
        load_p90 = load_p50 * 1.1
        
        return {
            'steps': steps_to_predict,
            'pv': {'p10': pv_p10, 'p50': pv_p50, 'p90': pv_p90},
            'load': {'p10': load_p10, 'p50': load_p50, 'p90': load_p90}
        }

def analyze_stress(forecast: Dict[str, Any], net, cfg) -> bool:
    """
    Evaluates if p90 forecast leads to limit violations.
    (Very simplified check: just check if total load > total capacity or PV > limits)
    """
    if forecast is None:
        return False
        
    # High stress if max PV in p90 > total load in p10 (overvoltage risk)
    max_pv = np.max(np.sum(forecast['pv']['p90'], axis=1))
    min_load = np.min(np.sum(forecast['load']['p10'], axis=1))
    
    if max_pv > min_load * 1.5:
        return True
        
    # High stress if max load in p90 > transformer capacity (thermal risk)
    # Case33bw transformer is 6.3 MVA = 6300 kVA = 6.3 MW approx.
    trafo_cap = 6.3 # MW
    max_load = np.max(np.sum(forecast['load']['p90'], axis=1))
    if max_load > trafo_cap * 0.9: # 90%
        return True
        
    return False
