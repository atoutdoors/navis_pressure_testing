# Pressure Test Visualization

This script processes pressure-test data and creates interactive Plotly plots.
It combines the work previously handled by several separate scripts.

## What it does

The script can:

1. Convert raw pickle files into Excel result files.
2. Combine valve and pump test results.
3. Calculate calibrated pH, oxygen, FDOM, chlorophyll, and backscatter values.
4. Create time-series and pressure plots.
5. Save plots as interactive HTML files.

## Before running

Install the required packages:

```bash
pip install numpy pandas plotly openpyxl gsw requests
```

Make sure the `G:` and `Z:` drives are mapped on Windows:

- `G:` contains the pressure-test input and result files.
- `Z:` contains the website plot directory.

The script contains the sensor-calculation and API functions internally, so no separate `calc_sensor.py` or `db_api.py` file is required.

## Adding a new float

Add the serial number and pickle-file date to `NEW_FLOATS` near the top of the script:

```python
NEW_FLOATS = {
    "2006": "20260806",
}
```

The date must match the date in the pickle filename:

```text
F2006_20260806.pkl
```

Leave this setting enabled to process only newly added floats:

```python
PROCESS_ONLY_NEW_FLOATS = True
```

After the calculated file is created successfully, the script permanently adds the serial number to `FLOAT_SERIAL_NUMBERS` and removes it from `NEW_FLOATS`.

## Main settings

```python
RUN_CREATE_RESULTS = False
RUN_COMBINE_RESULTS = False
RUN_ADD_CALCULATIONS = False
RUN_PLOTS = True
```

Set a stage to `True` when you want it to run. For a new raw pickle file, use:

```python
RUN_CREATE_RESULTS = True
RUN_COMBINE_RESULTS = True
RUN_ADD_CALCULATIONS = True
RUN_PLOTS = True
```

Existing output files are reused by default. Set this to `True` to recalculate them:

```python
OVERWRITE_EXISTING = True
```

## Plot settings

```python
SAVE_PLOTS = True
SHOW_PLOTS = False
PLOT_ALL_FLOATS = True
```

- `SAVE_PLOTS`: saves interactive HTML plots.
- `SHOW_PLOTS`: opens plots while the script runs.
- `PLOT_ALL_FLOATS`: includes existing floats and newly processed floats in the plots.

Plots are saved to:

```text
Z:\www\bgc\pressure_test
```

The script prints the exact output path for every saved plot.

## Running the script

From a terminal or Python environment, run:

```bash
python ptest_visualization_optimized.py
```

The script prints progress for each stage and each float. If there are no new floats in `NEW_FLOATS`, the new-float stages are skipped and existing calculated files can still be used to regenerate plots.
