import numpy as np
import pandas as pd
from twin.data.weather import generate_irradiance, apply_cloud_cover

def get_normalized_load_shapes() -> dict:
    """
    Returns a dictionary of normalized 0-1 shapes of length 96 for load profiles.
    """
    # 96 steps
    steps = np.arange(96)
    hours = steps * 0.25
    
    # Residential: morning and evening peaks
    res = 0.3 + 0.3 * np.exp(-0.5 * ((hours - 8) / 1.5)**2) + 0.7 * np.exp(-0.5 * ((hours - 19) / 2.0)**2)
    res = (res - res.min()) / (res.max() - res.min())
    
    # Commercial: midday broad peak
    com = 0.2 + 0.8 * np.exp(-0.5 * ((hours - 14) / 3.0)**2)
    com = (com - com.min()) / (com.max() - com.min())
    
    # Agricultural: night/early morning and late afternoon depending on tariffs
    agr = 0.1 + 0.9 * np.exp(-0.5 * ((hours - 6) / 2.0)**2) + 0.5 * np.exp(-0.5 * ((hours - 16) / 1.5)**2)
    agr = (agr - agr.min()) / (agr.max() - agr.min())
    
    return {'Residential': res, 'Commercial': com, 'Agricultural': agr}

def generate_profiles(net, cfg, date='2025-06-21'):
    """
    Generate deterministic (96, num_load) and (96, num_sgen) arrays for a given network and config.
    """
    num_steps = 96
    
    # 1. PV Profiles
    lat = cfg.weather_location['lat']
    lon = cfg.weather_location['lon']
    weather = generate_irradiance(lat, lon, date)
    
    poa_clear = weather['poa'].values
    poa_actual = apply_cloud_cover(poa_clear, cfg.scenario_id)
    
    # Convert POA (W/m2) to normalized PV output (pu). Assume 1000 W/m2 = 1.0 pu.
    pv_pu = poa_actual / 1000.0
    pv_pu[pv_pu > 1.0] = 1.0 # Clip just in case
    
    pv_profiles = np.zeros((num_steps, len(net.sgen)))
    for i, sgen_id in enumerate(net.sgen.index):
        capacity_mw = net.sgen.p_mw.at[sgen_id]
        pv_profiles[:, i] = pv_pu * capacity_mw
        
    # 2. Load Profiles
    shapes = get_normalized_load_shapes()
    
    load_p = np.zeros((num_steps, len(net.load)))
    load_q = np.zeros((num_steps, len(net.load)))
    
    for i, load_id in enumerate(net.load.index):
        load_type = net.load.type.at[load_id] if 'type' in net.load else 'Residential'
        if load_type not in shapes:
            load_type = 'Residential'
            
        shape = shapes[load_type]
        
        # Scale to match peak capacity defined in the network
        peak_p = net.load.p_mw.at[load_id]
        peak_q = net.load.q_mvar.at[load_id]
        
        # Ensure minimum load matches config (min_load_fraction)
        min_f = cfg.min_load_fraction
        
        # Scale the 0-1 shape to min_f - 1.0
        scaled_shape = min_f + shape * (1.0 - min_f)
        
        load_p[:, i] = scaled_shape * peak_p
        load_q[:, i] = scaled_shape * peak_q
        
    load_profiles = {'p_mw': load_p, 'q_mvar': load_q}
    
    return pv_profiles, load_profiles
