# Literature Review — Excerpt (medium)

This curated medium-length excerpt synthesises key themes from the Literature Review, highlighting prior work relevant to co-located PV and battery energy storage systems (BESS) in energy communities, common modelling approaches, economic frameworks, and identified research gaps that motivate the thesis.

## Key themes in prior work

- Distributed generation and community energy: Literature shows increasing interest in community-scale energy systems as a means to increase local renewable penetration, share benefits, and improve resilience. Studies examine governance models (energy communities/cooperatives), regulatory constraints, and the socio-economic drivers of community energy adoption.

- PV + BESS co-location benefits: Numerous studies quantify technical benefits of co-locating storage with PV: improved self-consumption, reduced grid imports, peak shaving, and reduced curtailment. Papers vary in their assumptions about storage control (rule-based, optimisation, or heuristic) and often report that benefits are context-specific — depending on load profiles, tariff structures, and PV resource quality.

- Control strategies and operational objectives: The literature contrasts different battery control objectives: maximise self-consumption, minimise energy cost under time-varying tariffs (arbitrage), minimise peak demand charges, or follow optimisation frameworks that balance multiple objectives. Model complexity ranges from simple rule-based heuristics to linear/quadratic optimisation and stochastic formulations accounting for forecast error.

- Techno-economic assessments: Common economic metrics used include levelized cost of energy (LCOE), levelized cost of storage (LCOS), net present value (NPV), internal rate of return (IRR), and payback period. Studies emphasise the sensitivity of conclusions to assumptions about capital cost trajectories (especially batteries), discount rates, and policy incentives (subsidies, feed-in tariffs, net-metering).

- Uncertainty and sensitivity analysis: Best-practice studies include scenario analysis and probabilistic sensitivity studies (Monte Carlo or scenario sweeps) to probe parameter uncertainty (battery degradation rates, future electricity prices, and capital costs). This research trend informs the thesis approach of combining scenario sweeps with sensitivity analysis.

## Modelling gaps and research opportunities

- Many studies use either synthetic load profiles or aggregated profiles that may not capture household heterogeneity; detailed community-scale, high-resolution empirical load data remain less common.
- Comparisons between control strategies with respect to combined technical and economic KPIs (rather than technical-only) are limited, especially in the context of energy communities with sharing arrangements.
- Battery degradation models are often simplified or omitted; including realistic degradation and replacement cost modelling materially affects lifecycle economics and optimal sizing.

## Relevance to this thesis

The Literature Review motivates a data-driven, high-resolution time-series approach that couples a realistic BESS operational model with a comprehensive economic layer, and argues for scenario and sensitivity analysis to capture uncertainty in costs, tariffs and degradation. The thesis fills gaps by using community-level load data (SMEC), explicit scenario bundles for PV (Gen), and an integrated techno-economic pipeline that jointly evaluates technical KPIs and economic outcomes for community-scale PV+BESS.
