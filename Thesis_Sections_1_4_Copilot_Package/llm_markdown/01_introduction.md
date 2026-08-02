---
chapter: 1
title: "Introduction"
canonical_source: "../canonical_tex/01_introduction.tex"
content_policy: "Exact LaTeX embedded below; no prose replacement"
---

# Chapter 1: Introduction

```latex
\subsection{Motivation}
\label{subsec:motivation}

The growing deployment of residential photovoltaic generation in Spain
has increased the opportunities for households to produce and consume
renewable electricity locally. However, the temporal mismatch between PV
generation and household demand means that part of the generated
electricity may be exported while electricity is still imported from the
grid during other periods. Battery energy storage can reduce this
mismatch by shifting surplus PV generation to periods of higher demand,
but its additional investment cost does not necessarily result in
sufficient economic benefit.

This question becomes more complex under collective self-consumption,
where shared PV generation is distributed among participants through
allocation coefficients and each participant's imports, exports, and
compensation are calculated separately. Consequently, the value of a
shared BESS depends not only on its technical operation but also on PV
capacity, battery cost, electricity-price conditions, participant number
and composition, allocation arrangements, and the application of the
Spanish simplified-compensation mechanism.

The motivation of this thesis is therefore to determine the technical,
economic, and community conditions under which a shared BESS provides
measurable additional value beyond a PV-only system in Spanish
residential collective self-consumption. A consistent comparison of
No-DER, PV-only, and PV--BESS scenarios is required to isolate the
battery-specific contribution and support informed investment and
allocation decisions.

\subsection{Background and Context}\label{background-and-context}

The transition toward decentralized energy systems has increased interest
in both Energy Communities (ECs) and Collective Self-Consumption (CSC) as
mechanisms for advancing decarbonization, citizen participation, and local
energy use. In the European context, energy communities
are increasingly understood as arrangements where consumers and
prosumers collectively generate, consume, share, and manage energy for
local benefit \cite{ch1ref001}. In Spain, the regulatory framework established by
Royal Decree (RD) 244/2019 has supported the adoption of
self-consumption and collective self-consumption arrangements by
defining the administrative, technical, and economic conditions \cite{ch1ref002}.

Distributed photovoltaic (PV) generation is central to this transition
because it enables households and communities to become active
participants in electricity production rather than passive consumers.
However, PV generation is variable and often concentrated during daytime
periods, while residential demand may occur partly in the evening. This
mismatch creates periods of surplus generation and periods of residual
grid import. As a result, the value of PV in residential communities
depends not only on annual generation, but also on the temporal
alignment between generation, demand, and settlement prices.

Battery Energy Storage Systems (BESS) can address this mismatch by
storing surplus PV generation and discharging it later to meet demand or
avoid higher-value grid imports. The literature shows that storage can
improve self-consumption, support load shifting, and create limited
arbitrage opportunities, but its financial value depends strongly on the
retail import price, export remuneration, battery cost, and system
utilization \cite{ch1ref003}, \cite{ch1ref004}. At community scale, a shared or community
battery energy storage system (CBESS) can exploit diversity in household
demand profiles and may reduce the need for oversized individual
batteries. Nevertheless, the economic case for CBESS is not automatic;
it must be tested against a PV-only baseline under the same settlement
conditions.

The Spanish setting is especially relevant because PV-BESS value is
shaped by both wholesale market signals and retail settlement rules.
Imports are valued in this thesis using the full Precio Voluntario para
el Pequeño Consumidor (PVPC) price in €/kWh as published, while exports
are valued under the simplified compensation mechanism associated with
RD 244/2019 \cite{ch1ref002}, \cite{ch1ref005}. The OMIE day-ahead market provides the
wholesale price signal used for dispatch representation, and since
October 2025 the day-ahead market has operated with 15-minute Market
Time Units (MTU15) \cite{ch1ref006}. In addition, PVPC final energy price
publication is available at quarter-hourly resolution from 2026 \cite{ch1ref007}.
To maintain a transparent simulation structure, this thesis stores
available price inputs at their native resolution and aggregates them to
an hourly time-step for the simulation backbone.

\subsection{Problem Definition and Research
Gap}\label{problem-definition-and-research-gap}

Although PV and PV-BESS systems have been widely studied, the literature
review shows that results are highly dependent on tariff structures,
export compensation mechanisms, battery capital cost, and modeling
assumptions. Spanish studies such as Codina et al.~\cite{ch1ref008} examine the
profitability of domestic solar investment, while Fuster-Palop et al.
\cite{ch1ref009} analyze urban PV potential under net billing and net metering
conditions. However, a gap remains in explicitly modelling
community-scale PV-BESS under Spanish simplified compensation rules
while also quantifying the incremental value of storage relative to a
PV-only counterfactual.

A central reason this problem is non-trivial is the simplified
compensation mechanism introduced under RD 244/2019. Under this
framework, exported surplus energy is credited, but the value of export
compensation cannot exceed the value of imported energy in the same
billing period. In practical terms, this creates a monthly export-credit
cap and no carry-over of unused credits to later months \cite{ch1ref002}.
Therefore, surplus PV that cannot be self-consumed or economically
credited may lose value. This ``use-it-or-lose-it'' feature is
particularly important for PV-BESS assessment because storage can shift
surplus generation into later demand periods, but only if the additional
savings justify the battery investment.

Many PV-BESS models approximate export remuneration using generalized
net-metering or net-billing assumptions. These assumptions can be
inappropriate for Spain if they do not enforce the monthly cap or if
they treat exported electricity as fully monetizable. Such
simplification can overstate the value of storage, underestimate the
importance of self-consumption, or misidentify sizing thresholds. The
literature also shows that the value of batteries is often discussed
together with PV value, without clearly isolating what the battery
itself contributes \cite{ch1ref010}, \cite{ch1ref011}. This makes it difficult for
community organizers to determine whether a PV-BESS system is genuinely
superior to a PV-only configuration.

The specific research gap addressed in this thesis is therefore the lack
of a Spain-specific, PV-only-benchmarked, battery-value-decomposed, and
sensitivity-tested techno-economic assessment of community PV-BESS
systems. Addressing this gap requires: (i) explicit implementation of
Spanish import/export settlement rules, including the monthly cap; (ii)
a transparent comparison between no-DER, PV-only, and PV-BESS cases; and
(iii) a structured sensitivity analysis across battery CAPEX, PV
penetration, and community composition.

\subsection{Research Questions and Objectives}

This thesis examines whether shared battery storage creates additional value when added to residential collective self-consumption under Spanish settlement rules. It addresses the following research questions:

\begin{itemize}
    \item \textbf{RQ1:} Under what conditions does a shared BESS provide incremental value over a PV-only configuration?

    \item \textbf{RQ2:} How much value is attributable specifically to the
    battery, and how is it affected by the monthly compensation cap under
    RD~244/2019?

    \item \textbf{RQ3:} How sensitive are the results to PV penetration,
    battery CAPEX, electricity prices, community size, and participant
    composition?
\end{itemize}

\textbf{Overall objective:} To evaluate the techno-economic viability of adding shared battery storage to a residential collective self-consumption arrangement in Seville, Spain, relative to a PV-only configuration.

\textbf{Specific objectives:}

\begin{itemize}
    \item Develop an hourly simulation comparing No-DER, PV-only, and PV--BESS configurations under identical assumptions.

    \item Implement PVPC import valuation and simplified surplus compensation, including the monthly cap and no carry-over.

    \item Evaluate technical and economic performance using energy flows, self-consumption, bill savings, NPV, and payback period.

    \item Isolate battery-specific value by comparing PV--BESS directly with PV-only.

    \item Assess sensitivity to PV penetration, battery CAPEX, electricity prices, community size, and participant composition.
\end{itemize}

\subsection{Scope of the Study}\label{scope-of-the-study}

The scope of this thesis is deliberately delimited to ensure that the
analysis remains focused, technically rigorous, and grounded in
transparent empirical and modelled datasets and Spanish regulatory
conditions. The study focuses on grid-connected residential collective
self-consumption in Seville, Spain, involving 10--50 households that
share photovoltaic generation and a centralized battery energy storage
system.

The operational assessment covers the period from 1 January 2013 at
00:00 to 31 December 2013 at 23:00. The regulatory and tariff boundary
reflects the Spanish collective self-consumption framework applicable in
2026, particularly the simplified compensation mechanism established
under RD~244/2019. The economic assessment covers a 15-year project
horizon and is limited to the energy-related costs and benefits
associated with shared PV generation and battery storage.

The study evaluates grid imports and exports, self-consumption,
self-sufficiency, electricity-bill savings, Net Present Value, payback
period, and the incremental value attributable to battery storage. It
also considers variations in PV penetration, battery CAPEX, electricity
prices, participant numbers, and community composition.

The study excludes standalone and grid-charged battery systems, electric
vehicles, vehicle-to-grid operation, hydrogen and thermal storage,
demand response, ancillary-service revenues, islanded operation, and
resilience or backup-power valuation. Detailed distribution-network
analysis, including voltage constraints, transformer loading, protection
requirements, and power-flow effects, is also outside the scope.
Battery and PV degradation, battery replacement scheduling, dynamic
allocation mechanisms, and alternative retail contracts are not
considered.
```
