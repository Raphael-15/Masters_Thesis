---
chapter: 3
title: "Mathematical Formulation for Energy Communities"
canonical_source: "../canonical_tex/03_mathematical_formulation.tex"
content_policy: "Exact LaTeX embedded below; no prose replacement"
---

# Chapter 3: Mathematical Formulation for Energy Communities

```latex
% =====================================================================
% Chapter 3: Mathematical Formulation for Energy Communities
% Content reorganised from the former Chapters 3 and 5.
% No substantive thesis content has been removed.
% =====================================================================

\subsection{Modelling Framework}
\label{sec:modelling_framework}

\subsubsection{Overall Approach}
\label{subsec:overall_approach}

A deterministic time-series simulation model is used. All inputs--household demand, PV generation, electricity prices, allocation coefficients, and technical parameters--are specified as aligned time series or fixed parameters. No stochastic process, probabilistic forecast, or optimisation solver is required in the baseline framework. This choice supports transparent, reproducible, and auditable evaluation of battery value under explicitly defined operating and settlement rules.

The model is formulated for a general simulation horizon $T$ and participant set $i=1,\ldots,N$. An hourly implementation is used in this thesis; for a complete non-leap calendar year, $T=8760$. Other locations, community sizes, and aligned time horizons can be represented without changing the energy-flow equations. Three configurations are simulated under identical inputs:

\begin{enumerate}
    \item \textbf{No-DER baseline:} no shared PV and no battery; all household demand is served from the grid.
    \item \textbf{PV-only scenario:} shared community PV is introduced; surplus allocated PV is exported to the grid.
    \item \textbf{PV--BESS scenario:} shared community PV is combined with a centralised community battery; allocated PV surplus charges the battery before export.
\end{enumerate}

Battery-specific value is defined as the incremental difference between the PV--BESS result and the PV-only result under the same load profiles, PV generation, price series, tariff rules, and allocation coefficients:

\begin{equation}
\label{eq:delta_x_bess}
\Delta X_{\mathrm{BESS}} = X_{\mathrm{PV\mbox{-}BESS}} - X_{\mathrm{PV\mbox{-}only}},
\end{equation}

where $X$ may represent annual bill savings, NPV, self-consumption ratio, self-sufficiency ratio, or another defined performance indicator. This reference-case comparison links the measured difference directly to the battery rather than to the PV system or to changes in the assumed inputs.

\subsubsection{Regulatory and Settlement Boundary}
\label{subsec:regulatory_settlement_boundary}

The physical energy-flow and allocation layers are general and can be reused under different regulatory settings. The settlement layer is modular: import valuation, export valuation, billing-period length, compensation limits, and carry-over rules can be replaced without changing the preceding hourly energy-flow equations.

For the Spanish application developed in this thesis, collective self-consumption is represented under Real Decreto 244/2019 \cite{boe2019real}. Shared generation is assigned through participant-level allocation coefficients, and the simplified-compensation mechanism is applied monthly. Export compensation cannot exceed the value of imported energy within the same billing period, and unused compensation is not carried forward. The case-specific regulatory boundary and Seville assumptions are documented in Section~\ref{sec:case-study}.

Static allocation coefficients are used in the baseline framework. These coefficients remain fixed over the simulation horizon and are applied to shared PV generation and to the attribution of battery-related flows. Dynamic allocation can be incorporated in another application by replacing the coefficient time series while retaining the same member-level accounting structure.

\subsection{No-DER Baseline Scenario}
\label{sec:no_der_baseline_ch4}

The No-DER baseline represents the reference case with no shared PV system and no battery in the community. This indicates that every household demand is supplied by the grid. This scenario creates the reference electricity bill against which PV-only and PV--BESS savings are measured.

\subsubsection{Energy Balance}
\label{subsec:no_der_energy_balance}

\begin{equation}
\label{eq:aggregate_load}
L_t = \sum_{i=1}^{N} L_{i,t},
\end{equation}

\begin{equation}
\label{eq:no_der_import_member}
I^0_{i,t} = L_{i,t},
\end{equation}

\begin{equation}
\label{eq:no_der_export_self_consumption}
E^0_{i,t} = 0, \qquad SC^0_{i,t} = 0,
\end{equation}

\begin{equation}
\label{eq:no_der_import_total}
I^0_t = \sum_{i=1}^{N} I^0_{i,t} = L_t.
\end{equation}

\subsubsection{Billing}
\label{subsec:no_der_billing}

\begin{equation}
\label{eq:no_der_monthly_cost}
C^0_{i,m} = \sum_{t \in m} I^0_{i,t} p^{\mathrm{imp}}_t,
\end{equation}

\begin{equation}
\label{eq:no_der_annual_bill_member}
B^0_i = \sum_{m=1}^{12} C^0_{i,m},
\end{equation}

\begin{equation}
\label{eq:no_der_annual_bill_community}
B^0_{\mathrm{community}} = \sum_{i=1}^{N} B^0_i.
\end{equation}

Since there is no export in the No-DER case, no export compensation or monthly compensation cap is applied. For calculating absolute and percentage savings in the PV-only and PV--BESS scenarios, the annual No-DER bill is considered the reference.

\subsection{PV-Only Scenario}
\label{sec:pv_only_scenario_ch4}

In this scenario, there is the introduction of a shared community PV system but no battery. PV generation is allocated to members using static coefficients. Here, each member first uses its allocated generated energy to offset its own hourly demand; energy demand is imported from the grid if there is residual demand left, and excess energy from allocated PV is exported.

\subsubsection{Static Member-Level Allocation}
\label{subsec:static_member_allocation_pv_only}

\begin{equation}
\label{eq:beta_condition}
\beta_i \geq 0, \qquad \sum_{i=1}^{N} \beta_i = 1,
\end{equation}

\begin{equation}
\label{eq:allocated_pv}
G^{\mathrm{alloc}}_{i,t} = \beta_i G_t.
\end{equation}

In the baseline, the static coefficients are proportional to annual household demand:

\begin{equation}
\label{eq:beta_annual_demand}
\beta_i = \frac{\sum_t L_{i,t}}{\sum_i \sum_t L_{i,t}}.
\end{equation}

This proportional rule provides larger shares of shared PV to members with greater annual demand, while preserving a transparent and reusable allocation mechanism.

\subsubsection{Member-Level Energy Flows}
\label{subsec:member_level_energy_flows_pv_only}

\begin{equation}
\label{eq:pv_self_consumption_member}
SC^{\mathrm{PV}}_{i,t} = \min\left(L_{i,t}, G^{\mathrm{alloc}}_{i,t}\right),
\end{equation}

\begin{equation}
\label{eq:pv_import_member}
I^{\mathrm{PV}}_{i,t} = \max\left(L_{i,t} - G^{\mathrm{alloc}}_{i,t}, 0\right),
\end{equation}

\begin{equation}
\label{eq:pv_export_member}
E^{\mathrm{PV}}_{i,t} = \max\left(G^{\mathrm{alloc}}_{i,t} - L_{i,t}, 0\right),
\end{equation}

\begin{equation}
\label{eq:pv_aggregated_flows}
SC^{\mathrm{PV}}_t = \sum_i SC^{\mathrm{PV}}_{i,t}, \qquad I^{\mathrm{PV}}_t = \sum_i I^{\mathrm{PV}}_{i,t}, \qquad E^{\mathrm{PV}}_t = \sum_i E^{\mathrm{PV}}_{i,t}.
\end{equation}

This member-level hourly calculation is preferred to community-level netting because offsetting imports and exports across participants can overestimate self-consumption. For example, one member may export excess allocated PV while another imports grid energy during the same hour. Static allocation therefore requires member-level flow calculation before aggregation.

\subsubsection{Energy Conservation and Performance Indicators}
\label{subsec:energy_conservation_indicators_pv_only}

\begin{equation}
\label{eq:pv_member_energy_conservation}
L_{i,t} + E^{\mathrm{PV}}_{i,t} = G^{\mathrm{alloc}}_{i,t} + I^{\mathrm{PV}}_{i,t},
\end{equation}

\begin{equation}
\label{eq:pv_community_energy_conservation}
L_t + E^{\mathrm{PV}}_t = G_t + I^{\mathrm{PV}}_t,
\end{equation}

\begin{equation}
\label{eq:scr_pv}
SCR^{\mathrm{PV}} = \frac{\sum_t SC^{\mathrm{PV}}_t}{\sum_t G_t},
\end{equation}

\begin{equation}
\label{eq:ssr_pv}
SSR^{\mathrm{PV}} = \frac{\sum_t SC^{\mathrm{PV}}_t}{\sum_t L_t}.
\end{equation}

The self-consumption ratio (SCR) measures the share of PV generation consumed locally, while the self-sufficiency ratio (SSR) measures the share of community demand served by local PV generation.

\subsection{PV--BESS Scenario}
\label{sec:pv_bess_scenario_ch4}

In this scenario, a centralised community battery is added to the PV-only configuration. The battery is represented by its upper and lower state-of-charge limits, charge and discharge power limits, round-trip efficiency, and initial state of charge. These parameters are application inputs rather than fixed properties of the general methodology. The corresponding values for the Seville case study are defined in Section~\ref{sec:technology_economic_parameters}.

Where equal one-way efficiencies are assumed, the round-trip efficiency $\eta^{\mathrm{rt}}$ is represented consistently as

\begin{equation}
\label{eq:one_way_efficiency}
\eta^{\mathrm{ch}}=\eta^{\mathrm{dis}}=\sqrt{\eta^{\mathrm{rt}}}.
\end{equation}

After member-level allocation, the battery charges only from surplus PV energy and discharges only to meet residual member demand. Grid charging is excluded, ensuring that the measured storage value reflects the shifting of community PV generation rather than a separate grid-arbitrage activity.

\subsubsection{Allocation-Consistent Community Flow Definitions}
\label{subsec:allocation_consistent_flows}

Collective self-consumption is settled for each participant, and dispatch is based on the member-level flows obtained after implementing the static coefficients. Direct PV use, allocated surplus, and residual demand are defined as

\begin{align}
D^{\mathrm{PV}}_{i,t} &= \min\!\left(L_{i,t},G^{\mathrm{alloc}}_{i,t}\right),\label{eq:direct_pv_member_bess}\\
U_{i,t} &= \max\!\left(G^{\mathrm{alloc}}_{i,t}-L_{i,t},0\right),\label{eq:surplus_pv_member}\\
D_{i,t} &= \max\!\left(L_{i,t}-G^{\mathrm{alloc}}_{i,t},0\right).\label{eq:deficit_pv_member}
\end{align}

The community totals used by the battery controller are

\begin{align}
U_t &= \sum_i U_{i,t},\label{eq:allocated_surplus_total}\\
D_t &= \sum_i D_{i,t},\label{eq:allocated_deficit_total}\\
D^{\mathrm{PV}}_t &= \sum_i D^{\mathrm{PV}}_{i,t}.\label{eq:direct_pv_total}
\end{align}

This formulation avoids offsetting imports and exports across participants. Under static allocation, one member may export allocated PV surplus while another imports during the same hour; therefore, using only $\max(G_t-L_t,0)$ would overstate direct community balancing.

\subsubsection{Community Energy Balance and State of Charge}
\label{subsec:bess_community_energy_balance}

At the accounting boundary, the community energy balance is

\begin{equation}
\label{eq:bess_community_energy_balance}
G_t + I^{\mathrm{BESS}}_t + P^{\mathrm{dis}}_t
=
L_t + E^{\mathrm{BESS}}_t + P^{\mathrm{ch}}_t.
\end{equation}

Here, $P^{\mathrm{ch}}_t$ is bus-side PV energy sent to the charger and $P^{\mathrm{dis}}_t$ is bus-side energy delivered from the battery to participant demand. It is important to note that conversion losses are set only in the state-of-charge equation:

\begin{equation}
\label{eq:bess_soc_update}
S_t=S_{t-1}+\eta^{\mathrm{ch}}P^{\mathrm{ch}}_t-
\frac{P^{\mathrm{dis}}_t}{\eta^{\mathrm{dis}}}.
\end{equation}

This convention ensures losses are not counted twice.

\subsubsection{Battery Operating Bounds}
\label{subsec:battery_operating_bounds}

\begin{align}
S_{\min} &\leq S_t \leq S_{\max},\label{eq:soc_bounds}\\
0 &\leq P^{\mathrm{ch}}_t \leq P^{\mathrm{ch,max}},\qquad
0 \leq P^{\mathrm{dis}}_t \leq P^{\mathrm{dis,max}},\label{eq:power_bounds}\\
P^{\mathrm{ch}}_tP^{\mathrm{dis}}_t &=0.\label{eq:no_simultaneous_charge_discharge}
\end{align}

For an application with charge and discharge C-rates $c^{\mathrm{ch}}$ and $c^{\mathrm{dis}}$, the corresponding power limits may be defined as

\begin{align}
P^{\mathrm{ch,max}} &= c^{\mathrm{ch}}S_{\max},\label{eq:charge_power_from_c_rate}\\
P^{\mathrm{dis,max}} &= c^{\mathrm{dis}}S_{\max}.\label{eq:discharge_power_from_c_rate}
\end{align}

If the permitted depth of discharge is $d^{\mathrm{DoD}}$, the minimum state of charge is

\begin{equation}
\label{eq:soc_min_from_dod}
S_{\min}=\left(1-d^{\mathrm{DoD}}\right)S_{\max}.
\end{equation}

The initial state of charge is specified as a fraction $s_0$ of the upper limit:

\begin{equation}
\label{eq:initial_soc}
S_0=s_0S_{\max}, \qquad 0\leq s_0\leq1.
\end{equation}

The case-specific C-rates, depth of discharge, initial state-of-charge fraction, and battery capacity are defined in Section~\ref{sec:technology_economic_parameters}. For annual comparisons, the model also reports the difference in terminal SOC, $S_T-S_0$. A sensitivity check may impose $S_T=S_0$ to prevent artificial benefit from ending the simulation at a lower SOC.

\subsubsection{Charging, Discharging, Import, and Export}
\label{subsec:community_surplus_import_export_self_consumption}

The battery charges from allocated PV surplus subject to available headroom:

\begin{equation}
\label{eq:charging_logic}
P^{\mathrm{ch}}_t=
\min\!\left(U_t,P^{\mathrm{ch,max}},
\frac{S_{\max}-S_{t-1}}{\eta^{\mathrm{ch}}}\right).
\end{equation}

After charging,

\begin{equation}
\label{eq:s_after_ch}
S^{\mathrm{after\,ch}}_t=S_{t-1}+\eta^{\mathrm{ch}}P^{\mathrm{ch}}_t.
\end{equation}

Discharge is allowed when residual demand is still present, and the OMIE signal is at or above the attributed threshold:

\begin{equation}
\label{eq:discharging_condition}
D_t>0 \quad \text{and} \quad p^W_t\geq p^{\mathrm{threshold}}.
\end{equation}

When this condition holds,

\begin{equation}
\label{eq:discharging_logic}
P^{\mathrm{dis}}_t=
\min\!\left(D_t,P^{\mathrm{dis,max}},
\eta^{\mathrm{dis}}\left(S^{\mathrm{after\,ch}}_t-S_{\min}\right)\right),
\end{equation}

and otherwise $P^{\mathrm{dis}}_t=0$. The end-of-hour SOC is

\begin{equation}
\label{eq:soc_after_discharge}
S_t=S^{\mathrm{after\,ch}}_t-
\frac{P^{\mathrm{dis}}_t}{\eta^{\mathrm{dis}}}.
\end{equation}

Community import and export are then

\begin{align}
I^{\mathrm{BESS}}_t &= D_t-P^{\mathrm{dis}}_t,\label{eq:bess_import}\\
E^{\mathrm{BESS}}_t &= U_t-P^{\mathrm{ch}}_t.\label{eq:bess_export}
\end{align}

The dispatch limits show $P^{\mathrm{dis}}_t\leq D_t$ and $P^{\mathrm{ch}}_t\leq U_t$ ensuring that both expressions are non-negative.

\subsubsection{Member-Level Allocation of Battery Flows}
\label{subsec:member_level_allocation_bess_flows}

Battery charging is proportionally attributed to members allocated to PV surplus that creates the charging opportunity:

\begin{equation}
\label{eq:allocated_battery_charge}
P^{\mathrm{ch,alloc}}_{i,t}=
\begin{cases}
P^{\mathrm{ch}}_t\dfrac{U_{i,t}}{U_t}, & U_t>0,\\[2mm]
0, & U_t=0.
\end{cases}
\end{equation}

Battery discharge is attributed to members in proportion to residual demand:

\begin{equation}
\label{eq:allocated_battery_discharge_positive}
P^{\mathrm{dis,alloc}}_{i,t}=
\begin{cases}
P^{\mathrm{dis}}_t\dfrac{D_{i,t}}{D_t}, & D_t>0,\\[2mm]
0, & D_t=0.
\end{cases}
\end{equation}

The resulting member-level import and export are

\begin{align}
I^{\mathrm{BESS}}_{i,t} &= D_{i,t}-P^{\mathrm{dis,alloc}}_{i,t},\label{eq:bess_import_member}\\
E^{\mathrm{BESS}}_{i,t} &= U_{i,t}-P^{\mathrm{ch,alloc}}_{i,t}.\label{eq:bess_export_member}
\end{align}

These definitions satisfy

\begin{equation}
\label{eq:member_flow_closure}
\sum_i I^{\mathrm{BESS}}_{i,t}=I^{\mathrm{BESS}}_t,
\qquad
\sum_i E^{\mathrm{BESS}}_{i,t}=E^{\mathrm{BESS}}_t.
\end{equation}

\subsection{Battery Dispatch Logic}
\label{sec:battery_dispatch_logic}

The controller is a transparent set of predefined operating rules rather than an optimisation model. A selected wholesale-price series may be used to rank hours for discharge, but it is kept separate from the retail prices used for billing. In the Spanish application, the OMIE day-ahead series provides this dispatch signal and does not directly value PVPC imports or exports \cite{omie2025omie}. The discharge threshold is defined as a configurable percentile of the annual price distribution; the selected percentile for the Seville application is reported in Section~\ref{sec:technology_economic_parameters}.

\subsection{Community Energy Balance and Performance Accounting}
\label{sec:community_energy_balance_validation}

\subsubsection{Complete Energy Balance}
\label{subsec:complete_energy_balance}

Equation~\eqref{eq:bess_community_energy_balance} reduces to the PV-only and No-DER balances as follows:

\begin{align}
\text{PV-only:}\quad G_t+I^{\mathrm{PV}}_t &= L_t+E^{\mathrm{PV}}_t,\label{eq:pv_only_balance_reduction}\\
\text{No-DER:}\quad I^0_t &= L_t.\label{eq:no_der_balance_reduction}
\end{align}

\subsubsection{Performance Accounting}
\label{subsec:annual_accounting}

To avoid ambiguity, two complementary local-use indicators are reported. The self-consumption ratio measures the share of PV generation used directly or sent to the battery:

\begin{equation}
\label{eq:scr_general}
SCR=\frac{\sum_t\left(D^{\mathrm{PV}}_t+P^{\mathrm{ch}}_t\right)}{\sum_t G_t}
=1-\frac{\sum_t E_t}{\sum_tG_t}.
\end{equation}

The self-sufficiency ratio measures the share of demand served directly by PV or by battery discharge:

\begin{equation}
\label{eq:ssr_general}
SSR=\frac{\sum_t\left(D^{\mathrm{PV}}_t+P^{\mathrm{dis}}_t\right)}{\sum_t L_t}.
\end{equation}

Battery losses are therefore reflected in the difference between PV energy charged and useful discharge delivered. The annual battery throughput and equivalent full cycles are

\begin{align}
E^{\mathrm{dis}}_{\mathrm{annual}} &= \sum_tP^{\mathrm{dis}}_t,\label{eq:annual_discharge}\\
N_{\mathrm{EFC}} &= \frac{E^{\mathrm{dis}}_{\mathrm{annual}}}{S_{\max}-S_{\min}}.\label{eq:equivalent_full_cycles}
\end{align}

The incremental technical contribution of storage is reported as

\begin{align}
\Delta SCR_{\mathrm{BESS}} &= SCR_{\mathrm{PV\mbox{-}BESS}}-SCR_{\mathrm{PV\mbox{-}only}},\label{eq:delta_scr_bess}\\
\Delta SSR_{\mathrm{BESS}} &= SSR_{\mathrm{PV\mbox{-}BESS}}-SSR_{\mathrm{PV\mbox{-}only}}.\label{eq:delta_ssr_bess}
\end{align}

\subsection{Spanish Settlement and Billing Model}
\label{sec:spanish_settlement_billing_model}

This section converts hourly member-level energy flows into monthly and annual bills under the Spanish PVPC tariff and the RD~244/2019 simplified compensation mechanism. OMIE is used only as a battery dispatch signal \cite{omie2025omie}; it is not used to value PVPC baseline imports or exports.

\subsubsection{PVPC Import Price and Billing Boundary}
\label{subsec:pvpc_import_billing_boundary}

The baseline billing boundary includes only variable energy cashflows. Grid imports are valued using the selected hourly PVPC variable energy-price series, $p^{\mathrm{imp}}_t$. Fixed power charges, meter rental, VAT, electricity tax, and other non-energy items are excluded because they are not altered by hourly PV or battery operation. The compensation cap is therefore applied against the same modelled monthly import-energy cost used in the scenario comparison.

This boundary does not represent a complete retail invoice. Any later extension that adds fixed charges or taxes must report them separately and must not imply that they are avoided by self-consumption.

\subsubsection{PVPC Excedentaria Export Credit}
\label{subsec:pvpc_excedentaria_export_credit}

Surplus exports are valued using the PVPC excedentaria export-credit price, $p^{\mathrm{exp}}_t$, published by REE/ESIOS \cite{reendprecio}. This export credit is generally lower than the import price because it does not include the full retail components avoided through self-consumption. Therefore, direct self-consumption and battery-enabled surplus shifting are typically more valuable than exporting surplus energy.

\subsubsection{Member-Level Monthly Compensation Cap}
\label{subsec:member_level_monthly_compensation_cap}

For each household $i$ and month $m$, the model calculates import cost, raw export compensation, applied export compensation, and net monthly energy bill as follows:

\begin{equation}
\label{eq:monthly_import_cost}
C^{\mathrm{imp}}_{i,m} = \sum_{t \in m} I_{i,t}p^{\mathrm{imp}}_t,
\end{equation}

\begin{equation}
\label{eq:raw_export_compensation}
R^{\mathrm{raw}}_{i,m} = \sum_{t \in m} E_{i,t}p^{\mathrm{exp}}_t,
\end{equation}

\begin{equation}
\label{eq:applied_export_compensation}
R^{\mathrm{applied}}_{i,m} = \min\left(R^{\mathrm{raw}}_{i,m}, C^{\mathrm{imp}}_{i,m}\right),
\end{equation}

\begin{equation}
\label{eq:net_monthly_energy_bill}
B_{i,m} = C^{\mathrm{imp}}_{i,m} - R^{\mathrm{applied}}_{i,m},
\end{equation}

\begin{equation}
\label{eq:community_monthly_bill}
B^{\mathrm{community}}_m = \sum_i B_{i,m},
\end{equation}

\begin{equation}
\label{eq:annual_bill}
B^{\mathrm{annual}} = \sum_{m=1}^{12} B^{\mathrm{community}}_m.
\end{equation}

The cap is applied at member level because each participant has an individual billing relationship. A member with high export credit and low import cost cannot transfer unused compensation to another member. This prevents hidden cross-subsidization and makes the member-level benefit analysis consistent with the settlement boundary.

\subsubsection{Forfeited Compensation and Cap-Binding Events}
\label{subsec:forfeited_compensation_cap_binding}

\begin{equation}
\label{eq:lost_compensation}
\mathrm{Lost}_{i,m} = R^{\mathrm{raw}}_{i,m} - R^{\mathrm{applied}}_{i,m},
\end{equation}

\begin{equation}
\label{eq:cap_binding}
\mathrm{CapBind}_{i,m} =
\begin{cases}
1, & R^{\mathrm{raw}}_{i,m} > C^{\mathrm{imp}}_{i,m}, \\
0, & \text{otherwise},
\end{cases}
\end{equation}

\begin{equation}
\label{eq:annual_lost_compensation}
\mathrm{Lost}_{\mathrm{annual}} = \sum_i \sum_m \mathrm{Lost}_{i,m}.
\end{equation}

These quantities identify months and members for which the simplified compensation cap binds. They are important for RQ2 because one battery-specific value mechanism is the reduction of forfeited export compensation: surplus PV that would otherwise be exported and partly forfeited can instead be stored and used later to avoid imports.

\subsubsection{Bill Savings and Battery-Specific Bill Savings}
\label{subsec:bill_savings_battery_specific}

\begin{equation}
\label{eq:scenario_saving}
\mathrm{Saving}_{\mathrm{scenario}} = B^{\mathrm{No\mbox{-}DER}} - B^{\mathrm{scenario}},
\end{equation}

\begin{equation}
\label{eq:scenario_saving_pct}
\mathrm{SavingPct}_{\mathrm{scenario}} = \frac{\mathrm{Saving}_{\mathrm{scenario}}}{B^{\mathrm{No\mbox{-}DER}}},
\end{equation}

\begin{equation}
\label{eq:bess_specific_saving}
\mathrm{Saving}_{\mathrm{BESS\mbox{-}specific}} = B^{\mathrm{PV\mbox{-}only}} - B^{\mathrm{PV\mbox{-}BESS}}.
\end{equation}

Equation~\eqref{eq:bess_specific_saving} is the core bill-based measure of battery-specific value. Economic metrics such as NPV and payback period are developed in Section~\ref{sec:economic-framework} using these annual savings and the investment-cost assumptions.
\subsection{Economic and Allocation Formulation}
\label{sec:economic-framework}

This chapter converts the participant-level monthly settlement outputs developed in Section~\ref{sec:spanish_settlement_billing_model} into project-level and member-level economic indicators. The hourly energy-flow model is not recalculated here. Instead, the annual bills obtained for the No-DER, PV-only, and PV--BESS configurations are combined with the technology-cost assumptions defined in Section~\ref{sec:technology_economic_parameters}.

All scenarios retain identical demand, PV generation, price series, tariff rules, allocation coefficients, and evaluation periods. Consequently, differences between the PV--BESS and PV-only configurations can be attributed to the addition of battery storage rather than to changes in the underlying assumptions. The billing boundary remains limited to variable energy cashflows: fixed power charges, meter rental, taxes, and other invoice components excluded in Section~\ref{subsec:pvpc_import_billing_boundary} are not treated as avoidable savings in this chapter.

\subsubsection{Economic Evaluation Metrics}
\label{sec:ch5_economic_metrics}

The economic assessment uses the following indicators.

\textbf{Annual bill savings.} Annual bill savings measure the reduction in the modelled variable-energy bill relative to the No-DER baseline. Savings are calculated both for the community and for each participant.

\textbf{Net Present Value.} Net Present Value (NPV) measures the present value of bill savings net of capital and operating costs over the 15-year project horizon. A positive NPV indicates that discounted benefits exceed discounted costs within the defined assessment boundary.

\textbf{Simple payback period.} The simple payback period is the first year in which cumulative undiscounted net savings recover the initial investment.

\textbf{Discounted payback period.} The discounted payback period is the first year in which cumulative discounted net savings recover the initial investment.

\textbf{Benefit--Cost Ratio.} The Benefit--Cost Ratio (BCR) compares the present value of bill savings with the present value of capital and operating costs. A value greater than one indicates that discounted benefits exceed discounted costs.

\textbf{Battery-specific value.} Battery-specific value is evaluated by comparing PV--BESS directly with PV-only under identical inputs. The principal indicators are battery-specific annual bill savings, incremental NPV, and battery-specific payback.

The Self-Consumption Ratio and Self-Sufficiency Ratio are retained as technical performance indicators and are calculated using Equations~\eqref{eq:scr_general} and~\eqref{eq:ssr_general}. They are not treated as monetary benefits unless their effect is already reflected in the participant-level import and export bills.

Levelized Cost of Energy is not used as the primary viability indicator because this thesis evaluates avoided electricity expenditure and participant-level settlement for a combined PV--BESS system rather than the cost of electricity produced by a single generation technology.

\subsubsection{Bill Savings Calculation}
\label{sec:ch5_bill_savings}

Let $s\in\{\mathrm{PV},\mathrm{PV\mbox{-}BESS}\}$ denote a project configuration. The annual bill of participant $i$ under configuration $s$ is obtained by summing the monthly bills defined in Equation~\eqref{eq:net_monthly_energy_bill}:

\begin{equation}
B_i^{s}=\sum_{m=1}^{12}B_{i,m}^{s}.
\label{eq:ch5_member_annual_bill}
\end{equation}

The corresponding annual community bill is

\begin{equation}
B^{s}=\sum_{i=1}^{N}B_i^{s}.
\label{eq:ch5_community_annual_bill}
\end{equation}

The participant-level annual bill saving relative to No-DER is

\begin{equation}
BS_i^{s}=B_i^{0}-B_i^{s},
\label{eq:ch5_member_bill_saving}
\end{equation}

and the community-level annual bill saving is

\begin{equation}
BS^{s}=\sum_{i=1}^{N}BS_i^{s}=B^{0}-B^{s}.
\label{eq:ch5_community_bill_saving}
\end{equation}

These quantities are consistent with the community-level saving already defined in Equation~\eqref{eq:scenario_saving}. Because the monthly compensation cap is applied before annual aggregation, $B_i^{s}$ already incorporates participant-level import cost, raw export compensation, applied export compensation, and forfeited compensation.

The battery-specific annual bill saving of participant $i$ is

\begin{equation}
BS_i^{\mathrm{BESS}}=B_i^{\mathrm{PV}}-B_i^{\mathrm{PV\mbox{-}BESS}},
\label{eq:ch5_member_bess_bill_saving}
\end{equation}

while the community-level battery-specific annual bill saving is

\begin{equation}
BS^{\mathrm{BESS}}=\sum_{i=1}^{N}BS_i^{\mathrm{BESS}}
=B^{\mathrm{PV}}-B^{\mathrm{PV\mbox{-}BESS}}.
\label{eq:ch5_community_bess_bill_saving}
\end{equation}

Equation~\eqref{eq:ch5_community_bess_bill_saving} is equivalent to Equation~\eqref{eq:bess_specific_saving}. A positive value indicates that the battery reduces the modelled annual community bill relative to PV-only.

The baseline economic analysis is expressed in real terms. The representative-year bill savings are therefore repeated over the 15-year project horizon without an automatic escalation factor:

\begin{equation}
BS_{i,y}^{s}=BS_i^{s},
\qquad
BS_y^{s}=BS^{s},
\qquad y=1,\ldots,H.
\label{eq:ch5_repeated_real_bill_savings}
\end{equation}

Electricity-price sensitivities are implemented by recalculating the underlying bills under the price scenarios defined in Section~\ref{sec:experimental}, rather than by applying an unverified annual escalation rate after settlement.

\subsubsection{Capital and Operating Cost Model}
\label{sec:ch5_cost_model}

Let $P_{\mathrm{PV}}$ denote installed PV capacity in kWp and $E_{\mathrm{BESS}}$ denote nominal battery energy capacity in kWh. Let $c_{\mathrm{PV}}$ and $c_{\mathrm{BESS}}$ denote the corresponding installed unit costs in EUR/kWp and EUR/kWh. The initial investment for the PV-only configuration is

\begin{equation}
C_0^{\mathrm{PV}}=c_{\mathrm{PV}}P_{\mathrm{PV}},
\label{eq:ch5_pv_capex}
\end{equation}

and the initial investment for the PV--BESS configuration is

\begin{equation}
C_0^{\mathrm{PV\mbox{-}BESS}}
=c_{\mathrm{PV}}P_{\mathrm{PV}}+c_{\mathrm{BESS}}E_{\mathrm{BESS}}.
\label{eq:ch5_pv_bess_capex}
\end{equation}

The installed unit-cost assumptions are treated as inclusive project-cost inputs. Separate module, inverter, balance-of-system, installation, and development costs are not added again unless they are explicitly separated in the scenario register, thereby avoiding double counting.

The annual PV operation and maintenance cost is

\begin{equation}
O_y^{\mathrm{PV}}=o_{\mathrm{PV}}P_{\mathrm{PV}},
\label{eq:ch5_pv_opex}
\end{equation}

where $o_{\mathrm{PV}}$ is the annual PV O\&M cost in EUR/kWp/year. Under the baseline assumptions currently defined in Section~\ref{sec:technology_economic_parameters}, no separate BESS O\&M parameter is added. Therefore,

\begin{equation}
O_y^{\mathrm{PV\mbox{-}BESS}}=O_y^{\mathrm{PV}}.
\label{eq:ch5_pv_bess_opex}
\end{equation}

If a separate BESS O\&M assumption is introduced in the scenario register, it must be added explicitly and applied consistently to every PV--BESS scenario.

Consistent with the scope of the thesis, the baseline cost model does not include PV or battery degradation, battery replacement scheduling, inverter replacement, financing costs, or terminal residual value. These items must not be introduced in selected scenarios without also updating the common assessment boundary.

\subsubsection{Net Present Value and Payback}
\label{sec:ch5_npv_payback}

Let $H=15$ years denote the project horizon and let $r$ denote the real discount rate defined in Section~\ref{sec:technology_economic_parameters}. The annual net cash benefit of configuration $s$ in year $y$ is

\begin{equation}
CF_y^{s}=BS_y^{s}-O_y^{s}.
\label{eq:ch5_scenario_cash_flow}
\end{equation}

The project-level NPV of configuration $s$ relative to No-DER is

\begin{equation}
NPV^{s}=-C_0^{s}+\sum_{y=1}^{H}\frac{CF_y^{s}}{(1+r)^y}.
\label{eq:ch5_project_npv}
\end{equation}

The simple payback period is the smallest year $n\leq H$ satisfying

\begin{equation}
\sum_{y=1}^{n}CF_y^{s}\geq C_0^{s}.
\label{eq:ch5_simple_payback}
\end{equation}

The discounted payback period is the smallest year $n\leq H$ satisfying

\begin{equation}
\sum_{y=1}^{n}\frac{CF_y^{s}}{(1+r)^y}\geq C_0^{s}.
\label{eq:ch5_discounted_payback}
\end{equation}

Where the relevant threshold is not reached within 15 years, payback is reported as not achieved within the project horizon rather than extrapolated beyond the assessment boundary.

The project-level BCR is

\begin{equation}
BCR^{s}=
\frac{\displaystyle\sum_{y=1}^{H}\frac{BS_y^{s}}{(1+r)^y}}
{\displaystyle C_0^{s}+\sum_{y=1}^{H}\frac{O_y^{s}}{(1+r)^y}}.
\label{eq:ch5_project_bcr}
\end{equation}

A BCR greater than one and a positive NPV provide equivalent accept/reject signals under the same cash-flow boundary, although they communicate profitability in different forms.

\subsubsection{Battery-Specific Value and Compensation-Cap Effects}
\label{sec:ch5_battery_value}

The incremental capital cost attributable to the battery is

\begin{equation}
\Delta C_0^{\mathrm{BESS}}
=C_0^{\mathrm{PV\mbox{-}BESS}}-C_0^{\mathrm{PV}}
=c_{\mathrm{BESS}}E_{\mathrm{BESS}}.
\label{eq:ch5_incremental_bess_capex}
\end{equation}

The incremental annual operating cost is

\begin{equation}
\Delta O_y^{\mathrm{BESS}}
=O_y^{\mathrm{PV\mbox{-}BESS}}-O_y^{\mathrm{PV}}.
\label{eq:ch5_incremental_bess_opex}
\end{equation}

Under the baseline cost assumptions, $\Delta O_y^{\mathrm{BESS}}=0$. The battery-specific incremental NPV is

\begin{align}
\Delta NPV^{\mathrm{BESS}}
&=NPV^{\mathrm{PV\mbox{-}BESS}}-NPV^{\mathrm{PV}} \nonumber\\
&=-\Delta C_0^{\mathrm{BESS}}
+\sum_{y=1}^{H}
\frac{BS_y^{\mathrm{BESS}}-\Delta O_y^{\mathrm{BESS}}}{(1+r)^y}.
\label{eq:ch5_incremental_bess_npv}
\end{align}

A positive $\Delta NPV^{\mathrm{BESS}}$ indicates that the additional discounted bill savings created by storage exceed the incremental battery cost within the 15-year horizon.

Battery-specific payback is calculated against the incremental battery investment. The simple battery payback is the smallest $n\leq H$ satisfying

\begin{equation}
\sum_{y=1}^{n}
\left(BS_y^{\mathrm{BESS}}-\Delta O_y^{\mathrm{BESS}}\right)
\geq \Delta C_0^{\mathrm{BESS}},
\label{eq:ch5_bess_simple_payback}
\end{equation}

and the discounted battery payback is the smallest $n\leq H$ satisfying

\begin{equation}
\sum_{y=1}^{n}
\frac{BS_y^{\mathrm{BESS}}-\Delta O_y^{\mathrm{BESS}}}{(1+r)^y}
\geq \Delta C_0^{\mathrm{BESS}}.
\label{eq:ch5_bess_discounted_payback}
\end{equation}

The annual bill effect of the battery can be decomposed without double counting. The avoided import-cost component is

\begin{equation}
V_y^{\mathrm{imp}}=
\sum_{i=1}^{N}\sum_{m=1}^{12}
\left(C_{i,m}^{\mathrm{imp,PV}}-C_{i,m}^{\mathrm{imp,PV\mbox{-}BESS}}\right),
\label{eq:ch5_avoided_import_value}
\end{equation}

and the change in applied export compensation is

\begin{equation}
\Delta R_y^{\mathrm{applied}}=
\sum_{i=1}^{N}\sum_{m=1}^{12}
\left(R_{i,m}^{\mathrm{applied,PV\mbox{-}BESS}}
-R_{i,m}^{\mathrm{applied,PV}}\right).
\label{eq:ch5_change_applied_export_credit}
\end{equation}

The exact accounting identity is

\begin{equation}
BS_y^{\mathrm{BESS}}=V_y^{\mathrm{imp}}+\Delta R_y^{\mathrm{applied}}.
\label{eq:ch5_bess_bill_identity}
\end{equation}

Battery charging generally reduces exports and therefore may reduce applied export compensation, while battery discharge reduces grid-import cost. Equation~\eqref{eq:ch5_bess_bill_identity} captures both effects once and prevents the same shifted kilowatt-hour from being counted separately as time-shifting value, export-displacement value, and self-consumption value.

The change in forfeited compensation is reported as a diagnostic indicator:

\begin{equation}
\Delta Lost_y^{\mathrm{BESS}}=
Lost_y^{\mathrm{PV}}-Lost_y^{\mathrm{PV\mbox{-}BESS}}.
\label{eq:ch5_reduction_forfeited_compensation}
\end{equation}

This quantity helps explain the effect of the monthly cap, but it is not added to Equation~\eqref{eq:ch5_bess_bill_identity}, because its financial effect is already contained in the applied export compensation and final bills.

\subsubsection{Static Allocation Coefficients}
\label{sec:ch5_static_allocation}

This chapter does not introduce a second energy-allocation rule. The same static coefficients $\beta_i$ used in the hourly model are retained throughout the economic assessment. They are non-negative, sum to one, and are proportional to annual household demand as defined in Equations~\eqref{eq:beta_condition} and~\eqref{eq:beta_annual_demand}.

Shared PV generation is allocated before participant-level self-consumption, imports, exports, battery charging, battery discharge, and monthly compensation are calculated. Therefore, economic benefits are derived from the participant-level bills produced by the settlement model; they are not obtained by dividing an aggregate community bill after settlement.

For the baseline ownership and cost-sharing arrangement, each participant's share of scenario capital cost is

\begin{equation}
C_{0,i}^{s}=\beta_i C_0^{s},
\label{eq:ch5_member_capex_share}
\end{equation}

and the participant's share of annual operating cost is

\begin{equation}
O_{i,y}^{s}=\beta_i O_y^{s}.
\label{eq:ch5_member_opex_share}
\end{equation}

These allocations satisfy

\begin{equation}
\sum_{i=1}^{N}C_{0,i}^{s}=C_0^{s},
\qquad
\sum_{i=1}^{N}O_{i,y}^{s}=O_y^{s}.
\label{eq:ch5_cost_allocation_closure}
\end{equation}

Alternative ownership or cost-sharing coefficients may be tested as a governance sensitivity, but they must be identified separately from the physical energy-allocation coefficients and must preserve cost-allocation closure.

\subsubsection{Member-Level Benefit Allocation}
\label{sec:ch5_member_benefit_allocation}

Because imports, exports, and compensation are calculated separately for each participant, member-level gross economic benefits are obtained directly from Equation~\eqref{eq:ch5_member_bill_saving}. The annual net cash benefit of participant $i$ under configuration $s$ is

\begin{equation}
CF_{i,y}^{s}=BS_{i,y}^{s}-O_{i,y}^{s}.
\label{eq:ch5_member_cash_flow}
\end{equation}

The member-level NPV is

\begin{equation}
NPV_i^{s}=-C_{0,i}^{s}
+\sum_{y=1}^{H}\frac{CF_{i,y}^{s}}{(1+r)^y}.
\label{eq:ch5_member_npv}
\end{equation}

The allocation framework is internally consistent because

\begin{equation}
\sum_{i=1}^{N}NPV_i^{s}=NPV^{s}.
\label{eq:ch5_member_npv_closure}
\end{equation}

The participant-level battery-specific NPV is

\begin{equation}
\Delta NPV_i^{\mathrm{BESS}}
=NPV_i^{\mathrm{PV\mbox{-}BESS}}-NPV_i^{\mathrm{PV}},
\label{eq:ch5_member_incremental_bess_npv}
\end{equation}

with

\begin{equation}
\sum_{i=1}^{N}\Delta NPV_i^{\mathrm{BESS}}
=\Delta NPV^{\mathrm{BESS}}.
\label{eq:ch5_member_incremental_npv_closure}
\end{equation}

A member-level BCR is calculated as

\begin{equation}
BCR_i^{s}=
\frac{\displaystyle\sum_{y=1}^{H}\frac{BS_{i,y}^{s}}{(1+r)^y}}
{\displaystyle C_{0,i}^{s}+\sum_{y=1}^{H}\frac{O_{i,y}^{s}}{(1+r)^y}}.
\label{eq:ch5_member_bcr}
\end{equation}

Member-level NPV, BCR, annual bill savings, and battery-specific bill savings are reported in Section~\ref{sec:results}. These results reveal whether a configuration that is viable at community level also produces acceptable outcomes for individual participants.

This section establishes a consistent economic bridge between the participant-level settlement model and the scenario analysis. Section~\ref{sec:experimental} applies these definitions across the selected PV penetration, battery CAPEX, electricity price, community size, and community composition cases, while Section~\ref{sec:results} reports the resulting project-level and member-level outcomes.

\subsection{Model Assumptions and Boundary Conditions}
\label{sec:model_assumptions_boundary_conditions}

The general model boundaries are stated explicitly so that the framework can be replicated without over-generalising the resulting conclusions. Numerical values are not fixed in this chapter; the Seville values are provided in Section~\ref{sec:case-study}, while the economic calculations are developed in Section~\ref{sec:economic-framework}.

\begin{longtable}{p{0.30\textwidth}p{0.60\textwidth}}
\caption{General methodological assumptions and configurable elements.}\label{tab:general_methodological_boundaries}\\
\toprule
\textbf{Element} & \textbf{General treatment} \\
\midrule
\endfirsthead
\toprule
\textbf{Element} & \textbf{General treatment} \\
\midrule
\endhead
System boundary & Grid-connected collective self-consumption with shared PV and an optional central community battery. \\
Temporal resolution & A common time step is required for load, PV, prices, allocation, and dispatch. The thesis uses hourly resolution, but the equations remain applicable to another consistent resolution. \\
Scenario consistency & No-DER, PV-only, and PV--BESS are evaluated using identical demand, PV, prices, tariff rules, allocation coefficients, and evaluation periods. \\
Allocation & Static non-negative coefficients summing to one are used in the baseline. Alternative static or dynamic rules can replace them if participant-level closure is maintained. \\
Battery charging source & The battery charges from allocated PV surplus only; grid charging is excluded from the baseline. \\
Battery representation & State of charge, power limits, efficiency, depth of discharge, and initial and terminal conditions are explicit input parameters. Detailed electrochemical degradation is outside the baseline. \\
Dispatch & Rule-based operation is used. A configurable price threshold may rank discharge hours, but the dispatch-price signal is separated from retail billing prices. \\
Settlement & Imports and exports are calculated for each participant before monthly settlement. The Spanish application implements the RD~244/2019 simplified-compensation cap and no carry-over. \\
Economic boundary & The hourly model passes annual bill and energy outputs to the economic framework. CAPEX, OPEX, project horizon, and discount rate are configurable application inputs. \\
Network representation & Voltage, thermal, transformer, protection, and power-quality constraints are not modelled. \\
Validation & Hourly energy balance, state-of-charge limits, non-negativity, member-level flow closure, allocation closure, monthly compensation limits, and scenario consistency are checked. \\
\bottomrule
\end{longtable}

The framework provides separation between the reusable computational method and the application-specific inputs. It is possible to reproduce another collective self-consumption case by replacing the input datasets and parameter register, selecting the relevant settlement module, and re-running the same sequence of hourly, monthly, and annual calculations.

This section has established the mathematical and computational framework used to compare No-DER, PV-only, and PV--BESS scenarios and to extract the incremental contribution/value of battery storage. Section~\ref{sec:case-study} now applies this framework to the specific case of the Seville community and defines the datasets, participant composition, technology parameters, and data architecture implemented in this research.
```
