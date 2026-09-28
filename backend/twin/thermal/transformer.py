def compute_hotspot(ambient_c: float, load_pu: float, state: dict, dt_hours: float = 0.25):
    """
    Computes transformer hotspot temperature using a simplified IEC 60076-7 model.
    Updates state dict in place.
    
    Parameters:
    - ambient_c: Ambient temperature in Celsius
    - load_pu: Transformer loading (S_load / S_rated)
    - state: dictionary containing 'top_oil_c', 'hotspot_c'
    - dt_hours: time step in hours (default 0.25 for 15 min)
    """
    # Simplified constants for a distribution transformer
    tau_oil = 3.0 # Oil time constant (hours)
    tau_wind = 0.1 # Winding time constant (hours)
    d_theta_oil_rated = 50.0 # Top-oil rise at rated load (K)
    d_theta_wind_rated = 25.0 # Hot-spot to top-oil gradient at rated load (K)
    R = 5.0 # Ratio of load losses to no-load losses
    
    # Exponents
    x = 0.8 # Oil exponent
    y = 1.6 # Winding exponent
    
    # Current states
    if 'top_oil_c' not in state:
        state['top_oil_c'] = ambient_c
    if 'hotspot_c' not in state:
        state['hotspot_c'] = ambient_c
        
    theta_oil_prev = state['top_oil_c']
    theta_h_prev = state['hotspot_c']
    
    # Ultimate top-oil rise
    # d_theta_oil_ult = d_theta_oil_rated * ((1 + R * load_pu**2) / (1 + R)) ** x
    term = (1 + R * (load_pu ** 2)) / (1 + R)
    d_theta_oil_ult = d_theta_oil_rated * (term ** x)
    
    # Ultimate hot-spot to top-oil gradient
    d_theta_wind_ult = d_theta_wind_rated * (load_pu ** y)
    
    # Ultimate temperatures
    theta_oil_ult = ambient_c + d_theta_oil_ult
    theta_h_ult = theta_oil_ult + d_theta_wind_ult
    
    import math
    
    # Exact exponential integration for the step
    theta_oil_new = theta_oil_ult + (theta_oil_prev - theta_oil_ult) * math.exp(-dt_hours / tau_oil)
    
    d_theta_wind_prev = theta_h_prev - theta_oil_prev
    d_theta_wind_new = d_theta_wind_ult + (d_theta_wind_prev - d_theta_wind_ult) * math.exp(-dt_hours / tau_wind)
    
    theta_h_new = theta_oil_new + d_theta_wind_new
    
    # Update state
    state['top_oil_c'] = theta_oil_new
    state['hotspot_c'] = theta_h_new
    
    return theta_h_new
