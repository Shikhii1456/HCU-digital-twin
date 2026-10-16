# Hydrocracking Unit (HCU) Digital Twin & Catalyst Health Optimizer

A real-time, physics-based, catalyst-aware Digital Twin for commercial Hydrocracking Units (HCU) built with Python, Streamlit, and Plotly.

---

## 🌟 Key Features

1. **First-Principles Hydrocracking Kinetics & Multi-Bed Reactor Physics**:
   - 5-Lump reaction network: Vacuum Gas Oil (VGO / UCO) $\rightarrow$ Diesel $\rightarrow$ Kerosene/Jet $\rightarrow$ Naphtha $\rightarrow$ LPG/Off-gas.
   - Arrhenius temperature kinetics, hydrogen partial pressure dependence, and Langmuir-Hinshelwood reversible nitrogen inhibition.
   - Commercial 3-bed trickle-bed reactor simulation with inter-bed hydrogen quench cooling, exothermic heat release, and axial temperature profile.
   - Industrial standard Weighted Average Bed Temperature (**WABT**):
     $$\text{WABT} = \sum_{j=1}^{N_{\text{beds}}} w_j \left(\frac{T_{\text{in}, j} + 2 T_{\text{out}, j}}{3}\right)$$
   - Ergun equation pressure drop ($\Delta P$) with bed fouling enhancement.

2. **Catalyst Deactivation & Remaining Useful Life (RUL) Engine**:
   - Multi-mechanism catalyst decay:
     - **Coke Deposition (Voorhies Mechanism)**: Dynamic rate based on temperature, hydrocarbon/hydrogen ratio, and coke saturation capacity.
     - **Reversible Nitrogen Poisoning**: Basic nitrogen ($NH_3$/amines) blocking Brønsted acid sites.
     - **Thermal Sintering & Aging**: Time-on-stream decay of active metal sites.
   - **Refinery WABT Compensation Calculation**: Computes required temperature increase to maintain target conversion as catalyst deactivates.
   - **Normalized WABT**: Corrected for feed API, nitrogen content, and space velocity (LHSV).
   - **Dual-Constraint RUL Prediction**: Tracks both WABT metallurgy boundary ($425^\circ\text{C}$ EOR limit) and reactor differential pressure boundary ($\Delta P \ge 8.5\text{ bar}$).

3. **Dynamic Real-Time DCS Telemetry**:
   - Ingests / generates minute-by-minute streaming plant telemetry matching industrial historians (OSIsoft PI, Honeywell Uniformance PHD, Emerson DeltaV).
   - 20+ standard industrial tag names (`HCU_FC101.PV`, `HCU_TI100.CALC`, `HCU_PDI100.CALC`, etc.).
   - Includes real-world sensor noise, diurnal ambient cycles, and operational transients.

4. **"What-If" Operational Sandbox & Deviation Matrix**:
   - Side-by-side comparison between **Baseline Normal** and **Perturbed Conditions**.
   - Pre-configured industrial disturbance cases:
     - *Feed Nitrogen Slip (Upstream Hydrotreater Breakthrough)*
     - *Recycle Gas Purity Drop / Low $H_2$ Partial Pressure (Severe Coking)*
     - *Inter-Bed Quench Valve Failure (Thermal Runaway Hazard)*
     - *Heavy Opportunity Crude Switch (Low API / High Conradson Carbon)*
     - *High Throughput / Maximum Diesel Production Push*
   - Real-time deviation analytics on Conversion, WABT, Catalyst Activity, RUL, and Gross Margin (\$/day).
   - Process safety envelope alarms (NORMAL, ADVISORY, WARNING, CRITICAL).

5. **Refinery Economics Tracker**:
   - Real-time calculation of feed costs, chemical hydrogen consumption cost, gross product revenues, gross margin (\$/day), and margin per barrel (\$/bbl).

---

## 🚀 How to Run the Streamlit Digital Twin

### Option 1: Terminal Command
Run the following command in PowerShell / Command Prompt:
```powershell
py -m streamlit run "C:\Users\OMEN\.gemini\antigravity\scratch\hcu_digital_twin\app.py"
```

### Option 2: Run via Batch File
Double click `run_app.bat` inside `C:\Users\OMEN\.gemini\antigravity\scratch\hcu_digital_twin\`.

---

## 📁 Project Architecture

```
hcu_digital_twin/
│
├── app.py                         # Main interactive Streamlit application
├── README.md                      # Documentation & mathematical formulations
├── run_app.bat                    # One-click startup script for Windows
│
├── models/
│   ├── __init__.py
│   ├── kinetics.py                # 5-lump reaction kinetics & H2 consumption
│   ├── reactor.py                 # 3-bed reactor heat balance, quenches, WABT & DP
│   └── deactivation.py            # Coke fouling, nitrogen poisoning, normalized WABT & RUL
│
├── simulator/
│   ├── __init__.py
│   ├── engine.py                  # Digital twin simulation engine, DCS tags & economics
│   └── scenarios.py               # "What-If" industrial disturbance presets
│
└── data/
    ├── dataset_generator.py       # Benchmark generator for industrial telemetry
    ├── hcu_realtime_industry_telemetry.csv  # 24-hr minute-by-minute DCS stream
    └── hcu_catalyst_run_lifecycle.csv       # 730-day SOR to EOR catalyst history
```

---

## 📊 Datasets Included

1. **`data/hcu_realtime_industry_telemetry.csv`**:
   - 1,440 time steps (24 hours at 1-minute intervals).
   - Contains feed rate swings, feed transition at minute 400, upstream hydrotreater nitrogen breakthrough at minute 900, and operator quench trim response.
2. **`data/hcu_catalyst_run_lifecycle.csv`**:
   - 730 operating days (2-year continuous run).
   - Shows progressive coke accumulation (from 0.8 wt% at SOR to 12.5 wt% at EOR), WABT ramping ($378^\circ\text{C} \rightarrow 422^\circ\text{C}$), and Remaining Useful Life (RUL) trajectory.
