
import pandapower as pp
import pandapower.networks as nw


def assign_line_limits(net):
    # Trunks get 0.30 kA, laterals 0.15 kA
    # For case33bw, lines close to slack bus (bus 0) are trunks.
    # We can just assign based on line index for simplicity or use a heuristic.
    # Simple heuristic: first 10 lines are trunk, rest are laterals.
    for idx in net.line.index:
        if idx < 10:
            net.line.loc[idx, 'max_i_ka'] = 0.30
        else:
            net.line.loc[idx, 'max_i_ka'] = 0.15

def build_net(cfg, mismatch: dict | None = None):
    # Start with raw case33bw
    net = nw.case33bw()
    
    # Optional mismatch
    if mismatch:
        impedance_error = mismatch.get('line_impedance_error_percent', 0) / 100.0
        load_error = mismatch.get('load_deviation_percent', 0) / 100.0
        
        if impedance_error:
            net.line['r_ohm_per_km'] *= (1 + impedance_error)
            net.line['x_ohm_per_km'] *= (1 + impedance_error)
            
        if load_error:
            net.load['p_mw'] *= (1 + load_error)
            net.load['q_mvar'] *= (1 + load_error)

    # Convert to operational network
    # 1. 33 kV ext_grid and 6.3 MVA 33/12.66 kV transformer with OLTC
    # Existing ext_grid is at bus 0 at 12.66kV. We replace it.
    old_slack = net.ext_grid.bus.values[0]
    
    # Create 33kV bus
    bus33 = pp.create_bus(net, vn_kv=33.0, name="Substation 33kV")
    net.ext_grid.loc[0, 'bus'] = bus33
    net.ext_grid.loc[0, 'vm_pu'] = cfg.substation_voltage_pu
    
    # Create transformer
    pp.create_transformer_from_parameters(
        net, hv_bus=bus33, lv_bus=old_slack,
        sn_mva=6.3, vn_hv_kv=33.0, vn_lv_kv=12.66,
        vkr_percent=1.0, vk_percent=7.0, pfe_kw=10.0, i0_percent=0.1,
        tap_side="hv", tap_neutral=0, tap_min=-8, tap_max=8, tap_step_percent=1.25, tap_pos=0,
        name="Substation Trafo"
    )
    
    # 2. Line thermal limits
    assign_line_limits(net)
    
    # 3. PV integration (Uniform placement example)
    pv_kw_per_bus = cfg.pv_size_kw / len(net.bus)
    for bus_idx in net.bus.index:
        pp.create_sgen(
            net, bus=bus_idx, 
            p_mw=pv_kw_per_bus / 1000.0, 
            sn_mva=(pv_kw_per_bus / 1000.0) * cfg.inverter_ratio,
            name=f"PV_{bus_idx}"
        )
        
    # Add hidden PV if present
    if mismatch and mismatch.get('hidden_pv_kw', 0) > 0:
        pp.create_sgen(
            net, bus=10, # arbitrary location for hidden PV
            p_mw=mismatch['hidden_pv_kw'] / 1000.0,
            sn_mva=(mismatch['hidden_pv_kw'] / 1000.0) * cfg.inverter_ratio,
            name="Hidden_PV"
        )
        
    # 4. Battery at bus 14
    pp.create_storage(
        net, bus=14, p_mw=0, max_e_mwh=cfg.battery_mwh, min_e_mwh=0.1 * cfg.battery_mwh,
        soc_percent=50.0, max_p_mw=cfg.battery_mw, min_p_mw=-cfg.battery_mw,
        name="Battery_Bus14"
    )
    
    # 5. Loads are already there in case33bw.
    # We can tag them.
    for i, load_idx in enumerate(net.load.index):
        if i % 3 == 0:
            net.load.loc[load_idx, 'type'] = 'Residential'
        elif i % 3 == 1:
            net.load.loc[load_idx, 'type'] = 'Commercial'
        else:
            net.load.loc[load_idx, 'type'] = 'Agricultural'

    return net
