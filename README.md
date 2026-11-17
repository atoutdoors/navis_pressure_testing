# Navis pressure testing

This repository contains the scripts for running a Navis pressure test, converting the raw measurements, applying sensor calibrations, and creating interactive plots.

The recommended analysis entry point is [`ptest_visualization_optimized.py`](ptest_visualization_optimized.py). It replaces the older, separate `create_results_1.py`, `combine_results_2opt.py`, `add_calcs_3.py`, and `ptest_analysis.py` workflow while keeping those scripts in `pressure_testing/analysis/` for reference.

## 1. Prepare the computer

The collection scripts communicate with the float through `navis_com`, which is imported from the separate `bgc-testing` repository. Before collecting data:

1. Connect the float and identify its serial COM port.
2. Make sure the `bgc-testing` repository is available at the path in `pressure_test.py` / `pressure_test2.py`, or update the `sys.path.append(...)` line in those scripts.
3. Map the WHOI shared drive as `G:`. The analysis script expects these folders:

   ```text
   G:\Shared drives\WHOI Argo\BGC\Float Tracking\pressure_test_data\
   G:\Shared drives\WHOI Argo\BGC\Float Tracking\pressure_test_results\
   ```

4. Install Python and the analysis dependencies. From this repository, run:

   ```text
   setup_pressure_test_env.bat
   ```

   This creates `.venv` and installs NumPy, pandas, Plotly, openpyxl, gsw, and requests. Activate it for later commands with:

   ```text
   .venv\Scripts\activate
   ```

The calibrated analysis requests the float's predeployment coefficients from `https://db.whoifloatgroup.org`, so internet access is required for the calibration stage.

## 2. Collect raw pressure-test data

Use one of the two collectors in `pressure_testing/`:

- `pressure_test.py`: standard valve pressure test columns.
- `pressure_test2.py`: same test with additional OCR and tilt columns.

Before running, edit the parameter block near the top of the selected script:

```python
run_until = "2026-12-31 00:00"   # stop time, YYYY-MM-DD HH:MM
measurement_interval = 0         # minutes between measurements
exercise_interval = 0.5          # hours between HP-valve exercises
exercise_n = 3                    # open/close cycles per exercise
save_directory = "G://Shared drives/WHOI Argo/BGC/Float Tracking/pressure_test_data/valve/2006/"
```

Use a folder named for the float serial number under the test type (`valve` or `pump`). This matches the layout expected by the analysis script:

```text
pressure_test_data\valve\2006\F2006_YYYYMMDD.pkl
```

The current collector asks for the COM port when it starts, wakes the float, records the serial number, samples pressure/sensor data, exercises the HP valve, and continuously overwrites the day's pickle file with the latest complete DataFrame. The float should be at the required starting buoyancy position before the run. Keep the terminal open while the test is running.

Run from the repository root, for example:

```text
.venv\Scripts\python.exe pressure_testing\pressure_test.py
```

When prompted, enter the COM port (for example `COM7`). If a pickle file for that float and date already exists, the script asks whether it may overwrite it. On an exception, the script attempts to freeze the float and close the serial connection; verify the float state before restarting.

If the collector was left with its original `save_directory` ending at `...\pressure_test_data\valve\`, move the resulting `F<serial>_<date>.pkl` into the serial-number folder shown above, or change the analysis input path accordingly.

## 3. Convert, calibrate, and plot the data

Edit the configuration section near the top of [`ptest_visualization_optimized.py`](ptest_visualization_optimized.py):

```python
USER = "Aidan"
TEST_TYPE = "valve"
INCLUDE_PUMP_RESULTS = True

NEW_FLOATS = {
    "2006": "20260806",  # serial number: date in the pickle filename
}

RUN_CREATE_RESULTS = True
RUN_COMBINE_RESULTS = True
RUN_ADD_CALCULATIONS = True
RUN_PLOTS = True
OVERWRITE_EXISTING = False
```

The date in `NEW_FLOATS` must exactly match the raw file name, such as `F2006_20260806.pkl`. Then run:

```text
.venv\Scripts\python.exe ptest_visualization_optimized.py
```

The four stages are:

1. **Create results** — converts each raw pickle into `pressure_test_results\valve\<serial>_pressure_test_results_valve.xlsx`.
2. **Combine results** — combines valve and, when enabled, pump workbooks into `pressure_test_results\combined_test_results\<serial>_pressure_test_results.xlsx`.
3. **Add calculations** — retrieves calibration coefficients and writes calibrated variables such as pH, oxygen, FDOM, chlorophyll, backscatter, and potential temperature to `<serial>_calcs_.xlsx`.
4. **Plot** — writes interactive Plotly HTML files to `Z:\www\bgc\pressure_test`.

The script reuses existing files by default. Set `OVERWRITE_EXISTING = True` when the raw data or configuration changed and the intermediate workbooks must be regenerated. After a new float is successfully calculated, the script adds its serial number to `FLOAT_SERIAL_NUMBERS` and clears `NEW_FLOATS` in the script.

### Plot existing calculated data only

To regenerate plots without repeating conversion or calibration:

```python
RUN_CREATE_RESULTS = False
RUN_COMBINE_RESULTS = False
RUN_ADD_CALCULATIONS = False
RUN_PLOTS = True
PROCESS_ONLY_NEW_FLOATS = False
PLOT_ALL_FLOATS = True
```

Set `PLOT_PARAMETERS` to a shorter list if only selected variables are needed. Each selected variable gets a test-time plot and a pressure plot. Pressure is displayed with increasing depth downward. The output directory contains files such as `TEMP.html` and `P vs. TEMP.html`.

## 4. Output layout

```text
pressure_test_data\<valve|pump>\<serial>\F<serial>_<YYYYMMDD>.pkl
pressure_test_results\<valve|pump>\<serial>_pressure_test_results_<type>.xlsx
pressure_test_results\combined_test_results\<serial>_pressure_test_results.xlsx
pressure_test_results\combined_test_results\<serial>_calcs_.xlsx
Z:\www\bgc\pressure_test\*.html
```

The plotting stage ignores samples with missing pressure and limits plotted pressure to 3000 dbar. Open the generated HTML files in a browser to use Plotly zooming, hovering, and legend selection.

## 5. Older scripts and notebooks

The scripts under `pressure_testing/analysis/` are the original manual workflow:

1. `create_results_1.py` — edit `name`, `SN`, `test`, and `date` to create a per-test Excel file.
2. `combine_results_2opt.py` — edit `floatnum` and combine test workbooks. Pump input is commented out in the checked-in version.
3. `add_calcs_3.py` — edit `SN` and apply calibration equations to create `<serial>_calcs_.xlsx`.
4. `ptest_analysis.py` or `analysis_4.py` — add elapsed time, buoyancy position, and oxygen-solubility analysis to `<serial>_calcs_added.xlsx`.

The notebooks in the same directory are exploratory plotting and merging tools. Use the optimized script for new tests unless a legacy notebook or intermediate calculation is specifically needed.

## Troubleshooting

- **Raw file not found:** verify the serial-number folder, test type, and date in `NEW_FLOATS` match the actual pickle path.
- **No plots are created:** confirm that `<serial>_calcs_.xlsx` exists, `RUN_PLOTS` and `SAVE_PLOTS` are `True`, and `PLOT_PARAMETERS` contains columns in that workbook.
- **Calibration failure:** check internet access and confirm that the WHOI calibration API has metadata for the float and the expected sensor names.
- **Drive/path errors:** map `G:` and `Z:`, or update `DRIVE_ROOTS` and `PLOT_ROOTS` in the visualization script for the local machine.
- **COM/`navis_com` errors:** check the COM port, float connection, and the `bgc-testing` repository path used by the collector.
