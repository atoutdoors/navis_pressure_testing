"""Testing entry point for the optimized pressure-test visualization.

This keeps the normal optimized plots and adds flow-through-style plots grouped
by calendar test date.  The grouped plots use the original ``DATE`` values on
the x-axis, so each HTML file contains only floats from one test date.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px

import ptest_visualization_optimized as optimized


# Keep this separate from the production script while the date-based layout is
# being evaluated.  Override these values here when testing is meant to write
# files or open figures in a browser.
SAVE_DATE_GROUPED_PLOTS = optimized.SAVE_PLOTS
SHOW_DATE_GROUPED_PLOTS = optimized.SHOW_PLOTS
DATE_GROUPED_DIRNAME = "date_grouped"


def _date_group_label(value) -> str:
    """Return a stable, filesystem-safe calendar-date label."""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def make_date_grouped_plots(serial_numbers, paths, *, save=None, show=None):
    """Create one flow-through-style plot per parameter and test date.

    Each calculated workbook is treated as one test run.  Floats whose first
    sample falls on the same calendar date are combined into the same plot,
    while different dates are written to separate files and never connected
    into one trace.
    """
    save = SAVE_DATE_GROUPED_PLOTS if save is None else save
    show = SHOW_DATE_GROUPED_PLOTS if show is None else show

    frames = []
    for serial_number in serial_numbers:
        try:
            frame = optimized.diff_analysis(str(serial_number), paths)
        except (FileNotFoundError, KeyError, IndexError) as error:
            print(f"[date plots] Skipping {serial_number}: {error}")
            continue
        frame = frame.copy()
        frame["DATE"] = pd.to_datetime(frame["DATE"], errors="coerce")
        frame = frame.dropna(subset=["DATE"])
        if frame.empty:
            continue
        # Match flowthrough's convention: the date is the test start date,
        # not the date of each individual sample in a run.
        frame["Test Date"] = _date_group_label(frame["DATE"].iloc[0])
        frames.append(frame)

    if not frames:
        raise FileNotFoundError("No calculated float files were available for date-grouped plots.")

    data = pd.concat(frames, ignore_index=True, copy=False)
    parameters = [
        parameter for parameter in optimized.PLOT_PARAMETERS
        if parameter in data.columns
    ]
    if "PRES" in data.columns and "PRES" not in parameters:
        parameters.append("PRES")

    output_dir = paths["plots"] / DATE_GROUPED_DIRNAME
    for parameter in parameters:
        parameter_data = data.loc[data[parameter].notna()].copy()
        for test_date, date_data in parameter_data.groupby("Test Date", sort=True):
            date_data = date_data.sort_values(["Float Number", "DATE"])
            title = f"{optimized.LABELS.get(parameter, parameter)} vs. Date — {test_date}"
            fig = px.scatter(
                date_data,
                x="DATE",
                y=parameter,
                color="Float Number",
                labels=optimized.LABELS,
                title=title,
                render_mode="webgl",
                hover_data={
                    "Float Number": True,
                    "DATE": "|%Y-%m-%d %H:%M:%S",
                    "PRES": ":.1f" if "PRES" in date_data else False,
                    parameter: ":.4g",
                },
            )
            optimized._common_layout(
                fig,
                title,
                "Date/time",
                optimized.LABELS.get(parameter, parameter),
            )
            optimized._finish_plot(
                fig,
                output_dir / parameter / f"{_date_group_label(test_date)}.html",
                save=save,
                show=show,
            )


def main():
    """Run the optimized pipeline followed by the experimental date plots."""
    optimized.main()
    serial_numbers = list(dict.fromkeys(
        optimized.FLOAT_SERIAL_NUMBERS
        + list(optimized.NEW_FLOATS)
    ))
    make_date_grouped_plots(serial_numbers, optimized._paths())


if __name__ == "__main__":
    main()
