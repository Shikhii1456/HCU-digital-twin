"""
Catalyst Deactivation and Degradation Model for Hydrocracking Units
Calculates multi-mechanism deactivation (coke deposition, nitrogen poisoning, thermal sintering),
WABT compensation requirements, normalized WABT, and Remaining Useful Life (RUL) estimation.
"""

import numpy as np

class CatalystDeactivationModel:
    def __init__(self):
        # Activation energy for cracking reaction lump (kJ/mol)
        self.Ea_cracking = 135.0  # kJ/mol
        self.R = 8.31446  # J/(mol*K)
        
        # Deactivation parameters
        self.coke_max_wt_pct = 18.0     # Maximum saturation coke content on catalyst (wt%)
        self.alpha_coke = 0.085          # Activity decay coefficient per wt% coke
        self.k_coke_base = 0.0042        # Base coking rate (% / day)
        self.Ea_coke = 85.0              # Activation energy for coking (kJ/mol)
        
        # Nitrogen reversible poisoning constant
        self.K_nitrogen = 0.025          # (ppmw)^-1
        
        # Sintering decay constant (1/day)
        self.k_sinter = 0.00015
        
        # EOR (End of Run) constraints
        self.WABT_SOR = 380.0            # Start of Run WABT (°C)
        self.WABT_EOR_LIMIT = 425.0      # Maximum allowable metallurgical WABT limit (°C)
        self.MAX_TOTAL_DP_BAR = 8.5      # Maximum allowable reactor differential pressure (bar)
        self.MAX_BED1_DP_BAR = 4.5       # Maximum allowable Bed 1 differential pressure (bar)

    def calculate_coking_rate(self, T_celsius, P_oil_bar, P_h2_bar, current_coke_wt_pct):
        """
        Calculates differential rate of coke deposition (wt% coke / day)
        Higher temperature, higher oil partial pressure, and lower H2 partial pressure accelerate coking.
        """
        T_k = T_celsius + 273.15
        T_ref_k = 390.0 + 273.15
        
        # Arrhenius factor for coking
        arrh = np.exp(- (self.Ea_coke * 1000.0 / self.R) * (1.0 / T_k - 1.0 / T_ref_k))
        
        # Severity ratio: Hydrocarbon / Hydrogen partial pressure ratio
        severity_ratio = (max(5.0, P_oil_bar) / max(20.0, P_h2_bar)) ** 1.3
        
        # Approach to maximum coke capacity (asymptotic deceleration)
        remaining_capacity = max(0.01, 1.0 - (current_coke_wt_pct / self.coke_max_wt_pct))
        
        d_coke_dt = self.k_coke_base * arrh * severity_ratio * remaining_capacity
        return d_coke_dt

    def calculate_activity(self, coke_wt_pct, feed_nitrogen_ppm, time_on_stream_days, metals_ppm=0.0):
        """
        Calculates current catalyst activity factor (0 < a <= 1.0)
        combining coke fouling, nitrogen poisoning, and long-term aging/sintering.
        """
        # 1. Coke deactivation factor
        a_coke = np.exp(-self.alpha_coke * coke_wt_pct)
        
        # 2. Nitrogen poisoning factor (reversible acid site suppression)
        a_nitrogen = 1.0 / (1.0 + self.K_nitrogen * max(0.0, feed_nitrogen_ppm - 5.0))
        
        # 3. Thermal sintering / aging factor
        a_sinter = 1.0 / np.sqrt(1.0 + self.k_sinter * time_on_stream_days)
        
        # 4. Metals poisoning factor (if feed contains nickel/vanadium/arsenic)
        a_metals = np.exp(-0.00025 * metals_ppm * (time_on_stream_days / 30.0))
        
        # Overall activity
        a_total = a_coke * a_nitrogen * a_sinter * a_metals
        return max(0.05, min(1.0, a_total)), {
            'a_coke': a_coke,
            'a_nitrogen': a_nitrogen,
            'a_sinter': a_sinter,
            'a_metals': a_metals
        }

    def calculate_required_wabt_compensation(self, base_wabt_c, target_activity, current_activity):
        """
        Refinery compensation calculation:
        How much must WABT be raised to maintain target conversion given activity loss?
        Arrhenius relationship: k(T) * a = const => 1/T_new = 1/T_base - (R/Ea) * ln(target_a / current_a)
        """
        T_base_k = base_wabt_c + 273.15
        activity_ratio = max(0.05, current_activity / max(0.05, target_activity))
        
        inv_T_new = (1.0 / T_base_k) - (self.R / (self.Ea_cracking * 1000.0)) * np.log(activity_ratio)
        T_new_k = 1.0 / inv_T_new
        new_wabt_c = T_new_k - 273.15
        
        delta_wabt = new_wabt_c - base_wabt_c
        return new_wabt_c, delta_wabt

    def calculate_normalized_wabt(self, actual_wabt_c, feed_api, base_api=22.0,
                                 feed_nitrogen_ppm=15.0, base_nitrogen_ppm=15.0,
                                 lhsv=1.4, base_lhsv=1.4):
        """
        Standard industry normalization equation to isolate true catalyst deactivation
        from operational swings in feed quality and throughput.
        """
        # Feed API correction (~1.2°C per 1 API drop)
        api_corr = -1.2 * (feed_api - base_api)
        
        # Nitrogen correction (~0.18°C per ppm N)
        n_corr = 0.18 * (feed_nitrogen_ppm - base_nitrogen_ppm)
        
        # LHSV correction (~15°C per ln(LHSV/base))
        lhsv_corr = 15.0 * np.log(max(0.1, lhsv) / base_lhsv)
        
        normalized_wabt = actual_wabt_c - api_corr - n_corr - lhsv_corr
        return normalized_wabt

    def estimate_remaining_useful_life(
        self,
        current_wabt_c,
        deactivation_rate_c_per_month,
        current_total_dp_bar,
        dp_rate_bar_per_month=0.04
    ):
        """
        Estimates Remaining Useful Life (RUL) in days and months based on
        temperature headroom to EOR and pressure drop headroom to compressor limit.
        """
        # Temperature headroom
        temp_margin_c = max(0.0, self.WABT_EOR_LIMIT - current_wabt_c)
        deact_rate_day = max(0.005, deactivation_rate_c_per_month / 30.417)
        rul_days_temp = temp_margin_c / deact_rate_day
        
        # Differential pressure headroom
        dp_margin_bar = max(0.0, self.MAX_TOTAL_DP_BAR - current_total_dp_bar)
        dp_rate_day = max(0.0005, dp_rate_bar_per_month / 30.417)
        rul_days_dp = dp_margin_bar / dp_rate_day
        
        # Governing constraint
        is_dp_limited = rul_days_dp < rul_days_temp
        rul_days_effective = min(rul_days_temp, rul_days_dp)
        rul_months_effective = rul_days_effective / 30.417
        
        return {
            'rul_days': rul_days_effective,
            'rul_months': rul_months_effective,
            'governing_limit': 'Delta-P (Fouling/Hydraulics)' if is_dp_limited else 'WABT (Metallurgy/Selectivity)',
            'temp_headroom_c': temp_margin_c,
            'dp_headroom_bar': dp_margin_bar,
            'deactivation_rate_c_month': deactivation_rate_c_per_month,
            'estimated_eor_date_days': rul_days_effective
        }
