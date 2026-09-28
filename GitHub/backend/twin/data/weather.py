import pvlib
import pandas as pd
import numpy as np

def generate_irradiance(lat: float, lon: float, date: str = '2025-06-21') -> pd.DataFrame:
    """
    Generates clear-sky 15-minute irradiance for a given location and date.
    Returns DataFrame with GHI, DNI, DHI, POA.
    """
    times = pd.date_range(f"{date} 00:00:00", f"{date} 23:45:00", freq='15min', tz='Asia/Kolkata')
    loc = pvlib.location.Location(lat, lon, tz='Asia/Kolkata')
    
    cs = loc.get_clearsky(times)
    
    # Assume fixed tilt for POA (e.g., tilt = latitude)
    tilt = lat
    surface_azimuth = 180 # South facing
    
    solar_position = loc.get_solarposition(times)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=surface_azimuth,
        solar_zenith=solar_position['apparent_zenith'],
        solar_azimuth=solar_position['azimuth'],
        dni=cs['dni'],
        ghi=cs['ghi'],
        dhi=cs['dhi']
    )
    
    df = pd.DataFrame({
        'ghi': cs['ghi'].values,
        'dni': cs['dni'].values,
        'dhi': cs['dhi'].values,
        'poa': poa['poa_global'].values
    })
    
    # Fill NAs at night with 0
    df = df.fillna(0)
    # Ensure no negative values
    df[df < 0] = 0
    
    return df

def apply_cloud_cover(poa_array: np.ndarray, scenario_id: str) -> np.ndarray:
    """
    Applies cloud cover multipliers based on scenario rules.
    poa_array is shape (96,). Returns shape (96,).
    """
    poa = poa_array.copy()
    
    if scenario_id == 's3_cloud_transient':
        # Drop by 80% around midday for a few steps
        # Midday is ~ 12:00 -> step 48
        poa[46:50] *= 0.2
    
    return poa
