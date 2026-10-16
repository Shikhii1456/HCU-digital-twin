"""
What-If Scenarios Definitions for Hydrocracking Unit Digital Twin
Provides standard industrial test cases and disturbances to stress-test reactor performance,
catalyst life, safety envelopes, and economic margins.
"""

SCENARIOS = {
    'normal': {
        'name': 'Normal Operation (Baseline Steady-State)',
        'description': 'Standard refinery operating conditions with nominal VGO feedstock and healthy catalyst.',
        'feed_flow_m3_h': 200.0,
        'feed_api': 22.0,
        'feed_nitrogen_ppm': 15.0,
        'reactor_inlet_temp_c': 378.0,
        'reactor_pressure_bar': 155.0,
        'recycle_gas_ratio_nm3_m3': 1400.0,
        'recycle_h2_purity_pct': 93.5,
        'quench_1_flow_kg_h': 3800.0,
        'quench_2_flow_kg_h': 4200.0,
        'time_on_stream_days': 120.0,
        'coke_per_bed': [3.5, 2.8, 2.2],
        'alert_notes': 'Stable operation within all safe operating limits (SOL).'
    },
    'nitrogen_slip': {
        'name': 'Feed Nitrogen Slip (Upstream Hydrotreater Breakthrough)',
        'description': 'Upstream pre-treat catalyst deactivates or slips nitrogen (15 ppm -> 130 ppm). Organic basic nitrogen blocks acidic cracking sites.',
        'feed_flow_m3_h': 200.0,
        'feed_api': 21.5,
        'feed_nitrogen_ppm': 130.0,
        'reactor_inlet_temp_c': 378.0,
        'reactor_pressure_bar': 155.0,
        'recycle_gas_ratio_nm3_m3': 1400.0,
        'recycle_h2_purity_pct': 93.0,
        'quench_1_flow_kg_h': 2400.0,
        'quench_2_flow_kg_h': 2600.0,
        'time_on_stream_days': 130.0,
        'coke_per_bed': [3.8, 3.0, 2.4],
        'alert_notes': 'WARNING: Severe acid site inhibition. Conversion slumps; operators will need to raise WABT sharply (+10-15°C) to compensate.'
    },
    'h2_purity_drop': {
        'name': 'Recycle Gas Purity Drop / Low H2 Partial Pressure',
        'description': 'PSA unit or hydrogen plant upset drops recycle gas purity from 93.5% to 80.0%, drastically lowering H2 partial pressure and accelerating coke buildup.',
        'feed_flow_m3_h': 200.0,
        'feed_api': 22.0,
        'feed_nitrogen_ppm': 18.0,
        'reactor_inlet_temp_c': 380.0,
        'reactor_pressure_bar': 150.0,
        'recycle_gas_ratio_nm3_m3': 1350.0,
        'recycle_h2_purity_pct': 80.0,
        'quench_1_flow_kg_h': 3600.0,
        'quench_2_flow_kg_h': 4000.0,
        'time_on_stream_days': 150.0,
        'coke_per_bed': [5.5, 4.8, 4.0],
        'alert_notes': 'ALERT: Low H2 partial pressure accelerates coking rate by >2.5x. Catalyst life is severely compromised.'
    },
    'quench_failure': {
        'name': 'Inter-Bed Quench Valve 2 Failure (Thermal Runaway Risk)',
        'description': 'Quench valve 2 sticks closed (flow drops from 4200 kg/h to 300 kg/h). Bed 3 inlet enters at unmitigated high temperature.',
        'feed_flow_m3_h': 200.0,
        'feed_api': 22.0,
        'feed_nitrogen_ppm': 15.0,
        'reactor_inlet_temp_c': 378.0,
        'reactor_pressure_bar': 155.0,
        'recycle_gas_ratio_nm3_m3': 1400.0,
        'recycle_h2_purity_pct': 93.5,
        'quench_1_flow_kg_h': 3800.0,
        'quench_2_flow_kg_h': 300.0,
        'time_on_stream_days': 120.0,
        'coke_per_bed': [3.5, 2.9, 2.8],
        'alert_notes': 'CRITICAL ALARM: Inter-bed quench starvation! Bed 3 temperature runaway hazard! Requires immediate emergency depressuring or feed cut.'
    },
    'heavy_feed': {
        'name': 'Heavy Opportunity Crude Switch (Low API / High Conradson Carbon)',
        'description': 'Refinery switches to heavy, aromatic feed blend (API drops from 22.0 to 16.5, higher polyaromatics and micro-carbon residue).',
        'feed_flow_m3_h': 190.0,
        'feed_api': 16.5,
        'feed_nitrogen_ppm': 45.0,
        'reactor_inlet_temp_c': 382.0,
        'reactor_pressure_bar': 155.0,
        'recycle_gas_ratio_nm3_m3': 1500.0,
        'recycle_h2_purity_pct': 92.0,
        'quench_1_flow_kg_h': 4200.0,
        'quench_2_flow_kg_h': 4600.0,
        'time_on_stream_days': 180.0,
        'coke_per_bed': [6.2, 5.1, 4.4],
        'alert_notes': 'NOTICE: Higher coke formation rate, increased chemical H2 consumption, and shifted product selectivity toward lighter boiling cuts.'
    },
    'high_throughput': {
        'name': 'High Throughput / Maximum Diesel Production Push',
        'description': 'Management increases fresh feed rate to 245 m3/h (+22.5%) and raises furnace temperature to 384°C to capitalize on high diesel crack spreads.',
        'feed_flow_m3_h': 245.0,
        'feed_api': 22.2,
        'feed_nitrogen_ppm': 14.0,
        'reactor_inlet_temp_c': 384.0,
        'reactor_pressure_bar': 160.0,
        'recycle_gas_ratio_nm3_m3': 1380.0,
        'recycle_h2_purity_pct': 93.5,
        'quench_1_flow_kg_h': 4800.0,
        'quench_2_flow_kg_h': 5400.0,
        'time_on_stream_days': 200.0,
        'coke_per_bed': [4.8, 4.0, 3.4],
        'alert_notes': 'CAUTION: Higher throughput increases bed Delta-P and raises WABT, shortening overall catalyst cycle length in exchange for higher daily margins.'
    }
}
