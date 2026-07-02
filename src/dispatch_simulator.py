"""
Dispatch Simulator — Chapter 4 Rule-Based BESS Dispatch
========================================================

This module implements the deterministic hourly rule-based battery dispatch
for PV-only and PV-BESS scenarios as specified in Chapter 4 of the thesis.

The dispatch is transparent, reproducible, and fully auditable hour-by-hour.
It does not use optimization; instead, it applies explicit heuristic rules
in a defined sequence.

Usage:
    from dispatch_simulator import BESSDispatcher, DispatchScenario
    
    scenario = DispatchScenario(
        load_kwh=df['load_kwh'].values,
        pv_kwh=df['pv_kwh'].values,
        ...
    )
    dispatcher = BESSDispatcher(scenario)
    results = dispatcher.run()
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import warnings


@dataclass
class BESSTechParams:
    """Battery technical parameters (Chapter 4, Table 4.4)."""
    E_nom: float = 150.0  # kWh, nominal energy capacity
    S_min: float = 15.0  # kWh, minimum SOC (90% DoD reserve)
    S_max: float = 150.0  # kWh, maximum SOC
    P_ch_max: float = 75.0  # kW, max charge power (0.5C for 150 kWh)
    P_dis_max: float = 75.0  # kW, max discharge power
    eta_ch: float = 0.949  # charging efficiency (90% round-trip ≈ 0.949 one-way)
    eta_dis: float = 0.949  # discharging efficiency
    S_init_pct: float = 0.5  # initial SOC as % of S_max


@dataclass
class DispatchScenario:
    """
    Input scenario for dispatch simulation.
    
    Attributes:
        load_kwh: numpy array of hourly load (kWh), length T
        pv_kwh: numpy array of hourly PV generation (kWh), length T
        omie_price: numpy array of OMIE day-ahead prices (€/MWh), length T
        omie_threshold_percentile: percentile for discharge threshold (default 75)
        use_omie: whether to apply OMIE threshold logic (default True)
        battery_params: BESSTechParams instance
        scenario_name: descriptive name for the scenario
        member_allocations: optional dict {member_id: allocation_coefficient}
    """
    load_kwh: np.ndarray
    pv_kwh: np.ndarray
    omie_price: np.ndarray
    omie_threshold_percentile: float = 75.0
    use_omie: bool = True
    battery_params: BESSTechParams = field(default_factory=BESSTechParams)
    scenario_name: str = "default"
    member_allocations: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        """Validate inputs."""
        T = len(self.load_kwh)
        assert len(self.pv_kwh) == T, "PV and load must have same length"
        assert len(self.omie_price) == T, "OMIE price must have same length"
        assert np.all(self.load_kwh >= 0), "Load must be non-negative"
        assert np.all(self.pv_kwh >= 0), "PV must be non-negative"
        assert np.all(self.omie_price >= -1000), "OMIE price must be reasonable (€/MWh)"
        
        # Compute OMIE threshold from percentile
        self.omie_threshold = np.percentile(self.omie_price, self.omie_threshold_percentile)
        
        # Default allocation: single community member
        if self.member_allocations is None:
            self.member_allocations = {"community": 1.0}
        
        # Normalize allocations to sum to 1
        alloc_sum = sum(self.member_allocations.values())
        if abs(alloc_sum - 1.0) > 1e-6:
            self.member_allocations = {
                k: v / alloc_sum for k, v in self.member_allocations.items()
            }


@dataclass
class DispatchResult:
    """
    Output of dispatch simulation.
    
    Hourly time series and KPI summary.
    """
    # Hourly time series (length T)
    P_ch: np.ndarray  # battery charge (kWh/h)
    P_dis: np.ndarray  # battery discharge (kWh/h)
    S: np.ndarray  # state of charge at end of hour (kWh)
    Import: np.ndarray  # grid import (kWh/h)
    Export: np.ndarray  # grid export (kWh/h)
    SC_pv: np.ndarray  # self-consumption (kWh/h)
    
    # Member-level allocations (optional)
    member_pv_alloc: Optional[Dict[str, np.ndarray]] = None  # allocated PV per member
    member_ch_alloc: Optional[Dict[str, np.ndarray]] = None  # allocated charge per member
    member_dis_alloc: Optional[Dict[str, np.ndarray]] = None  # allocated discharge per member
    member_import: Optional[Dict[str, np.ndarray]] = None  # allocated import per member
    member_export: Optional[Dict[str, np.ndarray]] = None  # allocated export per member
    
    # Annual KPIs
    total_load: float = 0.0
    total_pv: float = 0.0
    total_import: float = 0.0
    total_export: float = 0.0
    scr: float = 0.0  # self-consumption ratio
    ssr: float = 0.0  # self-sufficiency ratio
    energy_shifted: float = 0.0  # battery discharge (proxy for shifted energy)
    
    # Validation flags
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        df = pd.DataFrame({
            'P_ch': self.P_ch,
            'P_dis': self.P_dis,
            'SoC': self.S,
            'Import': self.Import,
            'Export': self.Export,
            'SC_pv': self.SC_pv,
        })
        return df


class BESSDispatcher:
    """
    Dispatch simulator implementing Chapter 4 rule-based logic.
    
    Transparent, reproducible, hour-by-hour deterministic dispatch.
    No optimization; explicit heuristic rules applied in sequence.
    """
    
    def __init__(self, scenario: DispatchScenario):
        self.scenario = scenario
        self.T = len(scenario.load_kwh)
        self.params = scenario.battery_params
        
    def run(self) -> DispatchResult:
        """
        Execute dispatch for all T hours.
        
        Returns:
            DispatchResult with hourly and annual KPIs.
        """
        # Initialize time series
        P_ch = np.zeros(self.T)
        P_dis = np.zeros(self.T)
        S = np.zeros(self.T)
        Import = np.zeros(self.T)
        Export = np.zeros(self.T)
        SC = np.zeros(self.T)
        
        # Member-level allocations
        member_pv_alloc = {m: np.zeros(self.T) for m in self.scenario.member_allocations}
        member_ch_alloc = {m: np.zeros(self.T) for m in self.scenario.member_allocations}
        member_dis_alloc = {m: np.zeros(self.T) for m in self.scenario.member_allocations}
        member_import = {m: np.zeros(self.T) for m in self.scenario.member_allocations}
        member_export = {m: np.zeros(self.T) for m in self.scenario.member_allocations}
        
        # Initialize state
        S_prev = self.params.S_max * self.params.S_init_pct
        
        # Hour-by-hour dispatch
        for t in range(self.T):
            Load_t = self.scenario.load_kwh[t]
            PV_t = self.scenario.pv_kwh[t]
            omie_t = self.scenario.omie_price[t]
            
            # ===== STEP 1: Meet load with PV (self-consumption) =====
            pv_to_load = min(PV_t, Load_t)
            load_remaining = Load_t - pv_to_load
            pv_remaining = PV_t - pv_to_load
            
            # ===== STEP 2: Charge battery from remaining PV =====
            if pv_remaining > 0 and S_prev < self.params.S_max:
                max_charge_energy = min(
                    pv_remaining,
                    self.params.P_ch_max,
                    (self.params.S_max - S_prev) / self.params.eta_ch
                )
                P_ch[t] = max_charge_energy
            else:
                P_ch[t] = 0.0
            
            # ===== STEP 3: Discharge to meet remaining load =====
            if load_remaining > 0 and S_prev > self.params.S_min:
                max_discharge_energy = min(
                    load_remaining,
                    self.params.P_dis_max,
                    (S_prev - self.params.S_min) * self.params.eta_dis
                )
                P_dis[t] = max_discharge_energy
                load_remaining -= P_dis[t]
            else:
                P_dis[t] = 0.0
            
            # ===== STEP 4: OMIE threshold logic (optional) =====
            if self.scenario.use_omie:
                # High price: opportunistic discharge to reduce imports
                if (omie_t >= self.scenario.omie_threshold and 
                    P_dis[t] == 0 and S_prev > self.params.S_min):
                    extra_discharge = min(
                        self.params.P_dis_max - P_dis[t],
                        (S_prev - self.params.S_min) * self.params.eta_dis
                    )
                    P_dis[t] += extra_discharge
                
                # Low price: avoid charging that leads to export
                if omie_t < self.scenario.omie_threshold and P_ch[t] > 0:
                    projected_export = pv_remaining - P_ch[t]
                    if projected_export > 0:
                        reduce = min(P_ch[t], projected_export)
                        P_ch[t] -= reduce
            
            # ===== STEP 5: Update SOC =====
            S_after_ch = S_prev + self.params.eta_ch * P_ch[t]
            S_new = S_after_ch - P_dis[t] / self.params.eta_dis
            S_new = np.clip(S_new, self.params.S_min, self.params.S_max)
            S[t] = S_new
            
            # ===== STEP 6: Calculate net flow and imports/exports =====
            net = Load_t - PV_t - P_dis[t] + P_ch[t]
            Import[t] = max(net, 0.0)
            Export[t] = max(-net, 0.0)
            SC[t] = PV_t - Export[t]
            
            # ===== STEP 7: Member-level allocation =====
            self._allocate_flows_to_members(
                t, Load_t, PV_t, P_ch[t], P_dis[t], Import[t], Export[t],
                member_pv_alloc, member_ch_alloc, member_dis_alloc,
                member_import, member_export
            )
            
            # Update state for next hour
            S_prev = S_new
        
        # Create result object
        result = DispatchResult(
            P_ch=P_ch, P_dis=P_dis, S=S,
            Import=Import, Export=Export, SC_pv=SC,
            member_pv_alloc=member_pv_alloc,
            member_ch_alloc=member_ch_alloc,
            member_dis_alloc=member_dis_alloc,
            member_import=member_import,
            member_export=member_export,
        )
        
        # Compute annual KPIs
        result.total_load = np.sum(self.scenario.load_kwh)
        result.total_pv = np.sum(self.scenario.pv_kwh)
        result.total_import = np.sum(Import)
        result.total_export = np.sum(Export)
        result.scr = np.sum(SC) / result.total_pv if result.total_pv > 0 else 0.0
        result.ssr = (result.total_load - result.total_import) / result.total_load if result.total_load > 0 else 0.0
        result.energy_shifted = np.sum(P_dis)
        
        # Run validation checks (Section 4.6.3)
        self._validate(result)
        
        return result
    
    def _allocate_flows_to_members(
        self, t: int, Load_t: float, PV_t: float, P_ch_t: float, P_dis_t: float,
        Import_t: float, Export_t: float,
        member_pv_alloc: Dict, member_ch_alloc: Dict, member_dis_alloc: Dict,
        member_import: Dict, member_export: Dict
    ):
        """
        Allocate community-level flows to members (Equations 4.30–4.37).
        
        Uses static allocation coefficients β_i for PV.
        Charges allocated proportionally to member surplus.
        Discharges allocated proportionally to member deficit.
        """
        members = list(self.scenario.member_allocations.keys())
        betas = self.scenario.member_allocations
        
        # PV allocation (Eq. 4.30)
        member_loads = {m: Load_t * betas[m] for m in members}  # assumption: uniform load
        for m in members:
            member_pv_alloc[m][t] = betas[m] * PV_t
        
        # Member-level surplus before battery (Eq. 4.31)
        member_surplus_pv = {
            m: max(member_pv_alloc[m][t] - member_loads[m], 0.0)
            for m in members
        }
        total_surplus_pv = sum(member_surplus_pv.values())
        
        # Charge allocation (Eq. 4.32)
        if total_surplus_pv > 1e-6:
            for m in members:
                member_ch_alloc[m][t] = P_ch_t * (member_surplus_pv[m] / total_surplus_pv)
        
        # Member-level deficit after PV (Eq. 4.33)
        member_deficit_pv = {
            m: max(member_loads[m] - member_pv_alloc[m][t], 0.0)
            for m in members
        }
        total_deficit_pv = sum(member_deficit_pv.values())
        
        # Discharge allocation (Eq. 4.34–4.35)
        if total_deficit_pv > 1e-6:
            for m in members:
                member_dis_alloc[m][t] = P_dis_t * (member_deficit_pv[m] / total_deficit_pv)
        
        # Member-level imports/exports (Eq. 4.36–4.37)
        for m in members:
            I_m = max(
                member_loads[m] - member_pv_alloc[m][t] - member_dis_alloc[m][t],
                0.0
            )
            E_m = max(
                member_pv_alloc[m][t] - member_loads[m] - member_ch_alloc[m][t],
                0.0
            )
            member_import[m][t] = I_m
            member_export[m][t] = E_m
    
    def _validate(self, result: DispatchResult):
        """
        Run validation checks (Table 4.3, Section 4.6.3).
        
        Records errors but does not raise exceptions (allows inspection).
        """
        tolerance = 1e-6
        errors = []
        
        # Check 1: Hourly energy balance (Eq. 4.45)
        Load = self.scenario.load_kwh
        PV = self.scenario.pv_kwh
        for t in range(self.T):
            lhs = PV[t] + result.Import[t] + result.P_dis[t]
            rhs = Load[t] + result.Export[t] + result.P_ch[t]
            if abs(lhs - rhs) > tolerance:
                errors.append(f"Hour {t}: energy balance error {abs(lhs - rhs):.6f} kWh")
        
        # Check 2: SOC bounds (Eq. 4.22)
        if np.any(result.S < self.params.S_min - tolerance) or np.any(result.S > self.params.S_max + tolerance):
            errors.append(f"SOC out of bounds: min={np.min(result.S):.2f}, max={np.max(result.S):.2f}")
        
        # Check 3: Non-negativity
        if np.any(result.P_ch < -tolerance) or np.any(result.P_dis < -tolerance):
            errors.append("Negative charge/discharge power")
        if np.any(result.Import < -tolerance) or np.any(result.Export < -tolerance):
            errors.append("Negative import/export")
        
        # Check 4: No simultaneous charge/discharge (Eq. 4.24)
        simultaneous = np.sum((result.P_ch > tolerance) & (result.P_dis > tolerance))
        if simultaneous > 0:
            errors.append(f"Simultaneous charge/discharge in {simultaneous} hours")
        
        # Check 5: Allocation coefficients sum to 1
        alloc_sum = sum(self.scenario.member_allocations.values())
        if abs(alloc_sum - 1.0) > tolerance:
            errors.append(f"Allocation coefficients sum to {alloc_sum:.6f}, not 1.0")
        
        # Check 6: Flow aggregation (member totals match community)
        if result.member_import is not None:
            for t in range(self.T):
                member_import_sum = sum(result.member_import[m][t] for m in result.member_import)
                if abs(member_import_sum - result.Import[t]) > tolerance:
                    errors.append(f"Hour {t}: member imports {member_import_sum:.6f} != community {result.Import[t]:.6f}")
        
        if errors:
            result.validation_passed = False
            result.validation_errors = errors
        else:
            result.validation_passed = True
            result.validation_errors = []


class PVOnlyDispatcher:
    """
    Simplified dispatcher for PV-only scenario (no battery).
    
    For comparison with PV-BESS to calculate battery-specific value.
    """
    
    def __init__(self, scenario: DispatchScenario):
        self.scenario = scenario
        self.T = len(scenario.load_kwh)
    
    def run(self) -> DispatchResult:
        """
        Execute PV-only dispatch (no battery).
        
        Returns:
            DispatchResult with battery flows set to zero.
        """
        Load = self.scenario.load_kwh
        PV = self.scenario.pv_kwh
        
        # Self-consumption: min(load, PV)
        SC = np.minimum(Load, PV)
        
        # Net flow
        net = Load - PV
        Import = np.maximum(net, 0.0)
        Export = np.maximum(-net, 0.0)
        
        # Battery flows are zero
        P_ch = np.zeros(self.T)
        P_dis = np.zeros(self.T)
        S = np.zeros(self.T)
        
        # Create result
        result = DispatchResult(
            P_ch=P_ch, P_dis=P_dis, S=S,
            Import=Import, Export=Export, SC_pv=SC
        )
        
        # Annual KPIs
        result.total_load = np.sum(Load)
        result.total_pv = np.sum(PV)
        result.total_import = np.sum(Import)
        result.total_export = np.sum(Export)
        result.scr = np.sum(SC) / result.total_pv if result.total_pv > 0 else 0.0
        result.ssr = (result.total_load - result.total_import) / result.total_load if result.total_load > 0 else 0.0
        result.energy_shifted = 0.0
        result.validation_passed = True
        
        return result


class NoDERDispatcher:
    """
    No-DER scenario (no PV, no battery).
    
    Baseline for bill savings comparison.
    """
    
    def __init__(self, scenario: DispatchScenario):
        self.scenario = scenario
        self.T = len(scenario.load_kwh)
    
    def run(self) -> DispatchResult:
        """
        Execute no-DER dispatch (all load from grid).
        
        Returns:
            DispatchResult with all load as import.
        """
        Load = self.scenario.load_kwh
        
        Import = Load.copy()
        Export = np.zeros(self.T)
        P_ch = np.zeros(self.T)
        P_dis = np.zeros(self.T)
        S = np.zeros(self.T)
        SC = np.zeros(self.T)
        
        result = DispatchResult(
            P_ch=P_ch, P_dis=P_dis, S=S,
            Import=Import, Export=Export, SC_pv=SC
        )
        
        result.total_load = np.sum(Load)
        result.total_pv = 0.0
        result.total_import = np.sum(Import)
        result.total_export = 0.0
        result.scr = 0.0
        result.ssr = 0.0
        result.energy_shifted = 0.0
        result.validation_passed = True
        
        return result
