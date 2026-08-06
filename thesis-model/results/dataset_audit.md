# Dataset audit

|provider|source_file|start|end|obs|tz|unit|missing_2024|missing_2025|dups|role|
|-|-|-|-|-|-|-|-|-|-|-|
|load|load_hourly.csv|2012-10-12T01:00:00||UNKNOWN|Europe/Madrid|kwh|UNKNOWN|UNKNOWN|UNKNOWN|load|
|pvgis||| |0||| | | |pv|
|omie||| |0||| | | |price_omie|
|pvpc_import||| |0||| | | |price_pvpc_import|
|pvpc_export||| |0||| | | |price_pvpc_export|

> Notes: Results marked UNKNOWN indicate the audit script should be run in an environment with access to the full raw files to compute precise start/end/observation counts. The repository contains load_hourly.csv; price and PVGIS folders are empty in this commit.
