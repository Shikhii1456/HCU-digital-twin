"""
Hydrocracking Unit Digital Twin Dynamic Simulation Engine
Integrates reactor physics, kinetics, catalyst deactivation tracking, telemetry generation,
and economics calculations.
"""

import numpy as np
import pandas as pd
from models.reactor import HydrocrackingReactor
from models.deactivation import CatalystDeactivationModel

class HCUDigitalTwinEngine:
    def __init__(self):
        self.reactor = HydrocrackingReactor()
        self.deactivation = CatalystDeactivationModel()
        
        # Economic benchmark pricing ($/metric ton)
        self.prices = {
            'VGO_feed': 520.0,
            'Diesel': 880.0,
            'Kerosene / Jet': 820.0,
            'Naphtha': 650.0,
            'LPG / Gas': 430.0,
            'UCO': 535.0,
            'Hydrogen': 2200.0   # $2.20 / kg H2
        }
        
    def evaluate_state(
        self,
        feed_flow_m3_h,
        feed_api,
        feed_nitrogen_ppm,
        reactor_inlet_temp_c,
        reactor_pressure_bar,
        recycle_gas_ratio_nm3_m3,
        recycle_h2_purity_pct,
        quench_1_flow_kg_h,
        quench_2_flow_kg_h,
        time_on_stream_days=120.0,
        coke_per_bed=[3.5, 2.8, 2.2],
        sensor_noise=False
    ):
        """
        Evaluates one instant of HCU operational state.
        Returns comprehensive dictionary of process values, catalyst health,
        yields, economics, and DCS alarm statuses.
        """
        # Calculate catalyst activity for each bed based on coke and conditions
        cat_activities = []
        activity_breakdowns = []
        for b in range(3):
            # In bed 1, hydrotreating removes bulk nitrogen, subsequent beds see lower slip
            n_eff = feed_nitrogen_ppm if b == 0 else feed_nitrogen_ppm * (0.25 ** b)
            act, breakdown = self.deactivation.calculate_activity(
                coke_wt_pct=coke_per_bed[b],
                feed_nitrogen_ppm=n_eff,
                time_on_stream_days=time_on_stream_days
            )
            cat_activities.append(act)
            activity_breakdowns.append(breakdown)
            
        # Run multi-bed reactor integration
        quench_flows = [quench_1_flow_kg_h, quench_2_flow_kg_h]
        rx_out = self.reactor.simulate_reactor(
            feed_flow_m3_h=feed_flow_m3_h,
            feed_api=feed_api,
            feed_nitrogen_ppm=feed_nitrogen_ppm,
            reactor_inlet_temp_c=reactor_inlet_temp_c,
            reactor_pressure_bar=reactor_pressure_bar,
            recycle_gas_ratio_nm3_m3=recycle_gas_ratio_nm3_m3,
            recycle_h2_purity_pct=recycle_h2_purity_pct,
            quench_flows_kg_h=quench_flows,
            catalyst_activities=cat_activities,
            coke_wt_pct_per_bed=coke_per_bed,
            time_on_stream_days=time_on_stream_days
        )
        
        # Normalized WABT calculation
        norm_wabt = self.deactivation.calculate_normalized_wabt(
            actual_wabt_c=rx_out['wabt_c'],
            feed_api=feed_api,
            feed_nitrogen_ppm=feed_nitrogen_ppm
        )
        
        # Deactivation rate estimate (°C / month)
        # Empirical deactivation scaling based on current severity and H2 partial pressure
        p_h2 = rx_out['p_h2_bar']
        severity_ratio = (rx_out['wabt_c'] / 380.0) ** 3.0 * (140.0 / max(50.0, p_h2)) ** 1.5
        deact_rate_c_month = 1.35 * severity_ratio * (1.0 + 0.005 * max(0.0, feed_nitrogen_ppm - 15.0))
        
        # RUL estimation
        rul_info = self.deactivation.estimate_remaining_useful_life(
            current_wabt_c=rx_out['wabt_c'],
            deactivation_rate_c_per_month=deact_rate_c_month,
            current_total_dp_bar=rx_out['total_dp_bar']
        )
        
        # Economics calculation
        feed_mass_t_h = rx_out['feed_mass_flow_kg_h'] / 1000.0
        h2_cons_t_h = (rx_out['h2_cons_wt_pct'] / 100.0) * feed_mass_t_h
        
        feed_cost_hr = feed_mass_t_h * self.prices['VGO_feed']
        h2_cost_hr = h2_cons_t_h * self.prices['Hydrogen']
        total_opex_hr = feed_cost_hr + h2_cost_hr
        
        prod_revenue_hr = (
            rx_out['product_mass_rates_t_h']['Diesel'] * self.prices['Diesel'] +
            rx_out['product_mass_rates_t_h']['Kerosene / Jet'] * self.prices['Kerosene / Jet'] +
            rx_out['product_mass_rates_t_h']['Naphtha'] * self.prices['Naphtha'] +
            rx_out['product_mass_rates_t_h']['LPG / Gas'] * self.prices['LPG / Gas'] +
            rx_out['product_mass_rates_t_h']['VGO / UCO'] * self.prices['UCO']
        )
        
        gross_margin_hr = prod_revenue_hr - total_opex_hr
        gross_margin_day = gross_margin_hr * 24.0
        
        # Barrels per day (approx 6.5 bbl / m3 for VGO)
        feed_bpd = feed_flow_m3_h * 6.2898 * 24.0
        margin_per_bbl = gross_margin_day / max(1.0, feed_bpd)
        
        # Safety & Envelope Alarms
        alarms = []
        alarm_level = 'NORMAL'  # NORMAL, ADVISORY, WARNING, CRITICAL
        
        for b_res in rx_out['bed_results']:
            if b_res['delta_t_c'] > 32.0:
                alarms.append(f"Bed {b_res['bed_index']} High Exotherm (ΔT = {b_res['delta_t_c']:.1f}°C > 32°C)")
                alarm_level = 'WARNING' if alarm_level != 'CRITICAL' else 'CRITICAL'
            if b_res['outlet_temp_c'] > 425.0:
                alarms.append(f"Bed {b_res['bed_index']} High Outlet Temperature ({b_res['outlet_temp_c']:.1f}°C > 425°C) - Thermal Runaway Risk!")
                alarm_level = 'CRITICAL'
                
        if p_h2 < 115.0:
            alarms.append(f"Low Hydrogen Partial Pressure ({p_h2:.1f} bar < 115 bar) - Rapid Coking Warning!")
            if alarm_level != 'CRITICAL':
                alarm_level = 'WARNING'
                
        if feed_nitrogen_ppm > 45.0:
            alarms.append(f"High Feed Nitrogen ({feed_nitrogen_ppm:.0f} ppmw) - Acid Cracking Inhibition!")
            if alarm_level == 'NORMAL':
                alarm_level = 'ADVISORY'
                
        if rx_out['total_dp_bar'] > 7.5:
            alarms.append(f"High Reactor Differential Pressure ({rx_out['total_dp_bar']:.2f} bar > 7.5 bar)")
            if alarm_level != 'CRITICAL':
                alarm_level = 'WARNING'
                
        if rx_out['wabt_c'] > 418.0:
            alarms.append(f"Approaching EOR Metallurgy Limit (WABT = {rx_out['wabt_c']:.1f}°C)")
            if alarm_level != 'CRITICAL':
                alarm_level = 'WARNING'
                
        # Optional realistic sensor noise
        def add_noise(val, pct=0.3):
            if not sensor_noise:
                return val
            return val + np.random.normal(0, abs(val) * (pct / 100.0))
            
        # DCS Tagged Telemetry Packet
        dcs_telemetry = {
            'HCU_FC101.PV': add_noise(feed_flow_m3_h, 0.2),              # Feed flow (m3/h)
            'HCU_AI102.PV': add_noise(feed_api, 0.1),                     # Feed API
            'HCU_AI103.PV': add_noise(feed_nitrogen_ppm, 0.5),            # Feed Nitrogen (ppmw)
            'HCU_PC101.PV': add_noise(reactor_pressure_bar, 0.1),         # Reactor pressure (bar)
            'HCU_FC104.PV': add_noise(recycle_gas_ratio_nm3_m3, 0.3),     # Gas/oil ratio
            'HCU_AI105.PV': add_noise(recycle_h2_purity_pct, 0.2),        # H2 purity (%)
            'HCU_TC101.PV': add_noise(reactor_inlet_temp_c, 0.1),         # Bed 1 inlet (°C)
            'HCU_TI102.PV': add_noise(rx_out['bed_results'][0]['outlet_temp_c'], 0.1),
            'HCU_TI103.PV': add_noise(rx_out['bed_results'][1]['inlet_temp_c'], 0.1),
            'HCU_TI104.PV': add_noise(rx_out['bed_results'][1]['outlet_temp_c'], 0.1),
            'HCU_TI105.PV': add_noise(rx_out['bed_results'][2]['inlet_temp_c'], 0.1),
            'HCU_TI106.PV': add_noise(rx_out['bed_results'][2]['outlet_temp_c'], 0.1),
            'HCU_FC106.PV': add_noise(quench_1_flow_kg_h, 0.4),           # Quench 1 flow (kg/h)
            'HCU_FC107.PV': add_noise(quench_2_flow_kg_h, 0.4),           # Quench 2 flow (kg/h)
            'HCU_TI100.CALC': add_noise(rx_out['wabt_c'], 0.05),          # Actual WABT (°C)
            'HCU_TI100_NORM.CALC': norm_wabt,                              # Normalized WABT (°C)
            'HCU_PDI101.PV': add_noise(rx_out['bed_results'][0]['dp_bar'], 0.3),
            'HCU_PDI102.PV': add_noise(rx_out['bed_results'][1]['dp_bar'], 0.3),
            'HCU_PDI103.PV': add_noise(rx_out['bed_results'][2]['dp_bar'], 0.3),
            'HCU_PDI100.CALC': add_noise(rx_out['total_dp_bar'], 0.2),
            'HCU_XC101.CALC': rx_out['vgo_conversion_pct'],
            'HCU_FC110.CALC': rx_out['h2_cons_nm3_m3'],
            'HCU_CAT_ACT.CALC': np.mean(cat_activities),
            'HCU_COKE_AVG.CALC': np.mean(coke_per_bed),
            'HCU_RUL_DAYS.CALC': rul_info['rul_days'],
            'HCU_MARGIN_BBL.CALC': margin_per_bbl,
            'HCU_MARGIN_DAY.CALC': gross_margin_day
        }
        
        return {
            'reactor_output': rx_out,
            'normalized_wabt_c': norm_wabt,
            'deact_rate_c_month': deact_rate_c_month,
            'catalyst_activities': cat_activities,
            'activity_breakdowns': activity_breakdowns,
            'rul_info': rul_info,
            'economics': {
                'gross_margin_day': gross_margin_day,
                'margin_per_bbl': margin_per_bbl,
                'prod_revenue_hr': prod_revenue_hr,
                'total_opex_hr': total_opex_hr,
                'feed_cost_hr': feed_cost_hr,
                'h2_cost_hr': h2_cost_hr,
                'feed_bpd': feed_bpd
            },
            'alarms': alarms,
            'alarm_level': alarm_level,
            'dcs_telemetry': dcs_telemetry
        }

    def generate_dynamic_time_series(self, num_points=60, step_minutes=1.0, scenario_key='normal', disturbance=None):
        """
        Generates dynamic DCS time-series stream over time.
        Useful for continuous plotting and historical comparison.
        """
        from simulator.scenarios import SCENARIOS
        sc = SCENARIOS.get(scenario_key, SCENARIOS['normal'])
        
        records = []
        coke = list(sc['coke_per_bed'])
        time_days = sc['time_on_stream_days']
        
        f_flow = sc['feed_flow_m3_h']
        f_api = sc['feed_api']
        f_n = sc['feed_nitrogen_ppm']
        t_in = sc['reactor_inlet_temp_c']
        p_rx = sc['reactor_pressure_bar']
        q_ratio = sc['recycle_gas_ratio_nm3_m3']
        h2_pur = sc['recycle_h2_purity_pct']
        q1 = sc['quench_1_flow_kg_h']
        q2 = sc['quench_2_flow_kg_h']
        
        for step in range(num_points):
            t_min = step * step_minutes
            t_days_curr = time_days + (t_min / (24.0 * 60.0))
            
            # Inject disturbance at step >= 20 if requested
            if disturbance and step >= 20:
                if 'feed_nitrogen_ppm' in disturbance:
                    f_n = disturbance['feed_nitrogen_ppm']
                if 'recycle_h2_purity_pct' in disturbance:
                    h2_pur = disturbance['recycle_h2_purity_pct']
                if 'quench_2_flow_kg_h' in disturbance:
                    q2 = disturbance['quench_2_flow_kg_h']
                if 'feed_flow_m3_h' in disturbance:
                    f_flow = disturbance['feed_flow_m3_h']
                if 'reactor_inlet_temp_c' in disturbance:
                    t_in = disturbance['reactor_inlet_temp_c']
                    
            # Slowly evolve coke
            coking_rate = 0.0035 * (t_in / 380.0) ** 2.0
            for b in range(3):
                coke[b] += coking_rate * (step_minutes / (24.0 * 60.0))
                
            res = self.evaluate_state(
                feed_flow_m3_h=f_flow,
                feed_api=f_api,
                feed_nitrogen_ppm=f_n,
                reactor_inlet_temp_c=t_in,
                reactor_pressure_bar=p_rx,
                recycle_gas_ratio_nm3_m3=q_ratio,
                recycle_h2_purity_pct=h2_pur,
                quench_1_flow_kg_h=q1,
                quench_2_flow_kg_h=q2,
                time_on_stream_days=t_days_curr,
                coke_per_bed=coke,
                sensor_noise=True
            )
            
            row = {
                'timestamp_min': t_min,
                'feed_flow_m3_h': res['dcs_telemetry']['HCU_FC101.PV'],
                'feed_nitrogen_ppm': res['dcs_telemetry']['HCU_AI103.PV'],
                'h2_purity_pct': res['dcs_telemetry']['HCU_AI105.PV'],
                'h2_partial_p_bar': res['reactor_output']['p_h2_bar'],
                'bed1_in_t_c': res['dcs_telemetry']['HCU_TC101.PV'],
                'bed1_out_t_c': res['dcs_telemetry']['HCU_TI102.PV'],
                'bed2_in_t_c': res['dcs_telemetry']['HCU_TI103.PV'],
                'bed2_out_t_c': res['dcs_telemetry']['HCU_TI104.PV'],
                'bed3_in_t_c': res['dcs_telemetry']['HCU_TI105.PV'],
                'bed3_out_t_c': res['dcs_telemetry']['HCU_TI106.PV'],
                'wabt_c': res['dcs_telemetry']['HCU_TI100.CALC'],
                'wabt_norm_c': res['dcs_telemetry']['HCU_TI100_NORM.CALC'],
                'conversion_pct': res['dcs_telemetry']['HCU_XC101.CALC'],
                'h2_cons_nm3_m3': res['dcs_telemetry']['HCU_FC110.CALC'],
                'total_dp_bar': res['dcs_telemetry']['HCU_PDI100.CALC'],
                'cat_activity_avg': res['dcs_telemetry']['HCU_CAT_ACT.CALC'],
                'coke_avg_pct': res['dcs_telemetry']['HCU_COKE_AVG.CALC'],
                'rul_days': res['dcs_telemetry']['HCU_RUL_DAYS.CALC'],
                'margin_day_usd': res['dcs_telemetry']['HCU_MARGIN_DAY.CALC'],
                'margin_bbl_usd': res['dcs_telemetry']['HCU_MARGIN_BBL.CALC'],
                'alarm_level': res['alarm_level'],
                'yield_diesel_pct': res['reactor_output']['final_yields']['Diesel'] * 100.0,
                'yield_jet_pct': res['reactor_output']['final_yields']['Kerosene / Jet'] * 100.0,
                'yield_naphtha_pct': res['reactor_output']['final_yields']['Naphtha'] * 100.0,
                'yield_lpg_pct': res['reactor_output']['final_yields']['LPG / Gas'] * 100.0,
                'yield_uco_pct': res['reactor_output']['final_yields']['VGO / UCO'] * 100.0,
            }
            records.append(row)
            
        return pd.DataFrame(records)
