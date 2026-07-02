"""
Billing Calculator — Chapter 4 Spanish PVPC Settlement
=======================================================

This module implements the Spanish PVPC billing model including:
- Hourly energy-term pricing (import and export)
- Member-level monthly compensation cap (RD 244/2019)
- Forfeited compensation tracking
- Annual bill calculations and battery-specific value

Usage:
    from billing_calculator import BillingCalculator
    
    calc = BillingCalculator(
        result=dispatch_result,
        import_price_eur_kwh=prices_import,
        export_credit_eur_kwh=prices_export,
        scenario_name="pv_bess"
    )
    bills = calc.calculate_bills(timestamps)
    summary = calc.summary()
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dispatch_simulator import DispatchResult


@dataclass
class MemberBilling:
    """Monthly and annual billing for one member."""
    member_id: str
    
    # Monthly data (12 months)
    import_cost_monthly: np.ndarray = field(default_factory=lambda: np.zeros(12))  # € per month
    export_raw_monthly: np.ndarray = field(default_factory=lambda: np.zeros(12))  # € raw credit per month
    export_applied_monthly: np.ndarray = field(default_factory=lambda: np.zeros(12))  # € applied (capped) per month
    bill_monthly: np.ndarray = field(default_factory=lambda: np.zeros(12))  # € net bill per month
    forfeited_monthly: np.ndarray = field(default_factory=lambda: np.zeros(12))  # € forfeited credit per month
    cap_bound_monthly: np.ndarray = field(default_factory=lambda: np.zeros(12, dtype=bool))  # cap binding flag per month
    
    # Annual totals
    import_cost_annual: float = 0.0  # €
    export_raw_annual: float = 0.0  # €
    export_applied_annual: float = 0.0  # € (capped total)
    bill_annual: float = 0.0  # € net annual bill
    forfeited_annual: float = 0.0  # € forfeited compensation
    
    def to_dict(self) -> Dict:
        """Convert to dict for export."""
        return {
            'member_id': self.member_id,
            'import_cost_annual_eur': self.import_cost_annual,
            'export_raw_annual_eur': self.export_raw_annual,
            'export_applied_annual_eur': self.export_applied_annual,
            'bill_annual_eur': self.bill_annual,
            'forfeited_annual_eur': self.forfeited_annual,
            'months_cap_bound': int(np.sum(self.cap_bound_monthly)),
        }


@dataclass
class CommunityBilling:
    """Community-level billing (aggregated from members)."""
    scenario_name: str
    
    # Member dict
    members: Dict[str, MemberBilling] = field(default_factory=dict)
    
    # Community aggregates
    import_cost_annual: float = 0.0  # €
    export_raw_annual: float = 0.0  # €
    export_applied_annual: float = 0.0  # €
    bill_annual: float = 0.0  # €
    forfeited_annual: float = 0.0  # €
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert member data to DataFrame."""
        data = [m.to_dict() for m in self.members.values()]
        return pd.DataFrame(data)
    
    def summary(self) -> Dict:
        """Return summary dict."""
        return {
            'scenario': self.scenario_name,
            'n_members': len(self.members),
            'import_cost_eur': self.import_cost_annual,
            'export_raw_eur': self.export_raw_annual,
            'export_applied_eur': self.export_applied_annual,
            'bill_eur': self.bill_annual,
            'forfeited_eur': self.forfeited_annual,
        }


class BillingCalculator:
    """
    Computes bills under Spanish PVPC settlement with simplified compensation cap.
    
    Implements Section 4.7 of Chapter 4:
    - PVPC import and export pricing
    - Member-level monthly cap (RD 244/2019)
    - Forfeited compensation tracking
    """
    
    def __init__(
        self,
        result: DispatchResult,
        import_price_eur_kwh: np.ndarray,
        export_credit_eur_kwh: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        scenario_name: str = "default",
        member_ids: Optional[List[str]] = None,
    ):
        """
        Initialize billing calculator.
        
        Args:
            result: DispatchResult from dispatch simulator
            import_price_eur_kwh: hourly import prices (€/kWh), length T
            export_credit_eur_kwh: hourly export credits (€/kWh), length T
            timestamps: optional array of datetime objects (for month extraction)
            scenario_name: descriptive name
            member_ids: list of member IDs (defaults to keys of result.member_import)
        """
        self.result = result
        self.import_price = import_price_eur_kwh
        self.export_credit = export_credit_eur_kwh
        self.scenario_name = scenario_name
        self.T = len(import_price_eur_kwh)
        
        # Timestamps: default to synthetic 2026 Jan 1 – Dec 31
        if timestamps is None:
            timestamps = pd.date_range('2026-01-01', periods=self.T, freq='H', tz='Europe/Madrid')
        self.timestamps = np.array(timestamps)
        
        # Member IDs
        if member_ids is None:
            member_ids = list(result.member_import.keys()) if result.member_import else ["community"]
        self.member_ids = member_ids
        
        # Validate
        assert len(self.import_price) == self.T, "Import price array length mismatch"
        assert len(self.export_credit) == self.T, "Export credit array length mismatch"
    
    def calculate_bills(self) -> CommunityBilling:
        """
        Calculate bills for all members.
        
        Returns:
            CommunityBilling with member details and community aggregates.
        """
        community = CommunityBilling(scenario_name=self.scenario_name)
        
        # Calculate for each member
        for member_id in self.member_ids:
            member_bill = self._calculate_member_bill(member_id)
            community.members[member_id] = member_bill
        
        # Aggregate to community level
        community.import_cost_annual = sum(m.import_cost_annual for m in community.members.values())
        community.export_raw_annual = sum(m.export_raw_annual for m in community.members.values())
        community.export_applied_annual = sum(m.export_applied_annual for m in community.members.values())
        community.bill_annual = sum(m.bill_annual for m in community.members.values())
        community.forfeited_annual = sum(m.forfeited_annual for m in community.members.values())
        
        return community
    
    def _calculate_member_bill(self, member_id: str) -> MemberBilling:
        """
        Calculate bill for one member over 12 months.
        
        Implements Equations 4.54–4.62 (Section 4.7.3–4.7.4).
        
        Args:
            member_id: member identifier
        
        Returns:
            MemberBilling with monthly and annual data
        """
        bill = MemberBilling(member_id=member_id)
        
        # Get member-level flows (or use community if no breakdown)
        if self.result.member_import and member_id in self.result.member_import:
            import_kwh = self.result.member_import[member_id]
            export_kwh = self.result.member_export[member_id]
        else:
            # Fall back to community-level flows
            import_kwh = self.result.Import
            export_kwh = self.result.Export
        
        # Extract month from each timestamp
        months = np.array([ts.month - 1 for ts in self.timestamps])  # 0-indexed (0=Jan, 11=Dec)
        
        # Monthly loop (Equations 4.54–4.57)
        for m in range(12):
            idx = months == m
            
            # Import cost (Eq. 4.54)
            C_imp = np.sum(import_kwh[idx] * self.import_price[idx])
            bill.import_cost_monthly[m] = C_imp
            
            # Raw export credit (Eq. 4.55)
            R_raw = np.sum(export_kwh[idx] * self.export_credit[idx])
            bill.export_raw_monthly[m] = R_raw
            
            # Applied export credit (capped) (Eq. 4.56)
            R_applied = min(R_raw, C_imp)
            bill.export_applied_monthly[m] = R_applied
            
            # Net monthly bill (Eq. 4.57)
            B_m = C_imp - R_applied
            bill.bill_monthly[m] = B_m
            
            # Forfeited compensation (Eq. 4.60)
            Lost_m = R_raw - R_applied
            bill.forfeited_monthly[m] = Lost_m
            
            # Cap-binding flag (Eq. 4.61)
            bill.cap_bound_monthly[m] = (R_raw > C_imp)
        
        # Annual totals
        bill.import_cost_annual = np.sum(bill.import_cost_monthly)
        bill.export_raw_annual = np.sum(bill.export_raw_monthly)
        bill.export_applied_annual = np.sum(bill.export_applied_monthly)
        bill.bill_annual = np.sum(bill.bill_monthly)
        bill.forfeited_annual = np.sum(bill.forfeited_monthly)
        
        return bill
    
    def bill_savings(
        self,
        bills_baseline: CommunityBilling,
        bills_scenario: CommunityBilling,
    ) -> Dict:
        """
        Calculate bill savings between two scenarios.
        
        Implements Equations 4.63–4.65 (Section 4.7.5).
        
        Args:
            bills_baseline: baseline (No-DER) CommunityBilling
            bills_scenario: scenario (PV-only or PV-BESS) CommunityBilling
        
        Returns:
            Dict with savings metrics
        """
        B_baseline = bills_baseline.bill_annual
        B_scenario = bills_scenario.bill_annual
        
        savings = B_baseline - B_scenario  # Eq. 4.63
        savings_pct = (savings / B_baseline * 100) if B_baseline > 0 else 0.0  # Eq. 4.64
        
        return {
            'bill_baseline_eur': B_baseline,
            'bill_scenario_eur': B_scenario,
            'savings_eur': savings,
            'savings_pct': savings_pct,
        }
    
    def battery_specific_savings(
        self,
        bills_pv_only: CommunityBilling,
        bills_pv_bess: CommunityBilling,
    ) -> Dict:
        """
        Calculate battery-specific value (Equation 4.65).
        
        Battery-specific savings = Bill(PV-only) - Bill(PV-BESS)
        
        Args:
            bills_pv_only: PV-only scenario billing
            bills_pv_bess: PV-BESS scenario billing
        
        Returns:
            Dict with battery value metrics
        """
        B_pv_only = bills_pv_only.bill_annual
        B_pv_bess = bills_pv_bess.bill_annual
        
        saving_bess = B_pv_only - B_pv_bess  # Eq. 4.65
        
        # Additional metrics
        forfeited_reduction = bills_pv_only.forfeited_annual - bills_pv_bess.forfeited_annual
        import_reduction = bills_pv_only.import_cost_annual - bills_pv_bess.import_cost_annual
        export_increase = bills_pv_bess.export_applied_annual - bills_pv_only.export_applied_annual
        
        return {
            'battery_specific_savings_eur': saving_bess,
            'forfeited_compensation_reduction_eur': forfeited_reduction,
            'import_cost_reduction_eur': import_reduction,
            'export_credit_increase_eur': export_increase,
        }
    
    def monthly_summary(self, community: CommunityBilling) -> pd.DataFrame:
        """
        Create monthly summary table for all members.
        
        Returns:
            DataFrame with monthly data (columns: member, month, import_cost, export_credit, bill, forfeited, cap_bound)
        """
        rows = []
        for member_id, member_bill in community.members.items():
            for m in range(12):
                rows.append({
                    'member_id': member_id,
                    'month': m + 1,
                    'import_cost_eur': member_bill.import_cost_monthly[m],
                    'export_raw_eur': member_bill.export_raw_monthly[m],
                    'export_applied_eur': member_bill.export_applied_monthly[m],
                    'bill_eur': member_bill.bill_monthly[m],
                    'forfeited_eur': member_bill.forfeited_monthly[m],
                    'cap_bound': member_bill.cap_bound_monthly[m],
                })
        return pd.DataFrame(rows)


def compare_scenarios(
    bills_no_der: CommunityBilling,
    bills_pv_only: CommunityBilling,
    bills_pv_bess: CommunityBilling,
    dispatch_results: Dict[str, DispatchResult],
) -> Dict:
    """
    Compare three scenarios and extract key metrics.
    
    Args:
        bills_no_der: No-DER baseline billing
        bills_pv_only: PV-only scenario billing
        bills_pv_bess: PV-BESS scenario billing
        dispatch_results: dict {scenario_name: DispatchResult}
    
    Returns:
        Dict with comparison summary
    """
    calc = BillingCalculator(dispatch_results['no_der'], np.zeros(8760), np.zeros(8760))
    
    # Bill savings
    savings_pv = calc.bill_savings(bills_no_der, bills_pv_only)
    savings_bess = calc.bill_savings(bills_no_der, bills_pv_bess)
    
    # Battery-specific value
    battery_value = calc.battery_specific_savings(bills_pv_only, bills_pv_bess)
    
    # Dispatch KPIs
    result_bess = dispatch_results['pv_bess']
    
    return {
        'scenario_comparison': {
            'no_der_bill_eur': bills_no_der.bill_annual,
            'pv_only_bill_eur': bills_pv_only.bill_annual,
            'pv_bess_bill_eur': bills_pv_bess.bill_annual,
        },
        'pv_only_savings': savings_pv,
        'pv_bess_savings': savings_bess,
        'battery_specific_value': battery_value,
        'pv_bess_kpis': {
            'scr': result_bess.scr,
            'ssr': result_bess.ssr,
            'energy_shifted_kwh': result_bess.energy_shifted,
            'total_pv_kwh': result_bess.total_pv,
            'total_import_kwh': result_bess.total_import,
            'total_export_kwh': result_bess.total_export,
        },
        'pv_only_kpis': {
            'scr': dispatch_results['pv_only'].scr,
            'ssr': dispatch_results['pv_only'].ssr,
            'total_import_kwh': dispatch_results['pv_only'].total_import,
            'total_export_kwh': dispatch_results['pv_only'].total_export,
        },
    }
