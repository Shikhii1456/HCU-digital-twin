"""
Hydrocracking Unit (HCU) Reaction Kinetics Model
5-Lump Model: VGO (Unconverted Oil) -> Diesel -> Kerosene -> Naphtha -> Gas (LPG/Fuel Gas)
Includes Arrhenius temperature dependence, hydrogen partial pressure effect,
and nitrogen reversible inhibition.
"""

import numpy as np

class HCUKinetics:
    def __init__(self):
        # Lump index:
        # 0: VGO (Vacuum Gas Oil / 370°C+)
        # 1: Diesel (250 - 370°C)
        # 2: Kerosene / Jet (150 - 250°C)
        # 3: Naphtha (C5 - 150°C)
        # 4: Gas (C1 - C4)
        self.lump_names = ['VGO / UCO', 'Diesel', 'Kerosene / Jet', 'Naphtha', 'LPG / Off-gas']
        
        # Reference temperature in Kelvin (390°C)
        self.T_ref = 390.0 + 273.15
        self.R = 8.31446  # J/(mol*K)
        
        # Reference hydrogen partial pressure (140 bar)
        self.P_h2_ref = 140.0
        
        # Reaction network pathways: (from_idx, to_idx, k0 [1/hr], Ea [kJ/mol])
        # Industrial kinetic parameters adapted from hydrocracking literature (Ancheyta et al., Sadighi et al.)
        self.reactions = [
            (0, 1, 0.420, 125.0),  # VGO -> Diesel
            (0, 2, 0.280, 130.0),  # VGO -> Kero
            (0, 3, 0.180, 138.0),  # VGO -> Naphtha
            (0, 4, 0.065, 145.0),  # VGO -> Gas
            (1, 2, 0.110, 142.0),  # Diesel -> Kero (secondary cracking)
            (1, 3, 0.085, 150.0),  # Diesel -> Naphtha
            (1, 4, 0.025, 158.0),  # Diesel -> Gas
            (2, 3, 0.055, 152.0),  # Kero -> Naphtha
            (2, 4, 0.018, 160.0),  # Kero -> Gas
            (3, 4, 0.012, 165.0),  # Naphtha -> Gas (overcracking)
        ]
        
        # Hydrogen consumption stoichiometric coefficients (wt% H2 consumed per wt% converted)
        self.h2_stoich = {
            (0, 1): 0.022,  # VGO -> Diesel (~2.2 wt% H2)
            (0, 2): 0.027,  # VGO -> Kero (~2.7 wt% H2)
            (0, 3): 0.033,  # VGO -> Naphtha (~3.3 wt% H2)
            (0, 4): 0.038,  # VGO -> Gas (~3.8 wt% H2)
            (1, 2): 0.018,  # Diesel -> Kero
            (1, 3): 0.024,  # Diesel -> Naphtha
            (1, 4): 0.028,  # Diesel -> Gas
            (2, 3): 0.016,  # Kero -> Naphtha
            (2, 4): 0.021,  # Kero -> Gas
            (3, 4): 0.014,  # Naphtha -> Gas
        }
        
        # Heat of reaction per kg H2 consumed (exothermic, ~ -50 MJ / kg H2 ~ -100 kJ/mol H2)
        self.heat_of_reaction_H2 = 50.0e6  # J / kg H2 consumed
        
        # Nitrogen inhibition constant (Langmuir-Hinshelwood)
        self.K_nitrogen = 0.025  # (ppmw)^(-1)
        
    def get_rate_constants(self, T_celsius, P_h2_bar, catalyst_activity=1.0, feed_nitrogen_ppm=15.0):
        """
        Calculates apparent reaction rate constants adjusted for temperature,
        hydrogen partial pressure, catalyst activity, and nitrogen poisoning.
        """
        T_k = T_celsius + 273.15
        
        # Reversible nitrogen inhibition on acid cracking sites
        nitrogen_factor = 1.0 / (1.0 + self.K_nitrogen * max(0.0, feed_nitrogen_ppm - 5.0))
        
        # Hydrogen partial pressure effect (reaction order ~ 0.5 for hydrocracking)
        h2_factor = (max(20.0, P_h2_bar) / self.P_h2_ref) ** 0.55
        
        k_dict = {}
        for (i, j, k0, ea) in self.reactions:
            # Modified Arrhenius centered at T_ref
            ea_j = ea * 1000.0
            arrhenius = np.exp(- (ea_j / self.R) * (1.0 / T_k - 1.0 / self.T_ref))
            
            # Overall apparent rate constant
            k_app = k0 * arrhenius * h2_factor * catalyst_activity * nitrogen_factor
            k_dict[(i, j)] = k_app
            
        return k_dict, nitrogen_factor
    
    def compute_reaction_rates(self, yields, T_celsius, P_h2_bar, catalyst_activity=1.0, feed_nitrogen_ppm=15.0):
        """
        Computes the net rate of formation for each lump (dY/dt) and hydrogen consumption rate.
        yields: array-like of length 5 (mass fractions summing to 1.0)
        """
        k_dict, n_factor = self.get_rate_constants(T_celsius, P_h2_bar, catalyst_activity, feed_nitrogen_ppm)
        
        y = np.array(yields, dtype=float)
        dy_dt = np.zeros(5)
        h2_cons_rate = 0.0  # kg H2 / (kg oil * hr)
        
        for (i, j, k0, ea) in self.reactions:
            rate = k_dict[(i, j)] * y[i]  # 1st order in reactant lump
            dy_dt[i] -= rate
            dy_dt[j] += rate
            
            stoich = self.h2_stoich.get((i, j), 0.025)
            h2_cons_rate += rate * stoich
            
        return dy_dt, h2_cons_rate, n_factor
