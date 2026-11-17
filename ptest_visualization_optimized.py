"""End-to-end pressure-test processing and plotting.

Pipeline: raw pickle files -> test Excel -> combined Excel -> calibrated Excel
-> interactive plots. Update the configuration section and run once.
"""

from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import requests
from numpy.polynomial.polynomial import polyval

# Open interactive figures in the system browser when SHOW_PLOTS is enabled.
pio.renderers.default = "browser"


# ---------------------------------------------------------------------------
# Embedded sensor calculations and calibration lookup
# ---------------------------------------------------------------------------
# These functions were embedded from calc_sensor.py and db_api.py so this
# script can run as a single file.
K0 = 273.15
R = 8.3144626
FARADAY = 96485.33
VO2 = 22.3916
O2_COEFFICIENTS = {
    "a": (2.00907, 3.22014, 4.0501, 4.94457, -0.256847, 3.88767),
    "b": (-6.24523e-3, -7.37614e-3, -1.03410e-2, -8.17083e-3),
    "c0": -4.88682e-7,
}
CALIBRATION_API = "https://db.whoifloatgroup.org"


def get_cal_sn(float_number):
    """Retrieve calibration metadata for one float from the WHOI API."""
    response = requests.get(
        f"{CALIBRATION_API}/api/cal",
        params={"FLOAT_SERIAL_NO": float_number, "PLATFORM_TYPE": "NAVIS_EBR"},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    return pd.DataFrame(json.loads(response.content))


def mcoms(scale, dark, counts):
    """Convert MCOMS counts to scientific units."""
    return scale * (counts - dark)


def o2_sbe(cal, phase, optode_temperature_voltage, pressure, temperature, salinity):
    """Calculate dissolved oxygen from an SBE optode."""
    cal_a = np.array([cal["A0"], cal["A1"], cal["A2"]])
    cal_b = np.array([cal["B0"], cal["B1"]])
    cal_c = np.array([cal["C0"], cal["C1"], cal["C2"]])
    cal_ta = np.array([cal["TA0"], cal["TA1"], cal["TA2"], cal["TA3"]])
    phase = phase + 0.115 * pressure / 1000
    pressure_correction = (0.00022 * temperature + 0.0419) * pressure / 1000 + 1
    log_voltage = np.log(1e5 * optode_temperature_voltage / (3.3 - optode_temperature_voltage))
    oxygen_temperature = 1 / polyval(log_voltage, cal_ta) - K0
    temperature_scale = np.log((25 + K0 - oxygen_temperature) / (K0 + oxygen_temperature))
    salinity_correction = np.exp(
        (salinity * polyval(temperature_scale, O2_COEFFICIENTS["b"]))
        + O2_COEFFICIENTS["c0"] * salinity**2
    )
    voltage = phase / 39.4570707
    ksv = polyval(temperature, cal_c)
    oxygen_ml_l = (((cal["A0"] + temperature * cal["A1"] + cal["A2"] * voltage**2)
                    / (cal["B0"] + voltage * cal["B1"]) - 1) / ksv)
    oxygen_ml_l = oxygen_ml_l * salinity_correction * pressure_correction
    return (1000 / VO2 * oxygen_ml_l, oxygen_temperature, oxygen_ml_l)


def pH_sbe(cal, reference_voltage, pressure, temperature, salinity):
    """Calculate free-scale and total-scale pH from SBE measurements."""
    tk = K0 + temperature
    ln10 = np.log(10)
    pressure_bar = pressure / 10
    pressure_coefficients = [0, cal["F1"], cal["F2"], cal["F3"], cal["F4"], cal["F5"], cal["F6"]]
    if "F9" in cal:
        pressure_coefficients.extend([cal["F7"], cal["F8"], cal["F9"]])
    ionic_strength = 19.924 * salinity / (1000 - 1.005 * salinity)
    sulfate_total = (0.14 / 96.062) * (salinity / 1.80655)
    chloride_total = (0.99889 / 35.453 * salinity / 1.80655) / (1 - 0.001005 * salinity)
    khso4 = np.exp(
        -4276.1 / tk + 141.328 - 23.093 * np.log(tk)
        + (-13856 / tk + 324.57 - 47.986 * np.log(tk)) * ionic_strength**0.5
        + (35474 / tk - 771.54 + 114.723 * np.log(tk)) * ionic_strength
        - 2698 / tk * ionic_strength**1.5 + 1776 / tk * ionic_strength**2
        + np.log(1 - 0.001005 * salinity)
    )
    delta_v_hso4 = -18.03 + 0.0466 * temperature + 0.000316 * temperature**2
    kappa_hso4 = (-4.53 + 0.09 * temperature) / 1000
    ln_khso4_pressure = (-delta_v_hso4 + 0.5 * kappa_hso4 * pressure_bar) * pressure_bar / (R * 10 * tk)
    khso4_pressure = khso4 * np.exp(ln_khso4_pressure)
    adh = polyval(temperature, [0.49172143, 6.7524e-4, 3.4286e-6])
    log_gamma_hcl = -adh * np.sqrt(ionic_strength) / (1 + 1.394 * np.sqrt(ionic_strength)) + (0.08885 - 0.000111 * temperature) * ionic_strength
    delta_v_hcl = 17.85 + 0.1044 * temperature - 0.001316 * temperature**2
    log_gamma_hcl_pressure = log_gamma_hcl + delta_v_hcl * pressure_bar / (R * tk * ln10) / 2 / 10
    k0_temperature = cal["K0"] + cal["K2f0"] * temperature
    pressure_correction = polyval(pressure, pressure_coefficients)
    k0_pressure_temperature = k0_temperature + pressure_correction
    ph_free = ((reference_voltage - k0_pressure_temperature) / (R * tk / FARADAY * ln10)
               + np.log(chloride_total) / ln10 + 2 * log_gamma_hcl_pressure
               - np.log10(1 - 0.001005 * salinity))
    ph_total = ph_free - np.log10(1 + sulfate_total / khso4_pressure)
    return ph_free, ph_total


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# The RUN_* switches control the four stages independently.  Once a stage has
# created its files, leave that stage off on later runs to save time.
USER = "Aidan"
RUN_CREATE_RESULTS = False       # Convert raw .pkl files to test-result Excel
RUN_COMBINE_RESULTS = False      # Combine valve and pump result files
RUN_ADD_CALCULATIONS = False     # Add calibrated sensor calculations
RUN_PLOTS = True
SAVE_PLOTS = True
SHOW_PLOTS = False
SAVE_DATE_GROUPED_PLOTS = True
SHOW_DATE_GROUPED_PLOTS = False
OVERWRITE_EXISTING = False      # Recompute files instead of reusing them
TEST_TYPE = "valve"
INCLUDE_PUMP_RESULTS = True

# Add new floats here as {serial_number: test_date}.  The date must match the
# date embedded in the pickle filename, for example F2006_20260806.pkl.
NEW_FLOATS = {
    # "2006": "20260806",
}
PROCESS_ONLY_NEW_FLOATS = True
PLOT_ALL_FLOATS = True  # Rebuild combined plots using old calculated files too

FLOAT_SERIAL_NUMBERS = [
    "1558", "1557", "1559", "1540", "1560", "1561", "1564", "1556",
    "1531", "1542", "1631", "1583", "1633", "1634", "1635", "1565",
    "1566", "1533", "1567", "1568", "1569", "1573", "1574", "1577",
    "1581", "1636", "1481", "1637", "1638", "1639", "1640", "1641",
    "1642", "1643", "1644", "1645", "1646", "1647", "1648", "1584",
    "1585", "1586", "1649", "1650", "1651", "1632", "1563", "1662",
    "1663", "15649", "16319", "16329", "15749", "1580", "1659", "1664",
    "1669", "1673", "1675", "1667", "1753", "1680", "1757", "1665",
    "1759", "1760", "2002", "2003", "2001", "2004", "1668", "1541",
    "2005", "2007", "2008", "2009", "2011", "2012", "2010", "1554",
    "1658", "1754", "2014", "2015", "2016", "2018", "1660", "1755",
    "1758", "2017", "1674", "1761", "1762", "1756", "2006",
]

PARAMETERS = ["PSAL", "FCDOM", "FCHLA", "BBP", "TEMP", "OXYGEN", "PH_9", "PTEMP", "rawFCDOM", "rawFCHLA", "rawBBP"]
# Use a shorter list here when you only need a few plots.
PLOT_PARAMETERS = PARAMETERS
USER_PATHS = {
    "Aidan": Path(r"C:\Users\aidan.thayer\Documents\repositories\bgc-testing\presure_testing"),
    "Kat": Path("/Users/katherineparise/Documents/GitHub/bgc-testing/pressure_testing"),
}
DRIVE_ROOTS = {
    "Aidan": Path(r"G:/Shared drives/WHOI Argo/BGC/Float Tracking"),
    "Kat": Path("/Users/katherineparise/Library/CloudStorage/GoogleDrive-katherine.parise@whoi.edu/Shared drives/WHOI Argo/BGC/Float Tracking"),
}
PLOT_ROOTS = {
    # Preserve the original filedir + pressure_test output location.
    "Aidan": Path(r"Z:/www/bgc/pressure_test"),
    "Kat": Path("/Volumes/data1/www/bgc/pressure_test"),
}
LABELS = {
    "PRES": "Pressure (dbar)", "PSAL": "Salinity (PSU)", "FCDOM": "FDOM (ppb)",
    "FCHLA": "Chlorophyll-a (mg/m³)", "BBP": "Backscattering at 700 nm (m⁻¹)",
    "TEMP": "Temperature (°C)", "PTEMP": "Potential temperature (°C)",
    "OXYGEN": "Dissolved oxygen (µM)", "PH_9": "pH (total scale)",
    "rawFCDOM": "Raw FDOM", "rawFCHLA": "Raw chlorophyll-a", "rawBBP": "Raw backscattering",
    "HUMIDITY": "Humidity (%)", "Buoyancy Position": "Buoyancy position",
    "Time Since Test Start (hours)": "Time since test start (hours)",
}


def _paths():
    # Build all locations from one shared-drive root so paths only need to be
    # changed in one place for each user.
    tracking = DRIVE_ROOTS[USER]
    return {
        "data": tracking / "pressure_test_data",
        "results": tracking / "pressure_test_results",
        "combined": tracking / "pressure_test_results" / "combined_test_results",
        # Plot files go directly to the website directory so the site can use
        # them without copying files from the processing results directory.
        "plots": PLOT_ROOTS[USER],
    }


def _persist_new_floats(paths):
    """Add successfully configured new floats to this script permanently."""
    # A float is considered complete only when its final calculated workbook
    # exists.  Missing input files therefore remain in NEW_FLOATS for review.
    pending = [
        sn for sn in NEW_FLOATS
        if sn not in FLOAT_SERIAL_NUMBERS
        and (paths["combined"] / f"{sn}_calcs_.xlsx").exists()
    ]
    if not pending:
        return

    # Update the in-memory list immediately so the current run includes them.
    FLOAT_SERIAL_NUMBERS.extend(pending)

    # Rewrite only the two configuration blocks in this script.  The rest of
    # the program is left untouched.
    script_path = Path(__file__).resolve()
    source = script_path.read_text(encoding="utf-8")
    serial_block = "FLOAT_SERIAL_NUMBERS = [\n" + "\n".join(
        f'    "{sn}",' for sn in FLOAT_SERIAL_NUMBERS
    ) + "\n]"
    source = re.sub(
        r"FLOAT_SERIAL_NUMBERS = \[.*?\n\]",
        serial_block,
        source,
        count=1,
        flags=re.DOTALL,
    )
    source = re.sub(
        r"NEW_FLOATS = \{.*?\n\}",
        "NEW_FLOATS = {\n}",
        source,
        count=1,
        flags=re.DOTALL,
    )
    script_path.write_text(source, encoding="utf-8")
    NEW_FLOATS.clear()
    print(f"Permanently added floats: {', '.join(pending)}")


def _read_result_file(base: Path):
    """Read either the CSV or Excel form of a test-result file."""
    # Older outputs may be CSV while newer outputs are Excel, so try both.
    for suffix in (".csv", ".xlsx"):
        candidate = base.with_suffix(suffix)
        if candidate.exists():
            return pd.read_csv(candidate) if suffix == ".csv" else pd.read_excel(candidate)
    raise FileNotFoundError(f"No CSV or Excel result file found for {base}")


def create_results(serial_numbers, paths):
    """Convert raw pickle files into per-test pressure-test workbooks."""
    # Convert raw sensor pickles into a consistent workbook for each test.
    total = len(serial_numbers)
    for number, sn in enumerate(serial_numbers, start=1):
        if sn not in NEW_FLOATS:
            print(f"[create {number}/{total}] Skipping {sn}: no test date configured")
            continue
        source = paths["data"] / TEST_TYPE / sn / f"F{sn}_{NEW_FLOATS[sn]}.pkl"
        destination = paths["results"] / TEST_TYPE / f"{sn}_pressure_test_results_{TEST_TYPE}.xlsx"
        if destination.exists() and not OVERWRITE_EXISTING:
            print(f"[create {number}/{total}] Reusing {sn}")
            continue
        if not source.exists():
            print(f"[create {number}/{total}] Skipping {sn}: raw file not found")
            continue
        data = pd.read_pickle(source).copy()
        data["SN"] = sn
        if "HUMIDITY" in data.columns:
            data["HUMIDITY"] = pd.to_numeric(data["HUMIDITY"], errors="coerce")
        destination.parent.mkdir(parents=True, exist_ok=True)
        data.to_excel(destination, index=False)
        print(f"[create {number}/{total}] Created {destination}")


def combine_results(serial_numbers, paths):
    """Combine available valve and pump workbooks for each float."""
    # Combine whichever valve/pump files exist and label their source test.
    total = len(serial_numbers)
    for number, sn in enumerate(serial_numbers, start=1):
        destination = paths["combined"] / f"{sn}_pressure_test_results.xlsx"
        if destination.exists() and not OVERWRITE_EXISTING:
            print(f"[combine {number}/{total}] Reusing {sn}")
            continue
        frames = []
        test_types = ["valve", "pump"] if INCLUDE_PUMP_RESULTS else [TEST_TYPE]
        for test_type in test_types:
            base = paths["results"] / test_type / f"{sn}_pressure_test_results_{test_type}"
            try:
                frame = _read_result_file(base)
            except FileNotFoundError:
                continue
            frame = frame.drop(columns=["Unnamed: 0"], errors="ignore")
            frame["Test Type"] = test_type
            frames.append(frame)
        if not frames:
            print(f"[combine {number}/{total}] Skipping {sn}: no result files found")
            continue
        combined = pd.concat(frames, ignore_index=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        combined.to_excel(destination, index=False)
        print(f"[combine {number}/{total}] Combined {len(combined):,} rows -> {destination}")


def _calibration_coefficients(metadata, sensor_name):
    """Extract one sensor's coefficient dictionary from ``get_cal_sn`` output.

    The API wrapper returns a DataFrame, while older local code sometimes
    represented the same response as nested dictionaries.  Supporting both
    forms keeps the processing stage independent of that representation.
    """
    coefficient_key = "PREDEPLOYMENT_CALIB_COEFFICIENT"
    if isinstance(metadata, pd.DataFrame):
        if sensor_name in metadata.columns:
            values = metadata[sensor_name].dropna().tolist()
            for value in values:
                if isinstance(value, dict):
                    return value.get(coefficient_key, value)
        if {"SENSOR", coefficient_key}.issubset(metadata.columns):
            rows = metadata.loc[metadata["SENSOR"].astype(str) == sensor_name, coefficient_key]
            if not rows.empty:
                value = rows.iloc[0]
                return value if isinstance(value, dict) else dict(value)
        raise KeyError(f"Could not find {sensor_name} calibration in API response columns: {list(metadata.columns)}")

    if isinstance(metadata, dict):
        value = metadata[sensor_name]
        if isinstance(value, dict):
            return value.get(coefficient_key, value)

    raise TypeError(f"Unsupported calibration response type: {type(metadata).__name__}")


def add_calculations(serial_numbers, paths):
    """Apply calibration equations and save one calculated workbook per float."""
    import gsw

    total = len(serial_numbers)
    for number, sn in enumerate(serial_numbers, start=1):
        source = paths["combined"] / f"{sn}_pressure_test_results.xlsx"
        destination = paths["combined"] / f"{sn}_calcs_.xlsx"
        if destination.exists() and not OVERWRITE_EXISTING:
            print(f"[calcs {number}/{total}] Reusing {sn}")
            continue
        if not source.exists():
            print(f"[calcs {number}/{total}] Skipping {sn}: combined file not found")
            continue
        print(f"[calcs {number}/{total}] Requesting calibration and calculating {sn}")
        data = pd.read_excel(source)
        data["DATE"] = pd.to_datetime(data["DATE"])
        data = data.sort_values("DATE").reset_index(drop=True)
        meta = get_cal_sn(str(sn))
        cal = _calibration_coefficients(meta, "TRANSISTOR_PH").copy()
        cal_o = _calibration_coefficients(meta, "OPTODE_DOXY")
        cal_cdom = _calibration_coefficients(meta, "FLUOROMETER_CDOM")
        cal_chla = _calibration_coefficients(meta, "FLUOROMETER_CHLA")
        cal_bbp = _calibration_coefficients(meta, "BACKSCATTERINGMETER_BBP700")
        if "K2" not in cal and "K2f0" in cal:
            cal["K2"] = cal["K2f0"]
        cal.setdefault("K0", -1.32)
        _, ph = pH_sbe(cal, data["PH_VRS"], data["PRES"], data["TEMP"], data["PSAL"])
        oxygen = o2_sbe(cal_o, data["O2_PHASE_DELAY"], data["O2_TEMPERATURE_VOLTAGE"], data["PRES"], data["TEMP"], data["PSAL"])[0]
        output = pd.DataFrame({
            "PH_9": ph, "PRES": data["PRES"], "DATE": data["DATE"], "PSAL": data["PSAL"], "TEMP": data["TEMP"], "OXYGEN": oxygen,
            "FCDOM": mcoms(scale=cal_cdom["SCALE_CDOM"], dark=cal_cdom["DARK_CDOM"], counts=data["MCOMS1"]),
            "FCHLA": mcoms(scale=cal_chla["SCALE_CHLA"], dark=cal_chla["DARK_CHLA"], counts=data["MCOMS2"]),
            "BBP": mcoms(scale=cal_bbp["SCALE_BACKSCATTERING700"], dark=cal_bbp["DARK_BACKSCATTERING700"], counts=data["MCOMS3"]),
            "PTEMP": gsw.conversions.pt0_from_t(data["PSAL"], data["TEMP"], data["PRES"]),
            "rawFCDOM": data["MCOMS1"], "rawFCHLA": data["MCOMS2"], "rawBBP": data["MCOMS3"],
        })
        for column in ["HUMIDITY", "BUOYANCY_POSITION", "PH_VRS", "PH_VK", "O2_PHASE_DELAY", "O2_TEMPERATURE_VOLTAGE", "PH_IK", "PH_IB"]:
            if column in data.columns:
                output[column.replace("BUOYANCY_POSITION", "Buoyancy Position")] = data[column]
        destination.parent.mkdir(parents=True, exist_ok=True)
        output.to_excel(destination, index=False)
        print(f"[calcs {number}/{total}] Added calculations -> {destination}")


def diff_analysis(sn: str, paths):
    """Build the plotting dataframe from calculated and raw result files."""
    # Read the calibrated values, attach buoyancy position from the raw file,
    # and calculate elapsed time from the first sample.
    calculated = pd.read_excel(paths["combined"] / f"{sn}_calcs_.xlsx")
    raw = pd.read_excel(paths["combined"] / f"{sn}_pressure_test_results.xlsx")
    calculated["DATE"] = pd.to_datetime(calculated["DATE"])
    calculated = calculated.sort_values("DATE").reset_index(drop=True)
    result = calculated.copy()
    result.insert(0, "Float Number", f"{sn}, Test Start: {result['DATE'].iloc[0]}")
    if "BUOYANCY_POSITION" in raw.columns:
        result["Buoyancy Position"] = raw["BUOYANCY_POSITION"].to_numpy()[: len(result)]
    result["Time Since Test Start (hours)"] = (result["DATE"] - result["DATE"].iloc[0]).dt.total_seconds() / 3600
    return result


def _finish_plot(fig, output_path: Path, *, save: bool, show: bool):
    if save:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(output_path, include_plotlyjs="cdn")
        if not output_path.exists():
            raise IOError(f"Plot write failed: {output_path}")
        print(f"Saved plot: {output_path}")
    if show:
        fig.show()


def _common_layout(fig, title, x_title, y_title):
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        template="plotly_white",
        hovermode="closest",
        legend_title_text="Float",
        legend={"font": {"size": 11}, "itemsizing": "constant"},
        margin={"l": 80, "r": 30, "t": 70, "b": 70},
        font={"size": 13},
    )
    fig.update_xaxes(title=x_title, showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    fig.update_yaxes(title=y_title, showgrid=True, gridcolor="#e5e7eb", zeroline=False)


def _serial_sort_key(label):
    """Sort legend labels by numeric float serial number."""
    serial_number = str(label).split(" — ", 1)[0].strip()
    try:
        return (0, int(serial_number))
    except ValueError:
        return (1, serial_number)


def _make_plot(data, parameter, output_dir, *, pressure_plot, save, show):
    # The same helper creates both time-series and pressure plots.  Time-series
    # plots use connected lines; pressure profiles use small translucent points
    # so dense data does not turn into a solid block of color.
    x, y = (parameter, "PRES") if pressure_plot else ("Time Since Test Start (hours)", parameter)
    title = f"{LABELS.get(parameter, parameter)} vs. {'Pressure' if pressure_plot else 'Test Time'}"
    plot_data = data.copy()
    # Keep the test date in the grouping key so separate tests for the same
    # float do not get connected into one trace.  Keep the full timestamp in
    # Float Number for hover details.
    float_parts = plot_data["Float Number"].astype(str).str.extract(
        r"^([^,]+),\s*Test Start:\s*(\d{4}-\d{2}-\d{2})"
    )
    plot_data["Float"] = (
        float_parts[0].fillna(plot_data["Float Number"].astype(str))
        + " — "
        + float_parts[1].fillna("")
    ).str.rstrip(" —")
    legend_order = sorted(plot_data["Float"].dropna().unique(), key=_serial_sort_key)
    hover_data = {
        "Float Number": True,
        "Float": False,
        "PRES": ":.1f",
        parameter: ":.4g",
    }
    if pressure_plot:
        fig = px.scatter(
            plot_data,
            x=x,
            y=y,
            color="Float",
            category_orders={"Float": legend_order},
            render_mode="webgl",
            opacity=0.55,
            labels=LABELS,
            title=title,
            hover_data=hover_data,
        )
        fig.update_traces(marker={"size": 4})
    else:
        plot_data = plot_data.sort_values(["Float", "Time Since Test Start (hours)"])
        fig = px.line(
            plot_data,
            x=x,
            y=y,
            color="Float",
            category_orders={"Float": legend_order},
            labels=LABELS,
            title=title,
            hover_data=hover_data,
        )
        fig.update_traces(line={"width": 1.5})
    _common_layout(fig, title, LABELS.get(x, x), LABELS.get(y, y))
    if pressure_plot:
        fig.update_yaxes(autorange="reversed")
        filename = f"P vs. {parameter}.html"
    else:
        filename = f"{parameter}.html"
    _finish_plot(fig, output_dir / filename, save=save, show=show)


def _make_date_grouped_plots(data, output_dir, *, save, show):
    """Create flow-through-style plots grouped by test start date.

    These plots are written below the normal plot root, without changing the
    filenames or contents of the existing time and pressure plots.
    """
    grouped = data.copy()
    grouped["DATE"] = pd.to_datetime(grouped["DATE"], errors="coerce")
    grouped = grouped.dropna(subset=["DATE", "Float Number"])
    if grouped.empty:
        return

    # Assign every sample in a run to that run's first calendar date. This
    # prevents a test crossing midnight from being split between two files.
    start_dates = grouped.groupby("Float Number")["DATE"].transform("min")
    grouped["Test Date"] = start_dates.dt.strftime("%Y-%m-%d")
    grouped_output = output_dir / "date_grouped"

    parameters = [p for p in PLOT_PARAMETERS if p in grouped.columns]
    if "PRES" in grouped.columns and "PRES" not in parameters:
        parameters.append("PRES")

    for parameter in parameters:
        parameter_data = grouped.loc[grouped[parameter].notna()].copy()
        for test_date, date_data in parameter_data.groupby("Test Date", sort=True):
            date_data = date_data.sort_values(["Float Number", "DATE"])
            title = f"{LABELS.get(parameter, parameter)} vs. Date — {test_date}"
            fig = px.scatter(
                date_data,
                x="DATE",
                y=parameter,
                color="Float Number",
                labels=LABELS,
                title=title,
                render_mode="webgl",
                hover_data={
                    "Float Number": True,
                    "DATE": "|%Y-%m-%d %H:%M:%S",
                    "PRES": ":.1f" if "PRES" in date_data else False,
                    parameter: ":.4g",
                },
            )
            _common_layout(fig, title, "Date/time", LABELS.get(parameter, parameter))
            _finish_plot(
                fig,
                grouped_output / parameter / f"{test_date}.html",
                save=save,
                show=show,
            )


def make_plots(serial_numbers, paths):
    # Load all floats once, then create the selected plots from the combined
    # in-memory DataFrame rather than repeatedly loading each float per plot.
    print(f"[plots] Loading {len(serial_numbers)} calculated float files")
    frames = []
    for sn in serial_numbers:
        try:
            frames.append(diff_analysis(sn, paths))
        except FileNotFoundError as error:
            print(f"Skipping {sn}: {error}")
    if not frames:
        raise FileNotFoundError("No calculated float files were available for plotting.")
    data = pd.concat(frames, ignore_index=True, copy=False)
    data = data.loc[data["PRES"].notna() & (data["PRES"] <= 3000)].copy()
    output_dir = paths["plots"]
    print(f"[plots] Output directory: {output_dir}")
    print(f"[plots] SAVE_PLOTS={SAVE_PLOTS}, SHOW_PLOTS={SHOW_PLOTS}")
    if SAVE_PLOTS:
        output_dir.mkdir(parents=True, exist_ok=True)
    parameters = [p for p in PLOT_PARAMETERS if p in data.columns]
    total_plots = len(parameters) * 2
    for number, parameter in enumerate(parameters, start=1):
        print(f"[plots {2 * number - 1}/{total_plots}] Creating {parameter} time plot")
        _make_plot(data, parameter, output_dir, pressure_plot=False, save=SAVE_PLOTS, show=SHOW_PLOTS)
        print(f"[plots {2 * number}/{total_plots}] Creating {parameter} pressure plot")
        _make_plot(data, parameter, output_dir, pressure_plot=True, save=SAVE_PLOTS, show=SHOW_PLOTS)
    for column in ["PRES", "HUMIDITY", "Buoyancy Position"]:
        if column not in data.columns:
            continue
        simple = data.loc[data[column].notna()].copy()
        if column == "Buoyancy Position":
            simple = simple.loc[simple[column] <= 951].copy()
        _make_plot(simple, column, output_dir, pressure_plot=False, save=SAVE_PLOTS, show=SHOW_PLOTS)
    if SAVE_DATE_GROUPED_PLOTS or SHOW_DATE_GROUPED_PLOTS:
        print("[plots] Creating date-grouped plots")
        _make_date_grouped_plots(
            data,
            output_dir,
            save=SAVE_DATE_GROUPED_PLOTS,
            show=SHOW_DATE_GROUPED_PLOTS,
        )


def main():
    print("Starting pressure-test pipeline")
    paths = _paths()
    # In incremental mode, only the serial numbers explicitly added to
    # NEW_FLOATS are processed by the data-creation/calibration stages.
    serial_numbers = list(NEW_FLOATS) if PROCESS_ONLY_NEW_FLOATS else FLOAT_SERIAL_NUMBERS
    if PROCESS_ONLY_NEW_FLOATS and not serial_numbers:
        print("No new floats configured; skipping new-float processing stages.")
    if RUN_CREATE_RESULTS:
        print("Stage 1/4: creating per-test result files")
        create_results(serial_numbers, paths)
    if RUN_COMBINE_RESULTS:
        print("Stage 2/4: combining test result files")
        combine_results(serial_numbers, paths)
    if RUN_ADD_CALCULATIONS:
        print("Stage 3/4: adding calibrated sensor calculations")
        add_calculations(serial_numbers, paths)
    # Persist new serial numbers only after all requested data-processing
    # stages have completed without an exception.
    _persist_new_floats(paths)
    if RUN_PLOTS:
        print("Stage 4/4: generating plots")
        # Include the newly added floats in the aggregate plots even when they
        # were not yet added to the historical FLOAT_SERIAL_NUMBERS list.
        plot_serial_numbers = list(dict.fromkeys(FLOAT_SERIAL_NUMBERS + serial_numbers)) if PLOT_ALL_FLOATS else serial_numbers
        make_plots(plot_serial_numbers, paths)
    print("Pipeline complete")


if __name__ == "__main__":
    main()
