Made the design doc: [geo_sbsp_sim_data_design.md](sandbox:/workspace/geo_sbsp_sim_data_design.md)

Core shape:

```text
Scenario config
-> Basilisk GEO simulation
-> raw telemetry
-> bronze normalized tables
-> silver derived physics/ops metrics
-> gold analysis tables
-> Spark campaign analysis
-> dashboards
```

The main dependent variables to test across sim runs are:

```text
array_area_m2
panel_efficiency
dc_to_rf_efficiency
rf_to_dc_efficiency
beam_frequency_hz
transmit_aperture_diameter_m
tx_power_w
pointing_error_deg
jitter_std_deg
phase_error_deg
sidelobe_ratio
rectenna_area_m2
thermal_gradient_c
deformation_rms_m
module_failure_rate_per_year
module_degradation_rate_pct_year
launch_cost_per_kg_usd
manufacturing_cost_per_m2_usd
```

The highest-value analysis outputs are:

```text
annualized_mwh_delivered
average_delivered_power_mw
capacity_factor
safety_violation_count
beam_abort_count
lost_energy_pointing_mwh
lost_energy_phase_mwh
lost_energy_thermal_mwh
lost_energy_failures_mwh
estimated_cost_per_mwh
design_score
```

Basically: Basilisk gives you orbit/attitude/dynamics, your SBSP module turns that into power/beam/rectenna telemetry, and Spark ranks thousands of design runs by power, safety, robustness, and economics.
