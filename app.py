"""
Hydrocracking Unit (HCU) Digital Twin - Interactive Streamlit Dashboard
Industrial Digital Twin for Process Monitoring, Catalyst Deactivation Tracking,
Dynamic Telemetry Visualization, and 'What-If' Scenario Stress Testing.
"""

import os
import sys
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure current directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from simulator.engine import HCUDigitalTwinEngine
from simulator.scenarios import SCENARIOS

# Streamlit Page Configuration
st.set_page_config(
    page_title="HCU Digital Twin | Catalyst Health & 'What-If' Sandbox",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for industrial high-tech styling
st.markdown("""
<style>
    .main { background-color: #0d1117; }
    .stMetric {
        background: #161b22;
        border: 1px solid #30363d;
        padding: 12px 18px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .status-card {
        padding: 14px 20px;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 16px;
    }
    .status-normal { background-color: rgba(46, 160, 67, 0.15); border: 1px solid #2ea043; color: #3fb950; }
    .status-advisory { background-color: rgba(210, 153, 34, 0.15); border: 1px solid #d29922; color: #e3b341; }
    .status-warning { background-color: rgba(219, 109, 40, 0.2); border: 1px solid #db6d28; color: #f0883e; }
    .status-critical { background-color: rgba(248, 81, 73, 0.2); border: 1px solid #f85149; color: #ff7b72; animation: blinker 1.5s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.6; } }
    .reactor-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Engine
@st.cache_resource
def get_engine():
    return HCUDigitalTwinEngine()

engine = get_engine()

# Load Datasets
@st.cache_data
def load_datasets():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    telemetry_path = os.path.join(data_dir, "hcu_realtime_industry_telemetry.csv")
    lifecycle_path = os.path.join(data_dir, "hcu_catalyst_run_lifecycle.csv")
    
    df_tel = pd.read_csv(telemetry_path) if os.path.exists(telemetry_path) else None
    df_life = pd.read_csv(lifecycle_path) if os.path.exists(lifecycle_path) else None
    return df_tel, df_life

df_telemetry_hist, df_lifecycle_hist = load_datasets()

# ----------------- SIDEBAR CONTROLS -----------------
st.sidebar.image("https://img.icons8.com/fluency/96/refinery.png", width=64)
st.sidebar.title("HCU Digital Twin")
st.sidebar.caption("Hydrocracking Unit Virtual Replica & Catalyst Optimizer")

nav_choice = st.sidebar.radio(
    "Navigation Mode",
    ["🎛️ Digital Twin Cockpit", "🔮 'What-If' Scenario Sandbox", "📈 Real-Time DCS Telemetry", "🧬 Catalyst Lifecycle & Degradation", "📁 Data Export & API"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🕹️ Simulation Baseline Preset")
preset_name = st.sidebar.selectbox(
    "Select Operating Preset",
    list(SCENARIOS.keys()),
    format_func=lambda x: SCENARIOS[x]['name']
)
preset = SCENARIOS[preset_name]

# Global slider overrides in sidebar
with st.sidebar.expander("⚙️ Process Variables Override", expanded=False):
    feed_flow = st.slider("Fresh Feed Rate (m³/h)", 120.0, 300.0, float(preset['feed_flow_m3_h']), 5.0)
    feed_api = st.slider("Feed API Gravity (°API)", 15.0, 28.0, float(preset['feed_api']), 0.5)
    feed_nitrogen = st.slider("Feed Nitrogen (ppmw)", 5.0, 250.0, float(preset['feed_nitrogen_ppm']), 5.0)
    furnace_temp = st.slider("Furnace Outlet Temp (°C)", 360.0, 420.0, float(preset['reactor_inlet_temp_c']), 0.5)
    rx_pressure = st.slider("Reactor Total Pressure (bar)", 120.0, 185.0, float(preset['reactor_pressure_bar']), 1.0)
    h2_ratio = st.slider("Recycle Gas/Oil Ratio (Nm³/m³)", 900.0, 2000.0, float(preset['recycle_gas_ratio_nm3_m3']), 50.0)
    h2_purity = st.slider("Recycle H₂ Purity (mol%)", 75.0, 99.0, float(preset['recycle_h2_purity_pct']), 0.5)
    quench_1 = st.slider("Quench 1 Flow (kg/h)", 0.0, 8000.0, float(preset['quench_1_flow_kg_h']), 100.0)
    quench_2 = st.slider("Quench 2 Flow (kg/h)", 0.0, 8000.0, float(preset['quench_2_flow_kg_h']), 100.0)
    tos_days = st.slider("Time on Stream (Days)", 1.0, 750.0, float(preset['time_on_stream_days']), 5.0)

# Evaluate Current State
current_coke = list(preset['coke_per_bed'])
# Scale coke with TOS
coke_scaled = [min(16.0, c * (1.0 + 0.0015 * max(0.0, tos_days - preset['time_on_stream_days']))) for c in current_coke]

eval_state = engine.evaluate_state(
    feed_flow_m3_h=feed_flow,
    feed_api=feed_api,
    feed_nitrogen_ppm=feed_nitrogen,
    reactor_inlet_temp_c=furnace_temp,
    reactor_pressure_bar=rx_pressure,
    recycle_gas_ratio_nm3_m3=h2_ratio,
    recycle_h2_purity_pct=h2_purity,
    quench_1_flow_kg_h=quench_1,
    quench_2_flow_kg_h=quench_2,
    time_on_stream_days=tos_days,
    coke_per_bed=coke_scaled,
    sensor_noise=True
)

dcs = eval_state['dcs_telemetry']
rx = eval_state['reactor_output']
rul = eval_state['rul_info']
econ = eval_state['economics']
alarm_lvl = eval_state['alarm_level']
alarms = eval_state['alarms']

# ==============================================================================
# 1. DIGITAL TWIN COCKPIT
# ==============================================================================
if nav_choice == "🎛️ Digital Twin Cockpit":
    st.title("🎛️ Hydrocracking Unit (HCU) Real-Time Digital Twin")
    st.markdown(f"**Operating Mode:** `{preset['name']}` | **TOS:** `{tos_days:.0f} Days`")
    
    # Process Alarm / Health Banner
    status_class = {
        'NORMAL': 'status-normal',
        'ADVISORY': 'status-advisory',
        'WARNING': 'status-warning',
        'CRITICAL': 'status-critical'
    }.get(alarm_lvl, 'status-normal')
    
    status_msg = f"🟢 STATUS: {alarm_lvl} — All operating parameters within safe envelopes." if alarm_lvl == 'NORMAL' else f"⚠️ STATUS: {alarm_lvl} — {', '.join(alarms)}"
    st.markdown(f"<div class='status-card {status_class}'>{status_msg}</div>", unsafe_allow_html=True)
    
    # High-level KPI Metric Cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Fresh Feed Flow", f"{dcs['HCU_FC101.PV']:.1f} m³/h", f"{econ['feed_bpd']:,.0f} BPD")
    c2.metric("Weighted Bed Temp (WABT)", f"{dcs['HCU_TI100.CALC']:.1f} °C", f"Limit: 425 °C")
    c3.metric("VGO Net Conversion", f"{dcs['HCU_XC101.CALC']:.1f} %", "Target: 70-75%")
    c4.metric("Catalyst Activity (a)", f"{dcs['HCU_CAT_ACT.CALC']:.3f}", f"SOR = 1.000")
    c5.metric("Remaining Useful Life (RUL)", f"{rul['rul_months']:.1f} mo", f"{rul['rul_days']:.0f} Days")
    c6.metric("Daily Gross Margin", f"${econ['gross_margin_day']:,.0f}", f"${econ['margin_per_bbl']:.2f}/bbl")
    
    st.markdown("### 🏭 Multi-Bed Reactor Thermal & Flow Profile")
    
    # Visual Bed Architecture Columns
    b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns([1.2, 0.4, 1.2, 0.4, 1.2])
    
    with b_col1:
        st.markdown(f"""
        <div class='reactor-box'>
            <h4 style='color:#58a6ff; margin:0;'>BED 1 (Pre-treat & HDN)</h4>
            <p style='font-size:12px; color:#8b949e;'>Cat Vol: 28% | trilobe NiMo</p>
            <div style='font-size:18px; font-weight:bold; margin:8px 0;'>
                Tin: {rx['bed_results'][0]['inlet_temp_c']:.1f}°C ➔ Tout: {rx['bed_results'][0]['outlet_temp_c']:.1f}°C
            </div>
            <p style='color:#e3b341; margin:0;'>ΔT Exotherm: +{rx['bed_results'][0]['delta_t_c']:.1f} °C</p>
            <p style='margin:4px 0 0 0;'>ΔP: {rx['bed_results'][0]['dp_bar']:.2f} bar | Coke: {rx['bed_results'][0]['coke_wt_pct']:.1f} wt%</p>
            <p style='margin:0; font-size:12px; color:#8b949e;'>Activity: {rx['bed_results'][0]['catalyst_activity']:.3f}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with b_col2:
        st.markdown(f"""
        <div style='text-align:center; padding-top:40px;'>
            <div style='color:#3fb950; font-size:24px;'>➔</div>
            <div style='font-size:11px; color:#58a6ff;'>Quench 1</div>
            <div style='font-weight:bold;'>{quench_1:.0f} kg/h</div>
            <div style='font-size:10px; color:#8b949e;'>@ 55°C H₂</div>
        </div>
        """, unsafe_allow_html=True)
        
    with b_col3:
        st.markdown(f"""
        <div class='reactor-box'>
            <h4 style='color:#58a6ff; margin:0;'>BED 2 (Main Cracking)</h4>
            <p style='font-size:12px; color:#8b949e;'>Cat Vol: 36% | Zeolite/NiW</p>
            <div style='font-size:18px; font-weight:bold; margin:8px 0;'>
                Tin: {rx['bed_results'][1]['inlet_temp_c']:.1f}°C ➔ Tout: {rx['bed_results'][1]['outlet_temp_c']:.1f}°C
            </div>
            <p style='color:#e3b341; margin:0;'>ΔT Exotherm: +{rx['bed_results'][1]['delta_t_c']:.1f} °C</p>
            <p style='margin:4px 0 0 0;'>ΔP: {rx['bed_results'][1]['dp_bar']:.2f} bar | Coke: {rx['bed_results'][1]['coke_wt_pct']:.1f} wt%</p>
            <p style='margin:0; font-size:12px; color:#8b949e;'>Activity: {rx['bed_results'][1]['catalyst_activity']:.3f}</p>
        </div>
        """, unsafe_allow_html=True)

    with b_col4:
        st.markdown(f"""
        <div style='text-align:center; padding-top:40px;'>
            <div style='color:#3fb950; font-size:24px;'>➔</div>
            <div style='font-size:11px; color:#58a6ff;'>Quench 2</div>
            <div style='font-weight:bold;'>{quench_2:.0f} kg/h</div>
            <div style='font-size:10px; color:#8b949e;'>@ 55°C H₂</div>
        </div>
        """, unsafe_allow_html=True)

    with b_col5:
        st.markdown(f"""
        <div class='reactor-box'>
            <h4 style='color:#58a6ff; margin:0;'>BED 3 (Finishing Cracking)</h4>
            <p style='font-size:12px; color:#8b949e;'>Cat Vol: 36% | High Selectivity</p>
            <div style='font-size:18px; font-weight:bold; margin:8px 0;'>
                Tin: {rx['bed_results'][2]['inlet_temp_c']:.1f}°C ➔ Tout: {rx['bed_results'][2]['outlet_temp_c']:.1f}°C
            </div>
            <p style='color:#e3b341; margin:0;'>ΔT Exotherm: +{rx['bed_results'][2]['delta_t_c']:.1f} °C</p>
            <p style='margin:4px 0 0 0;'>ΔP: {rx['bed_results'][2]['dp_bar']:.2f} bar | Coke: {rx['bed_results'][2]['coke_wt_pct']:.1f} wt%</p>
            <p style='margin:0; font-size:12px; color:#8b949e;'>Activity: {rx['bed_results'][2]['catalyst_activity']:.3f}</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Charts: Axial Temperature Profile & Product Yield Distribution
    ch1, ch2 = st.columns([1.2, 1.0])
    
    with ch1:
        st.subheader("🌡️ Reactor Axial Temperature & Quench Trajectory")
        z_pts = [0, 0.28, 0.28, 0.64, 0.64, 1.0]
        t_pts = [
            rx['bed_results'][0]['inlet_temp_c'],
            rx['bed_results'][0]['outlet_temp_c'],
            rx['bed_results'][1]['inlet_temp_c'],
            rx['bed_results'][1]['outlet_temp_c'],
            rx['bed_results'][2]['inlet_temp_c'],
            rx['bed_results'][2]['outlet_temp_c']
        ]
        
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=z_pts, y=t_pts, mode='lines+markers',
            name='Reactor Temp Profile',
            line=dict(color='#ff7b72', width=3),
            marker=dict(size=8, color='#f0883e')
        ))
        fig_temp.add_hline(y=425.0, line_dash='dash', line_color='#ff0000', annotation_text='EOR Safety Metallurgy Limit (425°C)')
        fig_temp.add_hline(y=eval_state['normalized_wabt_c'], line_dash='dot', line_color='#58a6ff', annotation_text=f"Normalized WABT ({eval_state['normalized_wabt_c']:.1f}°C)")
        
        fig_temp.update_layout(
            template='plotly_dark',
            xaxis_title='Normalized Reactor Bed Depth (z / L)',
            yaxis_title='Temperature (°C)',
            height=360,
            margin=dict(l=40, r=40, t=30, b=40)
        )
        st.plotly_chart(fig_temp, use_container_width=True)
        
    with ch2:
        st.subheader("⚖️ Product Yield Slates & Selectivity")
        yields = rx['final_yields']
        yield_df = pd.DataFrame({
            'Product': list(yields.keys()),
            'Yield (wt%)': [v * 100.0 for v in yields.values()],
            'Production (t/h)': [rx['product_mass_rates_t_h'][k] for k in yields.keys()]
        })
        
        colors = ['#8b949e', '#2ea043', '#58a6ff', '#e3b341', '#f0883e']
        fig_yield = px.pie(
            yield_df, names='Product', values='Yield (wt%)',
            color='Product',
            color_discrete_sequence=colors,
            hole=0.45
        )
        fig_yield.update_traces(textposition='inside', textinfo='percent+label')
        fig_yield.update_layout(
            template='plotly_dark',
            height=360,
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_yield, use_container_width=True)

# ==============================================================================
# 2. 'WHAT-IF' SCENARIO SANDBOX
# ==============================================================================
elif nav_choice == "🔮 'What-If' Scenario Sandbox":
    st.title("🔮 'What-If' Operational Scenario & Stress Tester")
    st.markdown("""
    Use this sandbox to inject process upsets, test feed quality variations, or evaluate operator strategies.
    The twin calculates real-time **deviations from nominal baseline**, showing safety hazards, RUL impacts, and margin shifts.
    """)
    
    # Baseline Scenario (Normal)
    baseline_params = SCENARIOS['normal']
    base_res = engine.evaluate_state(
        feed_flow_m3_h=baseline_params['feed_flow_m3_h'],
        feed_api=baseline_params['feed_api'],
        feed_nitrogen_ppm=baseline_params['feed_nitrogen_ppm'],
        reactor_inlet_temp_c=baseline_params['reactor_inlet_temp_c'],
        reactor_pressure_bar=baseline_params['reactor_pressure_bar'],
        recycle_gas_ratio_nm3_m3=baseline_params['recycle_gas_ratio_nm3_m3'],
        recycle_h2_purity_pct=baseline_params['recycle_h2_purity_pct'],
        quench_1_flow_kg_h=baseline_params['quench_1_flow_kg_h'],
        quench_2_flow_kg_h=baseline_params['quench_2_flow_kg_h'],
        time_on_stream_days=baseline_params['time_on_stream_days'],
        coke_per_bed=baseline_params['coke_per_bed'],
        sensor_noise=False
    )
    
    st.subheader("⚡ Quick Inject Industrial Disturbance Scenario")
    sc_select = st.selectbox(
        "Load Preset Disturbance Case",
        list(SCENARIOS.keys()),
        format_func=lambda k: f"{SCENARIOS[k]['name']}"
    )
    sc_data = SCENARIOS[sc_select]
    st.info(f"**Scenario Context:** {sc_data['description']}\n\n**Refinery Note:** {sc_data['alert_notes']}")
    
    with st.expander("🛠️ Fine-tune Disturbance Parameters", expanded=True):
        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            w_flow = st.number_input("What-If Feed Flow (m³/h)", 100.0, 350.0, float(sc_data['feed_flow_m3_h']), 5.0)
            w_api = st.number_input("What-If Feed API", 14.0, 30.0, float(sc_data['feed_api']), 0.5)
            w_nitrogen = st.number_input("What-If Feed Nitrogen (ppmw)", 5.0, 300.0, float(sc_data['feed_nitrogen_ppm']), 5.0)
        with col_w2:
            w_tin = st.number_input("What-If Furnace Inlet Temp (°C)", 350.0, 430.0, float(sc_data['reactor_inlet_temp_c']), 0.5)
            w_pres = st.number_input("What-If Rx Pressure (bar)", 100.0, 200.0, float(sc_data['reactor_pressure_bar']), 1.0)
            w_purity = st.number_input("What-If H₂ Purity (mol%)", 70.0, 99.0, float(sc_data['recycle_h2_purity_pct']), 0.5)
        with col_w3:
            w_q1 = st.number_input("What-If Quench 1 Flow (kg/h)", 0.0, 10000.0, float(sc_data['quench_1_flow_kg_h']), 100.0)
            w_q2 = st.number_input("What-If Quench 2 Flow (kg/h)", 0.0, 10000.0, float(sc_data['quench_2_flow_kg_h']), 100.0)
            w_tos = st.number_input("What-If TOS Days", 1.0, 800.0, float(sc_data['time_on_stream_days']), 10.0)
            
    # Run What-If Simulation
    whatif_res = engine.evaluate_state(
        feed_flow_m3_h=w_flow,
        feed_api=w_api,
        feed_nitrogen_ppm=w_nitrogen,
        reactor_inlet_temp_c=w_tin,
        reactor_pressure_bar=w_pres,
        recycle_gas_ratio_nm3_m3=sc_data['recycle_gas_ratio_nm3_m3'],
        recycle_h2_purity_pct=w_purity,
        quench_1_flow_kg_h=w_q1,
        quench_2_flow_kg_h=w_q2,
        time_on_stream_days=w_tos,
        coke_per_bed=sc_data['coke_per_bed'],
        sensor_noise=False
    )
    
    # Deviation Analytics Summary
    st.markdown("### 📊 Baseline vs. 'What-If' Deviation Matrix")
    
    d1, d2, d3, d4, d5 = st.columns(5)
    
    # Delta calculations
    delta_wabt = whatif_res['reactor_output']['wabt_c'] - base_res['reactor_output']['wabt_c']
    delta_conv = whatif_res['reactor_output']['vgo_conversion_pct'] - base_res['reactor_output']['vgo_conversion_pct']
    delta_act = np.mean(whatif_res['catalyst_activities']) - np.mean(base_res['catalyst_activities'])
    delta_rul = whatif_res['rul_info']['rul_days'] - base_res['rul_info']['rul_days']
    delta_margin = whatif_res['economics']['gross_margin_day'] - base_res['economics']['gross_margin_day']
    
    d1.metric(
        "WABT (°C)",
        f"{whatif_res['reactor_output']['wabt_c']:.1f} °C",
        f"{delta_wabt:+.1f} °C vs Base",
        delta_color="inverse"
    )
    d2.metric(
        "VGO Conversion",
        f"{whatif_res['reactor_output']['vgo_conversion_pct']:.1f} %",
        f"{delta_conv:+.1f} % vs Base"
    )
    d3.metric(
        "Catalyst Activity",
        f"{np.mean(whatif_res['catalyst_activities']):.3f}",
        f"{delta_act:+.3f} vs Base"
    )
    d4.metric(
        "RUL Projection",
        f"{whatif_res['rul_info']['rul_days']:.0f} Days",
        f"{delta_rul:+.0f} Days",
        delta_color="normal"
    )
    d5.metric(
        "Daily Gross Margin",
        f"${whatif_res['economics']['gross_margin_day']:,.0f}",
        f"${delta_margin:+,.0f}/day"
    )
    
    # Side-by-Side Comparison Plots
    tab_comp1, tab_comp2 = st.tabs(["🌡️ Temperature & Pressure Profiles", "💰 Product Yields & Margins"])
    
    with tab_comp1:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.subheader("Bed Outlet Temperatures Comparison")
            bed_labels = ["Bed 1", "Bed 2", "Bed 3"]
            base_touts = [b['outlet_temp_c'] for b in base_res['reactor_output']['bed_results']]
            whatif_touts = [b['outlet_temp_c'] for b in whatif_res['reactor_output']['bed_results']]
            
            fig_beds = go.Figure(data=[
                go.Bar(name='Baseline (Normal)', x=bed_labels, y=base_touts, marker_color='#2ea043'),
                go.Bar(name='What-If Disturbance', x=bed_labels, y=whatif_touts, marker_color='#f0883e')
            ])
            fig_beds.add_hline(y=425.0, line_dash='dash', line_color='#ff0000', annotation_text='Limit: 425°C')
            fig_beds.update_layout(template='plotly_dark', barmode='group', height=360, yaxis_title='Outlet Temp (°C)')
            st.plotly_chart(fig_beds, use_container_width=True)
            
        with col_p2:
            st.subheader("Differential Pressure & Fouling Comparison")
            base_dps = [b['dp_bar'] for b in base_res['reactor_output']['bed_results']]
            whatif_dps = [b['dp_bar'] for b in whatif_res['reactor_output']['bed_results']]
            
            fig_dp = go.Figure(data=[
                go.Bar(name='Baseline (Normal)', x=bed_labels, y=base_dps, marker_color='#58a6ff'),
                go.Bar(name='What-If Disturbance', x=bed_labels, y=whatif_dps, marker_color='#e3b341')
            ])
            fig_dp.update_layout(template='plotly_dark', barmode='group', height=360, yaxis_title='Differential Pressure (bar)')
            st.plotly_chart(fig_dp, use_container_width=True)

    with tab_comp2:
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            st.subheader("Product Yield Shift (wt%)")
            lumps = ['Diesel', 'Kerosene / Jet', 'Naphtha', 'LPG / Gas', 'VGO / UCO']
            base_y = [base_res['reactor_output']['final_yields'][l] * 100.0 for l in lumps]
            whatif_y = [whatif_res['reactor_output']['final_yields'][l] * 100.0 for l in lumps]
            
            fig_ys = go.Figure(data=[
                go.Bar(name='Baseline', x=lumps, y=base_y, marker_color='#2ea043'),
                go.Bar(name='What-If', x=lumps, y=whatif_y, marker_color='#f0883e')
            ])
            fig_ys.update_layout(template='plotly_dark', barmode='group', height=360, yaxis_title='Yield (wt%)')
            st.plotly_chart(fig_ys, use_container_width=True)
            
        with col_y2:
            st.subheader("Economic Sensitivity & Margin Delta")
            econ_categories = ['Feed Cost', 'H₂ Cost', 'Diesel Revenue', 'Jet Revenue', 'Net Margin']
            base_ec = [
                -base_res['economics']['feed_cost_hr'] * 24 / 1000,
                -base_res['economics']['h2_cost_hr'] * 24 / 1000,
                base_res['reactor_output']['product_mass_rates_t_h']['Diesel'] * 880 * 24 / 1000,
                base_res['reactor_output']['product_mass_rates_t_h']['Kerosene / Jet'] * 820 * 24 / 1000,
                base_res['economics']['gross_margin_day'] / 1000
            ]
            whatif_ec = [
                -whatif_res['economics']['feed_cost_hr'] * 24 / 1000,
                -whatif_res['economics']['h2_cost_hr'] * 24 / 1000,
                whatif_res['reactor_output']['product_mass_rates_t_h']['Diesel'] * 880 * 24 / 1000,
                whatif_res['reactor_output']['product_mass_rates_t_h']['Kerosene / Jet'] * 820 * 24 / 1000,
                whatif_res['economics']['gross_margin_day'] / 1000
            ]
            fig_ec = go.Figure(data=[
                go.Bar(name='Baseline ($k/day)', x=econ_categories, y=base_ec, marker_color='#58a6ff'),
                go.Bar(name='What-If ($k/day)', x=econ_categories, y=whatif_ec, marker_color='#a371f7')
            ])
            fig_ec.update_layout(template='plotly_dark', barmode='group', height=360, yaxis_title='$k / day')
            st.plotly_chart(fig_ec, use_container_width=True)

# ==============================================================================
# 3. REAL-TIME DCS TELEMETRY
# ==============================================================================
elif nav_choice == "📈 Real-Time DCS Telemetry":
    st.title("📈 Real-Time DCS Telemetry Stream & Plant Historian")
    st.markdown("""
    This module presents simulated dynamic plant telemetry streaming at 1-minute intervals matching
    real-time industrial historians (e.g. OSIsoft PI, Honeywell Uniformance PHD, Aspen InfoPlus.21).
    """)
    
    if df_telemetry_hist is not None:
        st.subheader("⏱️ Historian Dynamic Playback Scrubber")
        step_idx = st.slider("Select Telemetry Timeline Minute (0 to 1439)", 0, len(df_telemetry_hist)-1, 450)
        curr_row = df_telemetry_hist.iloc[step_idx]
        
        # Real-time Tag Display
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("HCU_FC101.PV (Feed)", f"{curr_row['HCU_FC101.PV']:.1f} m³/h")
        m2.metric("HCU_TI100.CALC (WABT)", f"{curr_row['HCU_TI100.CALC']:.1f} °C")
        m3.metric("HCU_XC101.CALC (Conv)", f"{curr_row['HCU_XC101.CALC']:.1f} %")
        m4.metric("HCU_AI103.PV (Nitrogen)", f"{curr_row['HCU_AI103.PV']:.0f} ppmw")
        m5.metric("HCU_PDI100.CALC (ΔP)", f"{curr_row['HCU_PDI100.CALC']:.2f} bar")
        
        # Dynamic Time-Series Plots
        st.subheader("📊 Multi-Tag Trend View")
        trend_tags = st.multiselect(
            "Select DCS Tags to Plot",
            [
                'HCU_FC101.PV', 'HCU_TI100.CALC', 'HCU_TI100_NORM.CALC',
                'HCU_AI103.PV', 'HCU_XC101.CALC', 'HCU_PDI100.CALC',
                'HCU_CAT_ACT.CALC', 'HCU_MARGIN_DAY.CALC'
            ],
            default=['HCU_TI100.CALC', 'HCU_TI100_NORM.CALC', 'HCU_AI103.PV']
        )
        
        if trend_tags:
            fig_hist = make_subplots(specs=[[{"secondary_y": True}]])
            for tag in trend_tags:
                is_secondary = 'Nitrogen' in tag or 'FC101' in tag or 'MARGIN' in tag or 'XC101' in tag
                fig_hist.add_trace(
                    go.Scatter(x=df_telemetry_hist['Minute'], y=df_telemetry_hist[tag], name=tag),
                    secondary_y=is_secondary
                )
            fig_hist.add_vline(x=step_idx, line_dash='dash', line_color='#ff7b72', annotation_text='Playback Cursor')
            fig_hist.update_layout(
                template='plotly_dark',
                height=420,
                xaxis_title='Timeline (Minutes)',
                hovermode='x unified'
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with st.expander("📄 View Raw Telemetry Data Window"):
            st.dataframe(df_telemetry_hist.iloc[max(0, step_idx-10):step_idx+10], use_container_width=True)
    else:
        st.warning("Telemetry dataset not found. Generating now...")
        from data.dataset_generator import generate_industry_datasets
        generate_industry_datasets()
        st.experimental_rerun()

# ==============================================================================
# 4. CATALYST LIFECYCLE & DEGRADATION
# ==============================================================================
elif nav_choice == "🧬 Catalyst Lifecycle & Degradation":
    st.title("🧬 Catalyst Health, Deactivation & Lifecycle Tracker")
    st.markdown("""
    Tracking catalyst activity decay across time-on-stream (TOS): coke deposition, nitrogen inhibition,
    thermal sintering, and the compensatory WABT ramping toward the End-of-Run (EOR) metallurgy boundary.
    """)
    
    if df_lifecycle_hist is not None:
        # Current cycle status metrics
        curr_day = st.slider("Select Lifecycle Day on Stream (TOS)", 1, 730, 240)
        day_row = df_lifecycle_hist.iloc[curr_day - 1]
        
        l1, l2, l3, l4, l5 = st.columns(5)
        l1.metric("Run Phase", f"{day_row['Run_Phase']}")
        l2.metric("Catalyst Activity", f"{day_row['Catalyst_Activity_Factor']:.3f}")
        l3.metric("Average Coke", f"{day_row['Average_Coke_wt_pct']:.1f} wt%")
        l4.metric("WABT Headroom", f"{day_row['WABT_Headroom_c']:.1f} °C", f"Limit: 425°C")
        l5.metric("Projected RUL", f"{day_row['RUL_Days_Projected']:.0f} Days", f"~{day_row['RUL_Days_Projected']/30.4:.1f} mo")
        
        # Dual Plot: WABT Ramping and Coke Deposition over 730 Days
        st.subheader("📈 Multi-Year WABT Ramping & Remaining Life Trajectory")
        
        fig_life = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            subplot_titles=("WABT Ramping to Maintain Conversion vs EOR Metallurgy Limit", "Catalyst Activity Decay & Coke Buildup (wt%)")
        )
        
        # Row 1: WABT
        fig_life.add_trace(
            go.Scatter(x=df_lifecycle_hist['Day'], y=df_lifecycle_hist['Actual_WABT_c'], name='Actual WABT (°C)', line=dict(color='#f0883e', width=2.5)),
            row=1, col=1
        )
        fig_life.add_trace(
            go.Scatter(x=df_lifecycle_hist['Day'], y=df_lifecycle_hist['Normalized_WABT_c'], name='Normalized WABT (°C)', line=dict(color='#58a6ff', dash='dot')),
            row=1, col=1
        )
        fig_life.add_hline(y=425.0, line_dash='dash', line_color='#ff0000', annotation_text='EOR Metallurgy Limit (425°C)', row=1, col=1)
        fig_life.add_vline(x=curr_day, line_dash='dash', line_color='#ffffff', annotation_text='Current Day', row=1, col=1)
        
        # Row 2: Catalyst Activity and Coke
        fig_life.add_trace(
            go.Scatter(x=df_lifecycle_hist['Day'], y=df_lifecycle_hist['Catalyst_Activity_Factor'], name='Activity Factor (a)', line=dict(color='#2ea043', width=2.5)),
            row=2, col=1
        )
        fig_life.add_trace(
            go.Scatter(x=df_lifecycle_hist['Day'], y=df_lifecycle_hist['Average_Coke_wt_pct'] / 15.0, name='Normalized Coke (0-15 wt%)', line=dict(color='#a371f7', dash='dash')),
            row=2, col=1
        )
        
        fig_life.update_layout(template='plotly_dark', height=550, hovermode='x unified')
        st.plotly_chart(fig_life, use_container_width=True)
        
        # Deactivation Mechanism Breakdown Theory Box
        with st.expander("📚 Catalyst Deactivation Mathematical Formulation"):
            st.markdown(r"""
            ### Mathematical Formulations:
            
            1. **Overall Catalyst Activity:**
            $$a(t) = a_{\text{coke}}(t) \cdot a_{N} \cdot a_{\text{aging}}(t)$$
            
            2. **Coke Deactivation (Voorhies Mechanism):**
            $$\frac{dC_{\text{coke}}}{dt} = k_c \exp\left(-\frac{E_c}{RT}\right) \left(\frac{P_{HC}}{P_{H2}}\right)^{1.3} \left(1 - \frac{C_{\text{coke}}}{C_{\text{coke, max}}}\right)$$
            $$a_{\text{coke}}(t) = \exp(-\alpha_c C_{\text{coke}})$$
            
            3. **Basic Nitrogen Poisoning (Langmuir-Hinshelwood Reversible Inhibition):**
            $$a_N = \frac{1}{1 + K_N \cdot C_{N,\text{slip}}}$$
            
            4. **WABT Compensation Requirement:**
            $$\Delta \text{WABT}_{\text{req}} = \frac{R \cdot \text{WABT}_{\text{ref}}^2}{E_a} \ln\left(\frac{1}{a(t)}\right)$$
            
            5. **Remaining Useful Life (RUL):**
            $$\text{RUL} = \min\left( \frac{\text{WABT}_{\text{EOR}} - \text{WABT}(t)}{d\text{WABT}/dt}, \; \frac{\Delta P_{\text{max}} - \Delta P(t)}{d\Delta P/dt} \right)$$
            """)

# ==============================================================================
# 5. DATA EXPORT & BENCHMARKS
# ==============================================================================
elif nav_choice == "📁 Data Export & API":
    st.title("📁 Industrial Datasets & Telemetry Export")
    st.markdown("""
    Download generated real-time industrial telemetry datasets and catalyst lifecycle data for external
    machine learning training, offline process simulation, or reporting.
    """)
    
    col_e1, col_e2 = st.columns(2)
    
    with col_e1:
        st.subheader("📡 Real-Time DCS Telemetry (24h Stream)")
        st.markdown("**Filename:** `hcu_realtime_industry_telemetry.csv`\n- 1,440 minute-by-minute records\n- Includes 20 DCS process tags, noise, diurnal cycle, and upset events.")
        if df_telemetry_hist is not None:
            csv_tel = df_telemetry_hist.to_csv(index=False).encode('utf-8')
            st.download_button(
                "⬇️ Download Real-Time DCS Telemetry (CSV)",
                data=csv_tel,
                file_name="hcu_realtime_industry_telemetry.csv",
                mime="text/csv"
            )
            st.dataframe(df_telemetry_hist.head(5), use_container_width=True)
            
    with col_e2:
        st.subheader("🧬 Full Catalyst Run Lifecycle (SOR to EOR)")
        st.markdown("**Filename:** `hcu_catalyst_run_lifecycle.csv`\n- 730 day records (2-year cycle)\n- Coke accumulation, WABT ramp, selectivity shift, and RUL tracking.")
        if df_lifecycle_hist is not None:
            csv_life = df_lifecycle_hist.to_csv(index=False).encode('utf-8')
            st.download_button(
                "⬇️ Download Catalyst Lifecycle Dataset (CSV)",
                data=csv_life,
                file_name="hcu_catalyst_run_lifecycle.csv",
                mime="text/csv"
            )
            st.dataframe(df_lifecycle_hist.head(5), use_container_width=True)

st.markdown("---")
st.caption("Hydrocracking Unit (HCU) Digital Twin v2.0 | Built with Python, Streamlit, and Plotly | Advanced Refining Solutions")
