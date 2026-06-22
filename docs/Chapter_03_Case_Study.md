# 3. Case Study and Data Architecture

**Techno-Economic Assessment of Co-Located PV and Battery Energy Storage Systems in Energy Communities**

This chapter defines the case-study setting, input datasets, technical assumptions, and data-processing architecture used in the thesis. Its purpose is to establish a transparent and reproducible basis for comparing three system configurations: a no-DER baseline, a PV-only collective self-consumption case, and a PV-BESS case. The chapter therefore provides the empirical and modelling foundation required to answer the research questions on economic viability, battery-specific value, and sensitivity to community composition, PV penetration, and battery capital cost.

The selected case study is a residential energy community located in Seville, Spain. Seville is used because of its high solar resource, Mediterranean climate, and relevance for collective self-consumption schemes in Southern Europe. The energy community is modelled as a grid-connected collective self-consumption arrangement with shared photovoltaic generation and a centralized battery energy storage system. The modelling does not aim to represent a specific existing community. Instead, it defines a stylized but technically consistent case that allows the effect of Spanish tariff and settlement rules to be isolated.

The data architecture is designed to support hourly simulation over one representative year. All input time series are cleaned, harmonized, and converted into model-ready datasets before being used in the techno-economic model. The core data domains are residential load, PV generation, electricity prices, tariff and compensation rules, and technology/economic parameters. The final Gold dataset supports the comparison of no-DER, PV-only, and PV-BESS scenarios, as well as the calculation of incremental battery-specific value.

---

## 3.1 Case Study Definition: Seville Energy Community

The case study represents a residential energy community configured under the Spanish collective self-consumption framework established by Real Decreto 244/2019 [1]. The baseline community consists of 30 residential households located within a compact urban area in Seville. For modelling purposes, the community is assumed to be spatially concentrated and compliant with the applicable proximity requirements for collective self-consumption. Real Decreto-ley 7/2026 modifies Real Decreto 244/2019 by retaining a general distance condition of less than 500 m and adding a less than 5,000 m condition for photovoltaic or wind generation installations of up to 5 MW connected through the grid [2]. The working case study keeps a compact 2 km modelling radius, which is therefore conservative relative to the wider 2026 PV-specific allowance.

The community includes a shared photovoltaic system and a centralized battery energy storage system. The PV system is sized through scenario analysis rather than fixed at a single value, allowing PV penetration to be tested as one of the key sensitivity dimensions. The battery is represented as a centralized lithium iron phosphate system with a baseline capacity of 150 kWh and a round-trip efficiency of 90%. The system is operated using transparent rule-based dispatch rather than full optimization. This is appropriate for the thesis because the purpose is not to identify a mathematically optimal dispatch strategy, but to evaluate whether adding a battery creates incremental economic value under Spanish settlement rules.

The community is treated as a cooperative or collectively managed arrangement in which shared generation and storage benefits are allocated among members through predefined rules. In the baseline case, static allocation coefficients are used. This means that each member receives a fixed share of the shared generation and associated benefits over the year. Dynamic allocation mechanisms are not included in the baseline case definition, which keeps the scope aligned with the research questions and avoids expanding the thesis into a broader governance-optimization study.

The case-study definition directly supports the three research questions. First, the no-DER, PV-only, and PV-BESS comparison allows the economic viability of storage to be assessed. Second, the PV-only case provides the counterfactual needed to isolate battery-specific value. Third, the community size, PV penetration, and battery CAPEX assumptions can be varied to test the robustness of the results.

---

## 3.2 Community Composition and Load Profiles

The community is composed of heterogeneous residential consumers. To represent this heterogeneity, households are divided into three consumption clusters: low, medium, and high consumption. This clustered representation preserves diversity in annual demand while keeping the model simple enough for transparent techno-economic analysis. The baseline composition is shown in Table 3.1.

**Table 3.1. Baseline community composition**

| Cluster            | Share of community | Number of households | Annual consumption range |
| ------------------ | -----------------: | -------------------: | -----------------------: |
| Low consumption    |                40% |                   12 |     1,500-2,500 kWh/year |
| Medium consumption |                40% |                   12 |     2,500-4,000 kWh/year |
| High consumption   |                20% |                    6 |     4,000-6,500 kWh/year |

Low-consumption households represent small apartments or dwellings with limited appliance use. Medium-consumption households represent standard family homes with typical occupancy and appliance patterns. High-consumption households represent larger homes or dwellings with higher use of appliances, cooling, or other electricity-intensive end uses.

Household demand profiles are constructed using empirical smart-meter data as a behavioural template. High-resolution smart-meter datasets are suitable for representing intra-day residential demand variability and for constructing household load archetypes [8]. However, the London Smart Meter dataset is not treated as geographically representative of Seville. Instead, it is used to preserve realistic residential load-shape variability, while annual consumption levels are rescaled to match the Low, Medium, and High consumption ranges defined above.

The load-processing approach follows three principles. First, empirical household profiles are retained at individual-household level for as long as possible to preserve heterogeneity. Second, half-hourly or higher-frequency data are aggregated to hourly resolution to match the simulation backbone. Third, profiles are rescaled to Spanish annual consumption ranges and, where required, adjusted to reflect Seville-specific climatic conditions. This is important because Seville's hot summers may affect cooling-related demand, while the original London dataset reflects a different climate and behavioural context.

Community composition is also a sensitivity dimension. In the baseline, the 40-40-20 distribution provides a balanced mix of household types. In sensitivity analysis, the relative share of Low, Medium, and High consumption members can be varied to test whether the economic value of PV-BESS depends on demand heterogeneity. This is directly relevant to RQ3, because storage value may increase when demand is more diverse and when evening consumption better aligns with stored PV energy.

---

## 3.3 PV Generation and Weather Data

PV generation is represented through an hourly photovoltaic production profile for Seville. For consistency and reproducibility, the baseline PV profile is generated using the PVGIS non-interactive API, specifically the seriescalc tool for hourly grid-connected PV output. PVGIS is selected as the primary PV generation source because it directly provides PV power output for a defined system configuration, reducing the need to construct a full PV conversion model from raw irradiance variables. The European Commission's Joint Research Centre describes PVGIS as a tool for obtaining solar radiation and photovoltaic system performance information, and its API supports non-interactive access to PVGIS tools [5], [6].

The baseline PV profile is generated for a normalized 1 kWp system and then scaled linearly to the required community PV capacity in each scenario. This allows different PV penetration levels to be evaluated without repeatedly changing the underlying weather year. The main PVGIS parameters are summarized in Table 3.2.

**Table 3.2. Baseline PV profile parameters**

| Parameter                 | Baseline value                                                                                           |
| ------------------------- | -------------------------------------------------------------------------------------------------------- |
| Location                  | Seville, Spain                                                                                           |
| Latitude / Longitude      | 37.4°N / -6.05°                                                                                          |
| Radiation database        | PVGIS-SARAH3                                                                                             |
| PV technology             | Crystalline silicon                                                                                      |
| Mounting type             | Building / rooftop                                                                                       |
| System losses             | 14%                                                                                                      |
| Tilt / azimuth            | 30° / 0° south-facing                                                                                    |
| Reference system size     | 1 kWp                                                                                                    |
| Temporal resolution       | Hourly                                                                                                   |
| Auxiliary validation data | Long-term GHI/DNI dataset and Open-Meteo/ERA5-Land weather file; not used as primary PV generation input |

The PVGIS output includes hourly PV power values, which are converted into hourly energy values. Since the simulation time step is one hour, PV energy in kWh is calculated by converting PV power from watts to kilowatts for each hourly step. The normalized 1 kWp output is then multiplied by the total installed PV capacity of the community scenario.

Timestamps are handled carefully because PVGIS returns time-series data that must be aligned with local tariff and demand data. For tariff alignment and demand matching, timestamps are converted to Europe/Madrid time, with daylight-saving time handled explicitly. This is essential because electricity prices, PVPC settlement, household demand, and PV generation must all be joined on the same time index.

Open-Meteo can be retained as an auxiliary source for irradiance and weather diagnostics. The Open-Meteo Historical Weather API provides long historical coverage with hourly resolution using reanalysis products [7]. However, if Open-Meteo were used as the primary PV source, additional modelling steps would be required, including plane-of-array irradiance calculation, module temperature modelling, DC-to-AC conversion, inverter clipping, and system loss modelling. For this reason, PVGIS is used as the cleaner baseline PV production source, while Open-Meteo remains useful for plausibility checks or later sensitivity analysis.

In addition to the PVGIS baseline profile, two auxiliary irradiance and weather datasets are retained for diagnostic and validation purposes: a long-term hourly GHI/DNI dataset and an Open-Meteo/ERA5-Land weather file for Seville. These datasets are not used as the primary PV generation input in the baseline simulation. Instead, they are used to support solar-resource characterization, check the plausibility of the PVGIS generation profile, and provide optional weather diagnostics. This avoids introducing a separate PV conversion model from raw irradiance data, while still allowing the PVGIS-based profile to be checked against independent solar-resource information.

The selection of Seville is also supported by its solar-resource context. Published solar-resource work on Seville shows that the location has been used for detailed solar radiation assessment based on high-resolution radiometric measurements, making it a suitable Mediterranean case for solar-energy analysis [9].

---

## 3.4 Electricity Price and Tariff Data

Electricity price data are required for two different purposes: operational dispatch and retail settlement. These two uses are separated in the data architecture to avoid mixing wholesale market prices with retail billing values.

First, the OMIE day-ahead market price is used as the wholesale price signal. This price can guide battery dispatch and represent wholesale-indexed price scenarios. OMIE publishes day-ahead prices for the Spanish and Portuguese electricity systems by market period, including quarter-hourly periods in the current market design [3]. In the model, OMIE prices are stored at their native resolution where available and aggregated to hourly resolution for the main simulation. OMIE is used as a dispatch or wholesale signal, not as the direct valuation basis for PVPC imports or exports.

Second, grid imports are valued using the PVPC import price series for residential consumers. This represents the regulated retail price signal used in the baseline billing model. Third, surplus exports are valued using the PVPC simplified-compensation export-credit series, specifically the ESIOS indicator for the price of surplus self-consumption energy under the simplified compensation mechanism [4].

The simplified compensation mechanism is central to this thesis. Under Real Decreto 244/2019, surplus compensation is applied within the billing framework for eligible self-consumption consumers. The value credited for exported surplus is limited by the value of imported energy within the billing period, and the billing period cannot exceed one month [1]. This monthly cap is one of the main reasons why the PV-only and PV-BESS comparison is necessary: a battery may create value by reducing surplus exports that would otherwise be credited at a lower value or limited by the cap.

The price-processing procedure includes the following rules. OMIE, PVPC import, and PVPC export-credit series are stored in EUR/MWh at the standardized data layer and converted to EUR/kWh only when calculating bill components. Where 15-minute data are available, values are aggregated to hourly resolution using the arithmetic mean of the four quarter-hour values within each hour. Negative wholesale prices are preserved rather than deleted, because they may be relevant to storage value and price-volatility sensitivity. Validation checks are applied for completeness, duplicate timestamps, extreme spikes, and correct application of the monthly compensation cap.

---

## 3.5 Technology and Economic Parameters

The techno-economic model requires assumptions for PV, BESS, and financial evaluation. These parameters are not treated as directly observed data. Instead, they are modelling assumptions based on literature, industry benchmarks, and sensitivity ranges [10]-[12]. This distinction is important because the thesis aims to identify conditions under which PV-BESS becomes viable, rather than claiming that one fixed cost or performance value is universally valid.

The PV system is represented using crystalline silicon technology with fixed-tilt rooftop installation. The baseline tilt is 30°, with south-facing orientation. The PV capacity itself is not fixed in this chapter, because PV penetration is one of the main sensitivity variables. Instead, the model scales the normalized PV generation profile to different installed capacities.

The BESS is represented as a centralized LFP battery. The baseline capacity is 150 kWh, with 90% round-trip efficiency, 90% depth of discharge, and a 0.5C charge/discharge rate. LFP is a relevant stationary-storage chemistry, and recent international assessments emphasize both the rapid cost decline of lithium-ion battery technologies and their growing role in power-sector and behind-the-meter storage applications [10], [11].

Battery degradation is not modelled explicitly. This means that usable capacity and efficiency are held constant over the simulation period. This simplification is acceptable for the thesis because the main focus is tariff and settlement realism, battery-specific value, and sensitivity to CAPEX rather than detailed electrochemical ageing. The implications of excluding degradation are treated as a limitation and future-work item.

**Table 3.3. Main technology and economic parameters**

| Category | Parameter             | Baseline assumption |
| -------- | --------------------- | ------------------- |
| PV       | Technology            | Crystalline silicon |
| PV       | System losses         | 14-15%              |
| PV       | Tilt / azimuth        | 30° / south-facing  |
| BESS     | Chemistry             | LFP                 |
| BESS     | Capacity              | 150 kWh             |
| BESS     | Round-trip efficiency | 90%                 |
| BESS     | Depth of discharge    | 90%                 |
| BESS     | C-rate                | 0.5C                |
| BESS     | CAPEX                 | EUR 400-500/kWh     |
| Economic | Discount rate         | 4% real             |
| Economic | PV lifetime           | 25 years            |
| Economic | BESS lifetime         | 15 years            |
| Economic | PV CAPEX              | EUR 1,000-1,200/kWp |
| Economic | PV O&M                | EUR 15-20/kWp/year  |

The economic parameters are used to calculate annual bill savings, NPV, payback period, and other techno-economic indicators. The most important comparison is not the absolute value of one configuration alone, but the incremental difference between PV-only and PV-BESS. Battery-specific value is therefore calculated as the additional benefit created by the battery relative to the PV-only counterfactual under the same load, PV generation, tariff, and settlement assumptions.

Battery CAPEX is a key sensitivity variable. The baseline range of EUR 400-500/kWh is used as a central assumption for an installed community-scale system, while lower and higher values should be tested to identify break-even thresholds. This directly supports RQ1 and RQ3 by showing whether PV-BESS viability depends mainly on storage cost reductions, price volatility, or community load composition.

---

## 3.6 Data Processing Architecture

The data architecture follows a Bronze-Silver-Gold structure. This structure is used to make the workflow transparent, reproducible, and auditable. It also prevents raw data, cleaned data, and model-ready data from being mixed.

The Bronze layer stores raw input files exactly as downloaded. This includes smart-meter load files, OMIE and ESIOS price files, PVGIS hourly PV-output files, auxiliary GHI/DNI irradiance files, Open-Meteo diagnostic weather files, and metadata such as download date, source URL, units, time zone, and file hashes.

The Silver layer contains cleaned and standardized data. At this stage, timestamps are normalized, units are harmonized, missing values are flagged, and all time series are converted or aggregated to hourly resolution. Load data are aggregated from half-hourly to hourly values where required. Price data are stored in EUR/MWh, and PV generation is stored in kWh per hour. Outliers and negative prices are flagged rather than automatically removed, because extreme market values can be economically meaningful for BESS value assessment.

The Gold layer contains the final model-ready tables. These are the datasets used directly by the simulation model. The main Gold table is defined at the member-hour-scenario level and contains household load, allocated PV, BESS flows, grid imports, grid exports, prices, and bill components. A community-level rollup table is also retained for checking energy balance and battery state of charge.

**Table 3.4. Data architecture summary**

| Layer  | Purpose                       | Main contents                                                   |
| ------ | ----------------------------- | --------------------------------------------------------------- |
| Bronze | Raw and immutable storage     | Original load, PV, price, tariff, and metadata files            |
| Silver | Cleaned and standardized data | Hourly load, hourly PV, hourly prices, QA flags                 |
| Gold   | Model-ready simulation data   | Member-hour-scenario tables, community rollups, bill components |

The Gold dataset is designed to support three scenarios: no-DER, PV-only, and PV-BESS. The no-DER case provides the baseline electricity cost without shared assets. The PV-only case measures the value of collective PV self-consumption under PVPC import/export rules. The PV-BESS case measures the additional value created when storage is added. The difference between PV-BESS and PV-only results is the basis for battery-specific value attribution.

A simplified representation of the battery-specific value calculation is given as:

```text
Battery-specific value = Result(PV-BESS) - Result(PV-only)
```

where the result may be expressed as annual bill savings, NPV, self-consumption ratio, grid-import reduction, or another defined performance indicator. The same load, PV generation, price series, tariff rules, and allocation coefficients are used in both cases so that the incremental effect can be attributed to the battery rather than to changes in other inputs.

---

## 3.7 Data Quality, Assumptions, and Limitations

Several data-quality checks are required before simulation. First, each hourly time series must contain the expected number of hourly records for the reference year. Second, all timestamps must be aligned to the same time zone, preferably Europe/Madrid for the model-facing dataset. Third, energy units must be consistent: load and PV generation in kWh, prices in EUR/MWh at the data-storage stage, and EUR/kWh in the billing-calculation stage. Fourth, load and PV values must be non-negative, while negative electricity prices should be allowed. Fifth, the community-level energy balance must be verified for each hour.

The billing logic also requires specific validation. In each billing month, the applied export credit must not exceed the value of imported energy. The model should therefore store both the raw hourly export-credit value and the capped monthly applied credit. This makes it possible to quantify whether and when the compensation cap binds. This is important for RQ2 because one expected source of battery value is the reduction of surplus exports whose credit is limited by the monthly cap.

The main limitation of the load dataset is geographic transferability. The London Smart Meter dataset provides useful empirical load shapes, but it does not directly represent Seville households. This limitation is addressed by treating the dataset as a behavioural template, rescaling annual demand to Spanish residential consumption ranges, and including community-composition sensitivity analysis.

A second limitation concerns PV and weather data. PVGIS provides a reproducible hourly PV profile, but it remains a modelled estimate rather than measured generation from the specific rooftops of the community. Shading, roof availability, orientation diversity, inverter sizing, and local soiling are simplified through general loss assumptions. These assumptions are acceptable for a techno-economic thesis but should be acknowledged when interpreting absolute results. The auxiliary GHI/DNI and Open-Meteo datasets are therefore used only for solar-resource plausibility checks and weather diagnostics, not to replace the PVGIS seriescalc output used in the baseline simulation.

A third limitation concerns technology costs. Battery and PV CAPEX values are uncertain and may vary significantly depending on market conditions, installer pricing, supply chains, and policy incentives. For this reason, the thesis should not rely on a single CAPEX assumption. Instead, CAPEX sensitivity analysis is required to identify threshold values at which PV-BESS becomes economically attractive.

A fourth limitation is that the model does not include detailed distribution-network constraints. Voltage limits, transformer loading, feeder capacity, and protection constraints are outside the scope. The case study therefore evaluates economic coordination and settlement effects rather than physical grid feasibility.

Finally, the battery model does not include detailed degradation. This means that results may slightly overstate long-term battery performance if degradation would reduce usable capacity or increase replacement needs. However, excluding degradation keeps the model transparent and focused on the thesis objective: determining whether the battery creates incremental value over PV-only operation under Spanish PVPC settlement and simplified compensation rules.

Overall, the data architecture and case-study design are suitable for answering the research questions. The chapter defines the system boundary, data sources, assumptions, validation rules, and scenario structure needed to evaluate PV-BESS viability, isolate battery-specific value, and test sensitivity to community composition, PV penetration, and battery CAPEX.

---

# References

[1] Boletín Oficial del Estado (BOE), Real Decreto 244/2019, de 5 de abril, por el que se regulan las condiciones administrativas, técnicas y económicas del autoconsumo de energía eléctrica, BOE-A-2019-5089, 2019. Available: https://www.boe.es/eli/es/rd/2019/04/05/244/con. Accessed: 15 Jun. 2026.

[2] Boletín Oficial del Estado (BOE), Real Decreto-ley 7/2026, de 20 de marzo, por el que se aprueba el Plan Integral de Respuesta a la Crisis en Oriente Medio, BOE-A-2026-6544, 2026. Available: https://www.boe.es/buscar/doc.php?id=BOE-A-2026-6544. Accessed: 15 Jun. 2026.

[3] OMIE, “Day-ahead price results: Daily market, Spanish electricity system.” Available: https://www.omie.es/en/market-results/daily/daily-market/day-ahead-price. Accessed: 15 Jun. 2026.

[4] Red Eléctrica de España (REE) / ESIOS, “Precio de la energía excedentaria del autoconsumo para el mecanismo de compensación simplificada (PVPC), Indicator 1739.” Available: https://www.esios.ree.es. Accessed: 15 Jun. 2026.

[5] European Commission, Joint Research Centre (JRC), “Photovoltaic Geographical Information System (PVGIS).” Available: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en. Accessed: 15 Jun. 2026.

[6] European Commission, Joint Research Centre (JRC), “PVGIS API non-interactive service documentation.” Available: https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en. Accessed: 15 Jun. 2026.

[7] Open-Meteo, “Historical Weather API documentation.” Available: https://open-meteo.com/en/docs/historical-weather-api. Accessed: 15 Jun. 2026.

[8] F. McLoughlin, A. Duffy, and M. Conlon, “A clustering approach to domestic electricity load profile characterisation using smart metering data,” Applied Energy, vol. 141, pp. 190-199, 2015, doi: 10.1016/j.apenergy.2014.12.039.

[9] S. Moreno-Tejera, M. A. Silva-Pérez, I. Lillo-Bravo, and L. Ramírez-Santigosa, “Solar resource assessment in Seville, Spain: Statistical characterisation of solar radiation at different time resolutions,” Solar Energy, vol. 132, pp. 430-441, 2016.

[10] International Energy Agency (IEA), Batteries and Secure Energy Transitions, Paris: IEA, 2024. Available: https://www.iea.org/reports/batteries-and-secure-energy-transitions. Accessed: 15 Jun. 2026.

[11] National Renewable Energy Laboratory (NREL), “2024 Annual Technology Baseline: Residential Battery Storage.” Available: https://atb.nrel.gov. Accessed: 15 Jun. 2026.

[12] International Renewable Energy Agency (IRENA), Renewable Power Generation Costs in 2024, Abu Dhabi: IRENA, 2025.
