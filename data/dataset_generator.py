"""
Dataset Generator for HCU Digital Twin
Creates benchmark dynamic industrial datasets mimicking real-time DCS historians (OSIsoft PI / Honeywell PHD)
and long-term catalyst lifecycle data (SOR to EOR).
"""

import os
import numpy as np
import pandas as pd
from simulator.engine import HCUDigitalTwinEngine

def generate_industry_datasets(output_dir="data"):
    os.makedirs(output_dir, exist_ok=True)
    engine = HCUDigitalTwinEngine()
    
    print("Generating Dynamic Real-Time Industry DCS Telemetry Dataset (1440 minutes = 24 hours)...")
    # 24-hour minute-by-minute industrial DCS telemetry stream
    n_points = 1440
    records = []
    
    # Base operating parameters
    base_flow = 205.0           # m3/h
    base_api = 22.3             # °API
    base_n = 16.0               # ppmw
    base_tin = 378.5            # °C
    base_pres = 156.0           # bar
    base_treat = 1420.0         # Nm3/m3
    base_purity = 93.8          # mol% H2
    base_q1 = 3900.0            # kg/h
    base_q2 = 4300.0            # kg/h
    
    coke = [3.4, 2.7, 2.1]
    
    np.random.seed(42)
    
    for m in range(n_points):
        # Diurnal temperature cycle (quench inlet fluctuates slightly with ambient day/night)
        diurnal = 1.2 * np.sin(2 * np.pi * m / 1440.0)
        
        # Operational events:
        # Minute 400 - 600: Feed switch (heavier blend, API drops to 20.8, Nitrogen jumps to 38 ppm)
        # Minute 900 - 1050: Upstream hydrotreater transient (nitrogen spikes to 75 ppm)
        # Minute 1000: Operator trims WABT (+2.5°C) to recover conversion
        curr_flow = base_flow + np.random.normal(0, 0.8)
        curr_api = base_api
        curr_n = base_n
        curr_tin = base_tin + diurnal
        curr_purity = base_purity
        curr_q1 = base_q1
        curr_q2 = base_q2
        
        if 400 <= m < 600:
            curr_api -= 1.5
            curr_n += 22.0
            curr_flow -= 5.0
        elif 900 <= m < 1050:
            curr_n += 60.0
            if m >= 960:
                curr_tin += 2.8  # Operator response: raise furnace temperature
                curr_q1 += 250.0
                curr_q2 += 300.0
                
        # Coke slow evolution
        for b in range(3):
            coke[b] += 0.0035 / 1440.0
            
        res = engine.evaluate_state(
            feed_flow_m3_h=curr_flow,
            feed_api=curr_api,
            feed_nitrogen_ppm=curr_n,
            reactor_inlet_temp_c=curr_tin,
            reactor_pressure_bar=base_pres,
            recycle_gas_ratio_nm3_m3=base_treat,
            recycle_h2_purity_pct=curr_purity,
            quench_1_flow_kg_h=curr_q1,
            quench_2_flow_kg_h=curr_q2,
            time_on_stream_days=115.0 + (m / 1440.0),
            coke_per_bed=coke,
            sensor_noise=True
        )
        
        row = {
            'Minute': m,
            'Timestamp': pd.Timestamp('2026-10-16 00:00:00') + pd.Timedelta(minutes=m),
            # DCS Tags
            'HCU_FC101.PV': round(res['dcs_telemetry']['HCU_FC101.PV'], 2),             # Fresh Feed Flow (m3/h)
            'HCU_AI102.PV': round(res['dcs_telemetry']['HCU_AI102.PV'], 2),             # Feed API (°API)
            'HCU_AI103.PV': round(res['dcs_telemetry']['HCU_AI103.PV'], 1),             # Feed Nitrogen (ppmw)
            'HCU_PC101.PV': round(res['dcs_telemetry']['HCU_PC101.PV'], 2),             # Rx Pressure (bar)
            'HCU_FC104.PV': round(res['dcs_telemetry']['HCU_FC104.PV'], 1),             # Treat Gas Ratio (Nm3/m3)
            'HCU_AI105.PV': round(res['dcs_telemetry']['HCU_AI105.PV'], 2),             # H2 Purity (mol%)
            'HCU_TC101.PV': round(res['dcs_telemetry']['HCU_TC101.PV'], 2),             # Bed 1 In Temp (°C)
            'HCU_TI102.PV': round(res['dcs_telemetry']['HCU_TI102.PV'], 2),             # Bed 1 Out Temp (°C)
            'HCU_TI103.PV': round(res['dcs_telemetry']['HCU_TI103.PV'], 2),             # Bed 2 In Temp (°C)
            'HCU_TI104.PV': round(res['dcs_telemetry']['HCU_TI104.PV'], 2),             # Bed 2 Out Temp (°C)
            'HCU_TI105.PV': round(res['dcs_telemetry']['HCU_TI105.PV'], 2),             # Bed 3 In Temp (°C)
            'HCU_TI106.PV': round(res['dcs_telemetry']['HCU_TI106.PV'], 2),             # Bed 3 Out Temp (°C)
            'HCU_FC106.PV': round(res['dcs_telemetry']['HCU_FC106.PV'], 1),             # Quench 1 Flow (kg/h)
            'HCU_FC107.PV': round(res['dcs_telemetry']['HCU_FC107.PV'], 1),             # Quench 2 Flow (kg/h)
            'HCU_TI100.CALC': round(res['dcs_telemetry']['HCU_TI100.CALC'], 2),         # WABT (°C)
            'HCU_TI100_NORM.CALC': round(res['dcs_telemetry']['HCU_TI100_NORM.CALC'], 2),# Normalized WABT (°C)
            'HCU_PDI100.CALC': round(res['dcs_telemetry']['HCU_PDI100.CALC'], 3),       # Total Delta-P (bar)
            'HCU_XC101.CALC': round(res['dcs_telemetry']['HCU_XC101.CALC'], 2),         # VGO Conversion (%)
            'HCU_FC110.CALC': round(res['dcs_telemetry']['HCU_FC110.CALC'], 1),         # H2 Consumption (Nm3/m3)
            'HCU_CAT_ACT.CALC': round(res['dcs_telemetry']['HCU_CAT_ACT.CALC'], 4),     # Cat Activity (0-1)
            'HCU_COKE_AVG.CALC': round(res['dcs_telemetry']['HCU_COKE_AVG.CALC'], 2),   # Coke wt%
            'HCU_RUL_DAYS.CALC': round(res['dcs_telemetry']['HCU_RUL_DAYS.CALC'], 1),   # RUL Days
            'HCU_MARGIN_DAY.CALC': round(res['dcs_telemetry']['HCU_MARGIN_DAY.CALC'], 0), # Gross Margin $/day
            'HCU_ALARM_LEVEL': res['alarm_level'],
            'Yield_Diesel_pct': round(res['reactor_output']['final_yields']['Diesel'] * 100.0, 2),
            'Yield_Jet_pct': round(res['reactor_output']['final_yields']['Kerosene / Jet'] * 100.0, 2),
            'Yield_Naphtha_pct': round(res['reactor_output']['final_yields']['Naphtha'] * 100.0, 2),
            'Yield_LPG_pct': round(res['reactor_output']['final_yields']['LPG / Gas'] * 100.0, 2),
            'Yield_UCO_pct': round(res['reactor_output']['final_yields']['VGO / UCO'] * 100.0, 2)
        }
        records.append(row)
        
    df_telemetry = pd.DataFrame(records)
    telemetry_file = os.path.join(output_dir, "hcu_realtime_industry_telemetry.csv")
    df_telemetry.to_csv(telemetry_file, index=False)
    print(f"Saved: {telemetry_file} ({len(df_telemetry)} records)")
    
    # 2. Long-term catalyst cycle dataset (730 days = 2-year full run from SOR to EOR)
    print("Generating Long-Term Catalyst Lifecycle Dataset (730 days: SOR to EOR)...")
    lifecycle_records = []
    
    coke_sor = [0.8, 0.5, 0.4]
    current_coke = list(coke_sor)
    wabt_sor = 378.0
    current_tin = wabt_sor - 6.0
    
    for day in range(1, 731):
        # Gradual coking and aging
        deact_factor = 1.0 - 0.28 * (day / 730.0) ** 0.65
        for b in range(3):
            # Coke accumulation accelerates with higher days/temperatures
            current_coke[b] = min(16.0, coke_sor[b] + 9.5 * (day / 730.0) ** 0.75 + (b * 0.4))
            
        # Target constant conversion ~ 72%: operator raises inlet temperature to maintain conversion
        # Temperature increase ramp
        required_tin = (wabt_sor - 6.0) + 42.0 * ((day / 730.0) ** 0.85)
        
        res = engine.evaluate_state(
            feed_flow_m3_h=200.0,
            feed_api=22.0,
            feed_nitrogen_ppm=15.0,
            reactor_inlet_temp_c=required_tin,
            reactor_pressure_bar=155.0,
            recycle_gas_ratio_nm3_m3=1400.0,
            recycle_h2_purity_pct=93.5,
            quench_1_flow_kg_h=3800.0 + 1.2 * day,
            quench_2_flow_kg_h=4200.0 + 1.5 * day,
            time_on_stream_days=float(day),
            coke_per_bed=current_coke,
            sensor_noise=False
        )
        
        cycle_row = {
            'Day': day,
            'Time_On_Stream_Days': day,
            'Run_Phase': 'SOR' if day < 60 else ('MOR' if day < 550 else 'EOR'),
            'Bed1_Coke_wt_pct': round(current_coke[0], 2),
            'Bed2_Coke_wt_pct': round(current_coke[1], 2),
            'Bed3_Coke_wt_pct': round(current_coke[2], 2),
            'Average_Coke_wt_pct': round(np.mean(current_coke), 2),
            'Catalyst_Activity_Factor': round(np.mean(res['catalyst_activities']), 4),
            'Actual_WABT_c': round(res['reactor_output']['wabt_c'], 2),
            'Normalized_WABT_c': round(res['normalized_wabt_c'], 2),
            'EOR_WABT_Limit_c': 425.0,
            'WABT_Headroom_c': round(max(0.0, 425.0 - res['reactor_output']['wabt_c']), 2),
            'Total_Reactor_DeltaP_bar': round(res['reactor_output']['total_dp_bar'], 3),
            'Bed1_DeltaP_bar': round(res['reactor_output']['bed_results'][0]['dp_bar'], 3),
            'VGO_Conversion_pct': round(res['reactor_output']['vgo_conversion_pct'], 2),
            'H2_Consumption_wt_pct': round(res['reactor_output']['h2_cons_wt_pct'], 2),
            'Diesel_Yield_pct': round(res['reactor_output']['final_yields']['Diesel'] * 100.0, 2),
            'Kero_Jet_Yield_pct': round(res['reactor_output']['final_yields']['Kerosene / Jet'] * 100.0, 2),
            'Naphtha_Yield_pct': round(res['reactor_output']['final_yields']['Naphtha'] * 100.0, 2),
            'LPG_Gas_Yield_pct': round(res['reactor_output']['final_yields']['LPG / Gas'] * 100.0, 2),
            'UCO_Yield_pct': round(res['reactor_output']['final_yields']['VGO / UCO'] * 100.0, 2),
            'RUL_Days_Projected': round(res['rul_info']['rul_days'], 1),
            'Daily_Gross_Margin_USD': round(res['economics']['gross_margin_day'], 0)
        }
        lifecycle_records.append(cycle_row)
        
    df_cycle = pd.DataFrame(lifecycle_records)
    cycle_file = os.path.join(output_dir, "hcu_catalyst_run_lifecycle.csv")
    df_cycle.to_csv(cycle_file, index=False)
    print(f"Saved: {cycle_file} ({len(df_cycle)} records)")
    print("Dataset generation complete!")

if __name__ == "__main__":
    generate_industry_datasets("C:/Users/OMEN/.gemini/antigravity/scratch/hcu_digital_twin/data")
