You generate it in Basilisk by doing **two things**:

1. Let Basilisk produce the real spacecraft state:
   `position`, `velocity`, `attitude`, `angular rate`, eclipse/sun geometry later.

2. Add your own SBSP post-processing/module:
   `solar power`, `beam spread`, `rectenna received power`, `safety events`, `run summary`.

Basilisk is modular and message-based, and it supports recording module output messages during a sim run. That is exactly what you want for telemetry generation. [Basilisk recording docs](https://hanspeterschaub.info/basilisk/Learn/bskPrinciples/bskPrinciples-4.html)

**Minimal Shape**

Start simple:

```text
Basilisk GEO spacecraft state
-> record spacecraft state message
-> convert recorder output to DataFrame
-> compute SBSP power/beam fields
-> write Parquet
-> Spark analyzes many run_id folders
```

Do **not** make custom Basilisk C++ modules first. For ROI, post-process in Python first.

**Skeleton**

```python
import os
import uuid
import numpy as np
import pandas as pd

from Basilisk.utilities import SimulationBaseClass, macros, orbitalMotion, simIncludeGravBody
from Basilisk.simulation import spacecraft


def run_geo_sbsp_sim(config: dict):
    run_id = config.get("run_id", str(uuid.uuid4()))

    sim = SimulationBaseClass.SimBaseClass()
    process_name = "simProcess"
    task_name = "simTask"
    step_ns = macros.sec2nano(config["timestep_seconds"])

    sim_proc = sim.CreateNewProcess(process_name)
    sim_task = sim.CreateNewTask(task_name, step_ns)
    sim_proc.addTask(sim_task)

    # Spacecraft
    sc = spacecraft.Spacecraft()
    sc.ModelTag = "geoSolarSat"

    earth_mu = 3.986004418e14
    earth_radius = 6378137.0
    geo_radius = 42164000.0

    oe = orbitalMotion.ClassicElements()
    oe.a = geo_radius
    oe.e = config.get("eccentricity", 0.0001)
    oe.i = np.deg2rad(config.get("inclination_deg", 0.05))
    oe.Omega = 0.0
    oe.omega = 0.0
    oe.f = 0.0

    r_n, v_n = orbitalMotion.elem2rv(earth_mu, oe)

    sc.hub.r_CN_NInit = r_n
    sc.hub.v_CN_NInit = v_n
    sc.hub.sigma_BNInit = [[0.0], [0.0], [0.0]]
    sc.hub.omega_BN_BInit = [[0.0], [0.0], [0.0]]

    grav_factory = simIncludeGravBody.gravBodyFactory()
    earth = grav_factory.createEarth()
    earth.isCentralBody = True
    earth.mu = earth_mu
    grav_factory.addBodiesTo(sc)

    sim.AddModelToTask(task_name, sc)

    # Record Basilisk spacecraft telemetry
    sc_rec = sc.scStateOutMsg.recorder(step_ns)
    sim.AddModelToTask(task_name, sc_rec)

    sim.InitializeSimulation()
    sim.ConfigureStopTime(macros.sec2nano(config["duration_seconds"]))
    sim.ExecuteSimulation()

    # Convert Basilisk telemetry to rows
    times_sec = sc_rec.times() * macros.NANO2SEC
    r = np.array(sc_rec.r_BN_N)
    v = np.array(sc_rec.v_BN_N)
    sigma = np.array(sc_rec.sigma_BN)
    omega = np.array(sc_rec.omega_BN_B)

    df = pd.DataFrame({
        "run_id": run_id,
        "time_s": times_sec,
        "position_eci_x_m": r[:, 0],
        "position_eci_y_m": r[:, 1],
        "position_eci_z_m": r[:, 2],
        "velocity_eci_x_m_s": v[:, 0],
        "velocity_eci_y_m_s": v[:, 1],
        "velocity_eci_z_m_s": v[:, 2],
        "sigma_bn_1": sigma[:, 0],
        "sigma_bn_2": sigma[:, 1],
        "sigma_bn_3": sigma[:, 2],
        "omega_x_rad_s": omega[:, 0],
        "omega_y_rad_s": omega[:, 1],
        "omega_z_rad_s": omega[:, 2],
    })

    df = add_sbsp_power_beam_rectenna(df, config)

    out_dir = (
        f"data/sbsp/raw/"
        f"campaign_id={config['campaign_id']}/"
        f"run_id={run_id}"
    )
    os.makedirs(out_dir, exist_ok=True)
    df.to_parquet(f"{out_dir}/telemetry.parquet", index=False)

    return df


def add_sbsp_power_beam_rectenna(df: pd.DataFrame, config: dict):
    solar_constant = config.get("solar_irradiance_w_m2", 1361.0)

    panel_area = config["array_area_m2"]
    panel_eff = config["panel_efficiency"]
    dc_bus_eff = config["dc_bus_efficiency"]
    dc_to_rf_eff = config["dc_to_rf_efficiency"]
    rf_to_dc_eff = config["rf_to_dc_efficiency"]

    frequency_hz = config["beam_frequency_hz"]
    wavelength_m = 299_792_458.0 / frequency_hz
    aperture_m = config["transmit_aperture_diameter_m"]
    geo_distance_m = 35_786_000.0

    pointing_error_deg = config["pointing_error_deg"]
    phase_error_deg = config["phase_error_deg"]
    rectenna_area_m2 = config["rectenna_area_m2"]

    # Version 1 simplifications.
    df["in_eclipse"] = False
    df["sun_exposure_factor"] = 1.0

    df["ideal_solar_w"] = solar_constant * panel_area
    df["generated_dc_w"] = df["ideal_solar_w"] * panel_eff
    df["bus_available_w"] = df["generated_dc_w"] * dc_bus_eff
    df["tx_power_w"] = df["bus_available_w"] * dc_to_rf_eff

    # Simple diffraction-style beam estimate.
    df["beam_radius_m"] = 1.22 * wavelength_m * geo_distance_m / aperture_m

    pointing_offset_m = np.tan(np.deg2rad(pointing_error_deg)) * geo_distance_m
    df["pointing_offset_m"] = pointing_offset_m

    # Crude coherence loss from phase error. Replace later with better phased-array model.
    phase_rad = np.deg2rad(phase_error_deg)
    coherence_eff = max(0.0, np.cos(phase_rad) ** 2)
    df["coherence_efficiency"] = coherence_eff

    beam_area_m2 = np.pi * df["beam_radius_m"] ** 2
    df["peak_power_density_w_m2"] = df["tx_power_w"] / beam_area_m2

    capture_ratio = np.minimum(1.0, rectenna_area_m2 / beam_area_m2)
    df["captured_rf_w"] = df["tx_power_w"] * capture_ratio * coherence_eff
    df["delivered_dc_w"] = df["captured_rf_w"] * rf_to_dc_eff

    public_limit = config["public_power_density_limit_w_m2"]
    df["safety_violation"] = df["peak_power_density_w_m2"] > public_limit

    return df
```

**Example Config**

```python
config = {
    "campaign_id": "geo_baseline_power_sweep",
    "duration_seconds": 86400,
    "timestep_seconds": 10.0,

    "array_area_m2": 19_000_000,
    "panel_efficiency": 0.30,
    "dc_bus_efficiency": 0.96,
    "dc_to_rf_efficiency": 0.75,
    "rf_to_dc_efficiency": 0.85,

    "beam_frequency_hz": 5.8e9,
    "transmit_aperture_diameter_m": 1000,
    "pointing_error_deg": 0.05,
    "phase_error_deg": 2.0,

    "rectenna_area_m2": 100_000_000,
    "public_power_density_limit_w_m2": 10.0,
}

df = run_geo_sbsp_sim(config)
```

Then for many runs, sweep configs:

```python
for aperture in [500, 1000, 2000, 3000]:
    for pointing_error in [0.005, 0.01, 0.05, 0.1]:
        config["transmit_aperture_diameter_m"] = aperture
        config["pointing_error_deg"] = pointing_error
        run_geo_sbsp_sim(config)
```

That generates your Parquet lake:

```text
data/sbsp/raw/campaign_id=geo_baseline_power_sweep/run_id=.../telemetry.parquet
```

Then Spark reads:

```python
df = spark.read.parquet("data/sbsp/raw/campaign_id=geo_baseline_power_sweep/")
```

The clean path is: **Basilisk records dynamics, Python computes SBSP-specific telemetry, Spark analyzes campaigns.** Later, once the math stabilizes, you convert the SBSP post-processing into proper Basilisk Python modules or C++ modules.
