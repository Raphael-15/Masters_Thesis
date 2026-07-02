"""
Scenario Runner — Orchestrates parameter sweeps and result aggregation
=======================================================================

This module provides the orchestration layer for running multiple scenarios
with parameter sensitivity analysis. It manages:

- Scenario parameter sweeps (PV capacity, battery CAPEX, community composition)
- Parallel/sequential execution of dispatch and billing
- Result aggregation and KPI table generation
- Export to CSV and JSON

Usage:
    from scenario_runner import ScenarioRunner, ScenarioConfig
    
    config = ScenarioConfig(
        load_kwh=df['load_kwh'].values,
        pv_kwh=df['pv_kwh'].values,
        import_prices=prices_import,
        export_credits=prices_export,
        pv_capacities=[10, 20, 30],  # kWp
        battery_capex=[400, 500, 600],  # €/kWh
    )
    runner = ScenarioRunner(config)
    results = runner.run_all()
    summary = runner.summary()
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import itertools
import json
from pathlib import Path

from dispatch_simulator import (
    BESSDispatcher, PVOnlyDispatcher, NoDERDispatcher,
    DispatchScenario, BESSTechParams
)
from billing_calculator import BillingCalculator


@dataclass
class ScenarioConfig:
    """
    Configuration for scenario sweep.
    
    Attributes:
        load_kwh: baseline hourly load (kWh)
        pv_kwh: baseline hourly PV generation for 1 kWp (kWh)
        import_prices: hourly import prices (€/kWh)
        export_credits: hourly export credits (€/kWh)
        omie_prices: hourly OMIE day-ahead prices (€/MWh) for dispatch signal
        
        pv_capacities: list of PV system sizes to test (kWp)
        battery_capex: list of battery costs to test (€/kWh)
        battery_capacity: fixed battery energy (kWh, default 150)
        community_sizes: list of household counts (default [30])
        cluster_compositions: list of (low%, medium%, high%) tuples (default: 40-40-20)
        
        omie_threshold_percentile: percentile for discharge threshold (default 75)
        discount_rate: real discount rate for NPV (default 0.04)
        pv_lifetime: PV system lifetime (years, default 25)
        bess_lifetime: battery lifetime (years, default 15)
        pv_capex: PV system cost (€/kWp, default 1100)
    """
    load_kwh: np.ndarray
    pv_kwh: np.ndarray
    import_prices: np.ndarray
    export_credits: np.ndarray
    omie_prices: Optional[np.ndarray] = None
    
    # Sensitivity parameters
    pv_capacities: List[float] = field(default_factory=lambda: [10, 20, 30])
    battery_capex: List[float] = field(default_factory=lambda: [400, 500, 600])
    battery_capacity: float = 150.0
    community_sizes: List[int] = field(default_factory=lambda: [30])
    cluster_compositions: List[Tuple[float, float, float]] = field(
        default_factory=lambda: [(0.4, 0.4, 0.2)]
    )
    
    # Economic assumptions
    omie_threshold_percentile: float = 75.0
    discount_rate: float = 0.04
    pv_lifetime: int = 25
    bess_lifetime: int = 15
    pv_capex: float = 1100.0  # €/kWp
    
    def __post_init__(self):
        """Validate and prepare config."""
        if self.omie_prices is None:
            self.omie_prices = np.ones_like(self.import_prices) * 50.0  # default dummy
        
        assert len(self.load_kwh) == len(self.pv_kwh), "Load and PV length mismatch"
        assert len(self.load_kwh) == len(self.import_prices), "Prices length mismatch"
        
        self.T = len(self.load_kwh)


@dataclass
class ScenarioResult:
    """Result for one scenario combination."""
    scenario_id: str  # unique identifier
    pv_capacity_kwp: float
    battery_capex_eur_kwh: float
    community_size: int
    cluster_composition: Tuple[float, float, float]
    
    # Dispatch results (3 scenarios)
    dispatch_no_der: Optional[Dict] = None
    dispatch_pv_only: Optional[Dict] = None
    dispatch_pv_bess: Optional[Dict] = None
    
    # Billing results
    bill_no_der: Optional[Dict] = None
    bill_pv_only: Optional[Dict] = None
    bill_pv_bess: Optional[Dict] = None
    
    # KPIs
    savings_pv_only_eur: float = 0.0
    savings_pv_only_pct: float = 0.0
    savings_pv_bess_eur: float = 0.0
    savings_pv_bess_pct: float = 0.0
    battery_specific_savings_eur: float = 0.0
    
    # Battery KPIs
    scr_pv_only: float = 0.0
    scr_pv_bess: float = 0.0
    ssr_pv_only: float = 0.0
    ssr_pv_bess: float = 0.0
    energy_shifted_kwh: float = 0.0
    
    # Economic metrics (simple payback, NPV)
    payback_years: Optional[float] = None
    npv_eur: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to flat dict for CSV/table export."""
        return {
            'scenario_id': self.scenario_id,
            'pv_capacity_kwp': self.pv_capacity_kwp,
            'battery_capex_eur_kwh': self.battery_capex_eur_kwh,
            'community_size': self.community_size,
            'cluster_low_pct': self.cluster_composition[0],
            'cluster_medium_pct': self.cluster_composition[1],
            'cluster_high_pct': self.cluster_composition[2],
            'savings_pv_only_eur': self.savings_pv_only_eur,
            'savings_pv_only_pct': self.savings_pv_only_pct,
            'savings_pv_bess_eur': self.savings_pv_bess_eur,
            'savings_pv_bess_pct': self.savings_pv_bess_pct,
            'battery_specific_savings_eur': self.battery_specific_savings_eur,
            'scr_pv_only': self.scr_pv_only,
            'scr_pv_bess': self.scr_pv_bess,
            'ssr_pv_only': self.ssr_pv_only,
            'ssr_pv_bess': self.ssr_pv_bess,
            'energy_shifted_kwh': self.energy_shifted_kwh,
            'payback_years': self.payback_years,
            'npv_eur': self.npv_eur,
        }


class ScenarioRunner:
    """
    Orchestrates parameter sweeps and scenario execution.
    
    Generates scenario matrix from config, runs dispatch and billing for
    each combination, and aggregates results.
    """
    
    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.results: List[ScenarioResult] = []
        self.scenario_matrix = self._generate_scenarios()
    
    def _generate_scenarios(self) -> List[Dict]:
        """
        Generate all scenario combinations from config.
        
        Returns:
            List of scenario dicts: {pv_cap, battery_capex, community_size, cluster_comp}
        """
        scenarios = []
        for (pv_cap, bat_capex, comm_size, cluster) in itertools.product(
            self.config.pv_capacities,
            self.config.battery_capex,
            self.config.community_sizes,
            self.config.cluster_compositions,
        ):
            scenario_id = (
                f"pv{pv_cap:.0f}kWp_bess{bat_capex:.0f}eur_n{comm_size}_"
                f"c{int(cluster[0]*100)}-{int(cluster[1]*100)}-{int(cluster[2]*100)}"
            )
            scenarios.append({
                'scenario_id': scenario_id,
                'pv_capacity_kwp': pv_cap,
                'battery_capex_eur_kwh': bat_capex,
                'community_size': comm_size,
                'cluster_composition': cluster,
            })
        return scenarios
    
    def run_all(self, verbose: bool = True) -> List[ScenarioResult]:
        """
        Execute all scenarios.
        
        Args:
            verbose: print progress
        
        Returns:
            List of ScenarioResult objects
        """
        total = len(self.scenario_matrix)
        for idx, scenario in enumerate(self.scenario_matrix):
            if verbose:
                print(f"Running scenario {idx + 1}/{total}: {scenario['scenario_id']}")
            
            result = self._run_scenario(scenario)
            self.results.append(result)
        
        return self.results
    
    def _run_scenario(self, scenario: Dict) -> ScenarioResult:
        """
        Execute one scenario combination.
        
        Args:
            scenario: dict with pv_capacity_kwp, battery_capex_eur_kwh, etc.
        
        Returns:
            ScenarioResult with all metrics
        """
        pv_cap = scenario['pv_capacity_kwp']
        bat_capex = scenario['battery_capex_eur_kwh']
        comm_size = scenario['community_size']
        cluster = scenario['cluster_composition']
        scenario_id = scenario['scenario_id']
        
        # Scale PV and load for community size
        pv_kwh = self.config.pv_kwh * pv_cap  # scale by capacity
        load_kwh = self.config.load_kwh * comm_size  # scale by household count
        
        # Create dispatch scenario
        dispatch_scenario = DispatchScenario(
            load_kwh=load_kwh,
            pv_kwh=pv_kwh,
            omie_price=self.config.omie_prices,
            omie_threshold_percentile=self.config.omie_threshold_percentile,
            use_omie=True,
            battery_params=BESSTechParams(
                E_nom=self.config.battery_capacity,
                S_max=self.config.battery_capacity,
                S_min=self.config.battery_capacity * 0.1,  # 10% reserve
            ),
            scenario_name=scenario_id,
        )
        
        # Run three dispatch scenarios
        dispatch_no_der = NoDERDispatcher(dispatch_scenario).run()
        dispatch_pv_only = PVOnlyDispatcher(dispatch_scenario).run()
        dispatch_pv_bess = BESSDispatcher(dispatch_scenario).run()
        
        # Create billing calculator
        calc = BillingCalculator(
            result=dispatch_no_der,  # dummy for initialization
            import_price_eur_kwh=self.config.import_prices,
            export_credit_eur_kwh=self.config.export_credits,
            scenario_name=scenario_id,
        )
        
        # Calculate bills for each dispatch result
        # (For simplicity, we're using the same pricing for all scenarios)
        calc_no_der = BillingCalculator(
            dispatch_no_der, self.config.import_prices, self.config.export_credits,
            scenario_name=f"{scenario_id}_no_der"
        )
        calc_pv_only = BillingCalculator(
            dispatch_pv_only, self.config.import_prices, self.config.export_credits,
            scenario_name=f"{scenario_id}_pv_only"
        )
        calc_pv_bess = BillingCalculator(
            dispatch_pv_bess, self.config.import_prices, self.config.export_credits,
            scenario_name=f"{scenario_id}_pv_bess"
        )
        
        bill_no_der = calc_no_der.calculate_bills()
        bill_pv_only = calc_pv_only.calculate_bills()
        bill_pv_bess = calc_pv_bess.calculate_bills()
        
        # Calculate savings
        savings_pv = calc.bill_savings(bill_no_der, bill_pv_only)
        savings_bess = calc.bill_savings(bill_no_der, bill_pv_bess)
        battery_value = calc.battery_specific_savings(bill_pv_only, bill_pv_bess)
        
        # Create result object
        result = ScenarioResult(
            scenario_id=scenario_id,
            pv_capacity_kwp=pv_cap,
            battery_capex_eur_kwh=bat_capex,
            community_size=comm_size,
            cluster_composition=cluster,
            dispatch_no_der=dispatch_no_der.to_dataframe().to_dict(),
            dispatch_pv_only=dispatch_pv_only.to_dataframe().to_dict(),
            dispatch_pv_bess=dispatch_pv_bess.to_dataframe().to_dict(),
            bill_no_der=bill_no_der.summary(),
            bill_pv_only=bill_pv_only.summary(),
            bill_pv_bess=bill_pv_bess.summary(),
            savings_pv_only_eur=savings_pv['savings_eur'],
            savings_pv_only_pct=savings_pv['savings_pct'],
            savings_pv_bess_eur=savings_bess['savings_eur'],
            savings_pv_bess_pct=savings_bess['savings_pct'],
            battery_specific_savings_eur=battery_value['battery_specific_savings_eur'],
            scr_pv_only=dispatch_pv_only.scr,
            scr_pv_bess=dispatch_pv_bess.scr,
            ssr_pv_only=dispatch_pv_only.ssr,
            ssr_pv_bess=dispatch_pv_bess.ssr,
            energy_shifted_kwh=dispatch_pv_bess.energy_shifted,
        )
        
        # Calculate economic metrics (simplified payback)
        result.payback_years = self._calculate_payback(
            battery_value['battery_specific_savings_eur'],
            bat_capex * self.config.battery_capacity
        )
        result.npv_eur = self._calculate_npv(
            battery_value['battery_specific_savings_eur'],
            bat_capex * self.config.battery_capacity,
            self.config.bess_lifetime,
            self.config.discount_rate
        )
        
        return result
    
    def _calculate_payback(self, annual_savings: float, investment: float) -> Optional[float]:
        """Simple payback period (years)."""
        if annual_savings <= 0:
            return None
        return investment / annual_savings
    
    def _calculate_npv(
        self,
        annual_savings: float,
        investment: float,
        lifetime: int,
        discount_rate: float
    ) -> float:
        """
        Net Present Value over project lifetime.
        
        NPV = -Investment + ∑(Annual Savings / (1 + r)^t) for t=1 to lifetime
        """
        npv = -investment
        for year in range(1, lifetime + 1):
            npv += annual_savings / ((1 + discount_rate) ** year)
        return npv
    
    def summary(self) -> pd.DataFrame:
        """
        Aggregate all results into a summary table.
        
        Returns:
            DataFrame with one row per scenario
        """
        data = [r.to_dict() for r in self.results]
        return pd.DataFrame(data)
    
    def export_csv(self, path: str):
        """Export summary to CSV."""
        self.summary().to_csv(path, index=False)
        print(f"Exported summary to {path}")
    
    def export_json(self, path: str):
        """Export full results to JSON."""
        data = {
            'config': {
                'T': self.config.T,
                'pv_capacities': self.config.pv_capacities,
                'battery_capex': self.config.battery_capex,
                'community_sizes': self.config.community_sizes,
                'discount_rate': self.config.discount_rate,
                'pv_lifetime': self.config.pv_lifetime,
                'bess_lifetime': self.config.bess_lifetime,
            },
            'results': [r.to_dict() for r in self.results],
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Exported full results to {path}")
    
    def sensitivity_table(self, by: str = 'battery_capex_eur_kwh') -> pd.DataFrame:
        """
        Create sensitivity table sliced by one parameter.
        
        Args:
            by: parameter name to group by ('battery_capex_eur_kwh', 'pv_capacity_kwp', etc.)
        
        Returns:
            Pivot-style DataFrame
        """
        df = self.summary()
        if by == 'battery_capex_eur_kwh':
            return df.pivot_table(
                index='pv_capacity_kwp',
                columns='battery_capex_eur_kwh',
                values='battery_specific_savings_eur',
                aggfunc='first'
            )
        else:
            # Generic groupby
            return df.groupby(by)[['battery_specific_savings_eur', 'payback_years', 'npv_eur']].mean()
