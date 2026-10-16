"""
Multi-Bed Fixed Bed Hydrocracking Reactor Model
Simulates a commercial 3-bed trickle-bed hydrocracking reactor with interbed hydrogen quenches,
axial temperature exotherms, WABT calculations, Ergun pressure drops, and product yields.
"""

import numpy as np
from .kinetics import HCUKinetics

class HydrocrackingReactor:
    def __init__(self):
        self.kinetics = HCUKinetics()
        
        # Reactor physical specifications
        self.num_beds = 3
        self.bed_volume_fractions = [0.28, 0.36, 0.36]  # Volume distribution
        self.total_catalyst_volume_m3 = 145.0  # ~35,000 BPD commercial unit
        self.catalyst_bulk_density = 780.0     # kg/m3
        self.reactor_diameter = 3.2            # meters
        
        # Specific heats (J / kg * K)
        self.cp_oil = 2450.0  # Average hydrocarbon liquid/vapor mix
        self.cp_gas = 14500.0 # Hydrogen-rich recycle gas
        
        # Quench gas temperature (°C)
        self.quench_gas_temp_c = 55.0
        
        # Ergun equation base parameters
        self.particle_diameter = 0.0016  # 1.6 mm trilobe extrudate
        self.bed_void_fraction = 0.40
        self.base_dp_clean_bar = [1.2, 1.4, 1.4]  # Clean bed differential pressures (bar)
        
    def calculate_wabt(self, bed_temperatures):
        """
        Calculates commercial Weighted Average Bed Temperature (WABT).
        Formula: Sum(w_i * (T_in,i + 2 * T_out,i) / 3)
        bed_temperatures: list of tuples [(Tin_1, Tout_1), (Tin_2, Tout_2), (Tin_3, Tout_3)]
        """
        wabt = 0.0
        for i, (t_in, t_out) in enumerate(bed_temperatures):
            w = self.bed_volume_fractions[i]
            # Standard refining 2/3 outlet weighting for exothermic fixed beds
            bed_avg_t = (t_in + 2.0 * t_out) / 3.0
            wabt += w * bed_avg_t
        return wabt

    def simulate_reactor(
        self,
        feed_flow_m3_h,
        feed_api,
        feed_nitrogen_ppm,
        reactor_inlet_temp_c,
        reactor_pressure_bar,
        recycle_gas_ratio_nm3_m3,
        recycle_h2_purity_pct,
        quench_flows_kg_h,
        catalyst_activities,
        coke_wt_pct_per_bed=[2.0, 1.5, 1.2],
        time_on_stream_days=100.0,
        feed_yields=None
    ):
        """
        Full simulation of 3-bed reactor profile.
        
        Parameters:
        - feed_flow_m3_h: Fresh feed volumetric rate (m3/h)
        - feed_api: Feed API gravity (typically 20-24)
        - feed_nitrogen_ppm: Basic/organic nitrogen in feed (ppmw)
        - reactor_inlet_temp_c: Furnace outlet temperature entering Bed 1 (°C)
        - reactor_pressure_bar: Reactor total pressure (typically 130-170 bar)
        - recycle_gas_ratio_nm3_m3: H2/Oil treat gas ratio (typically 1200 - 1800 Nm3/m3)
        - recycle_h2_purity_pct: Recycle gas H2 mole % (typically 88 - 96%)
        - quench_flows_kg_h: list/tuple of [quench_bed2_kg_h, quench_bed3_kg_h]
        - catalyst_activities: list of length 3 [a_bed1, a_bed2, a_bed3]
        - coke_wt_pct_per_bed: list of coke content on catalyst
        - time_on_stream_days: TOS in days
        - feed_yields: initial feed lump fractions (default 100% VGO)
        
        Returns:
        dict containing temperatures, yields, conversions, hydrogen consumption,
        pressure drops, exotherms, and WABT.
        """
        # Convert API to specific gravity and mass flow
        sg = 141.5 / (feed_api + 131.5)
        feed_density_kg_m3 = sg * 1000.0
        feed_mass_flow_kg_h = feed_flow_m3_h * feed_density_kg_m3
        
        # Recycle hydrogen gas mass flow
        # Treat gas at standard conditions: 1 Nm3 H2 mix ~= 0.08988 kg * (MW_mix / 2.016)
        mw_h2_mix = (recycle_h2_purity_pct / 100.0) * 2.016 + (1.0 - recycle_h2_purity_pct / 100.0) * 18.0
        gas_density_nm3 = mw_h2_mix / 22.414  # kg / Nm3
        recycle_gas_vol_nm3_h = feed_flow_m3_h * recycle_gas_ratio_nm3_m3
        recycle_gas_mass_kg_h = recycle_gas_vol_nm3_h * gas_density_nm3
        
        # Hydrogen partial pressure (bar)
        p_h2_bar = reactor_pressure_bar * (recycle_h2_purity_pct / 100.0)
        
        # Initial composition
        if feed_yields is None:
            # Typical VGO feed: 94% VGO, 5% heavy diesel tail, 1% others
            current_yields = np.array([0.94, 0.05, 0.01, 0.0, 0.0])
        else:
            current_yields = np.array(feed_yields, dtype=float)
            current_yields = current_yields / np.sum(current_yields)
            
        bed_results = []
        bed_temps = []
        total_h2_consumed_kg_h = 0.0
        
        current_inlet_t = reactor_inlet_temp_c
        current_oil_mass_kg_h = feed_mass_flow_kg_h
        current_gas_mass_kg_h = recycle_gas_mass_kg_h
        
        for b in range(self.num_beds):
            cat_vol_bed = self.total_catalyst_volume_m3 * self.bed_volume_fractions[b]
            cat_mass_bed = cat_vol_bed * self.catalyst_bulk_density
            
            # Space velocity (LHSV)
            lhsv_bed = feed_flow_m3_h / cat_vol_bed
            tau_bed_hr = 1.0 / max(0.01, lhsv_bed)
            
            # Subdivide bed into 10 axial numerical integration slices
            num_slices = 10
            d_tau = tau_bed_hr / num_slices
            slice_cat_mass = cat_mass_bed / num_slices
            
            t_slice = current_inlet_t
            y_slice = current_yields.copy()
            bed_h2_consumed_kg_h = 0.0
            
            # Nitrogen profile: Bed 1 hydrotreating removes ~75% of basic nitrogen
            eff_nitrogen = feed_nitrogen_ppm if b == 0 else feed_nitrogen_ppm * (0.25 ** b)
            
            for s in range(num_slices):
                # Kinetics at this slice
                dy_dt, h2_rate, n_factor = self.kinetics.compute_reaction_rates(
                    yields=y_slice,
                    T_celsius=t_slice,
                    P_h2_bar=p_h2_bar,
                    catalyst_activity=catalyst_activities[b],
                    feed_nitrogen_ppm=eff_nitrogen
                )
                
                # Update yields
                y_slice += dy_dt * d_tau
                y_slice = np.maximum(0.0, y_slice)
                y_slice /= np.sum(y_slice)
                
                # Hydrogen consumed in this slice (kg H2/hr)
                # h2_rate is in kg H2 / (kg oil * hr)
                delta_h2 = h2_rate * current_oil_mass_kg_h * d_tau
                bed_h2_consumed_kg_h += delta_h2
                
                # Exothermic heat release
                heat_released_w = (delta_h2 / (d_tau * 3600.0)) * self.kinetics.heat_of_reaction_H2
                
                # Flow thermal capacity (W / K)
                m_cp_oil = (current_oil_mass_kg_h / 3600.0) * self.cp_oil
                m_cp_gas = (current_gas_mass_kg_h / 3600.0) * self.cp_gas
                m_cp_total = m_cp_oil + m_cp_gas
                
                # Delta T across this slice
                delta_t = heat_released_w / max(100.0, m_cp_total) * (d_tau * 3600.0 / 3600.0)
                t_slice += delta_t
                
            t_outlet = t_slice
            delta_t_bed = t_outlet - current_inlet_t
            
            # Differential pressure across bed (bar) with fouling
            base_dp = self.base_dp_clean_bar[b]
            flow_ratio = feed_flow_m3_h / 200.0  # 200 m3/h baseline
            coke_factor = 1.0 + 0.08 * coke_wt_pct_per_bed[b]
            tos_fouling = 1.0 + 0.0007 * time_on_stream_days
            dp_bed = base_dp * (flow_ratio ** 1.8) * coke_factor * tos_fouling
            
            bed_temps.append((current_inlet_t, t_outlet))
            total_h2_consumed_kg_h += bed_h2_consumed_kg_h
            current_yields = y_slice
            
            bed_results.append({
                'bed_index': b + 1,
                'inlet_temp_c': current_inlet_t,
                'outlet_temp_c': t_outlet,
                'delta_t_c': delta_t_bed,
                'catalyst_activity': catalyst_activities[b],
                'coke_wt_pct': coke_wt_pct_per_bed[b],
                'dp_bar': dp_bed,
                'h2_consumed_kg_h': bed_h2_consumed_kg_h,
                'effective_nitrogen_ppm': eff_nitrogen
            })
            
            # Prepare inlet for next bed (apply interbed quench if not last bed)
            if b < self.num_beds - 1:
                q_flow_kg_h = quench_flows_kg_h[b]
                
                # Enthalpy mixing at quench box
                # Effluent stream before quench
                m_eff_oil = current_oil_mass_kg_h
                m_eff_gas = current_gas_mass_kg_h
                h_eff = (m_eff_oil * self.cp_oil + m_eff_gas * self.cp_gas) * t_outlet
                
                # Quench stream
                h_quench = q_flow_kg_h * self.cp_gas * self.quench_gas_temp_c
                
                # Combined stream
                m_tot_gas = m_eff_gas + q_flow_kg_h
                m_tot_cp = (m_eff_oil * self.cp_oil + m_tot_gas * self.cp_gas)
                
                next_inlet_t = (h_eff + h_quench) / m_tot_cp
                current_inlet_t = next_inlet_t
                current_gas_mass_kg_h = m_tot_gas
                
        # Calculate overall unit metrics
        wabt = self.calculate_wabt(bed_temps)
        total_dp_bar = sum(res['dp_bar'] for res in bed_results)
        
        # Net conversion of VGO (Lump 0)
        initial_vgo = feed_yields[0] if feed_yields is not None else 0.94
        vgo_conversion_pct = max(0.0, (initial_vgo - current_yields[0]) / initial_vgo * 100.0)
        
        # Chemical H2 consumption in wt% on feed and Nm3/m3
        h2_cons_wt_pct = (total_h2_consumed_kg_h / max(1.0, feed_mass_flow_kg_h)) * 100.0
        h2_cons_nm3_m3 = (total_h2_consumed_kg_h / 0.08988) / max(1.0, feed_flow_m3_h)
        
        # Product volumetric / mass flow rates
        product_mass_rates_t_h = {
            'VGO / UCO': current_yields[0] * feed_mass_flow_kg_h / 1000.0,
            'Diesel': current_yields[1] * feed_mass_flow_kg_h / 1000.0,
            'Kerosene / Jet': current_yields[2] * feed_mass_flow_kg_h / 1000.0,
            'Naphtha': current_yields[3] * feed_mass_flow_kg_h / 1000.0,
            'LPG / Gas': current_yields[4] * feed_mass_flow_kg_h / 1000.0,
        }
        
        return {
            'wabt_c': wabt,
            'total_dp_bar': total_dp_bar,
            'vgo_conversion_pct': vgo_conversion_pct,
            'h2_cons_wt_pct': h2_cons_wt_pct,
            'h2_cons_nm3_m3': h2_cons_nm3_m3,
            'final_yields': {
                'VGO / UCO': current_yields[0],
                'Diesel': current_yields[1],
                'Kerosene / Jet': current_yields[2],
                'Naphtha': current_yields[3],
                'LPG / Gas': current_yields[4]
            },
            'product_mass_rates_t_h': product_mass_rates_t_h,
            'bed_results': bed_results,
            'p_h2_bar': p_h2_bar,
            'feed_mass_flow_kg_h': feed_mass_flow_kg_h
        }
