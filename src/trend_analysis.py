"""
Trend analysis for FDA adverse-event reports.

This module prepares time-series data for the Streamlit dashboard.

It can calculate:
- Overall adverse-event report volume over time
- Drug-specific report trends
- Reaction-specific report trends
- Drug + reaction trends
"""

from typing import Optional

import pandas as pd


# -------------------------------------------------------------------
# Required columns
# -------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "report_id",
    "received_date",
}

# Valid pandas offset alias tokens (non-exhaustive; covers common use).
_VALID_FREQUENCIES = {"D", "W", "M", "Q", "Y", "H", "T", "S", "ME", "QE", "YE"}


# -------------------------------------------------------------------
# Main trend analysis
# -------------------------------------------------------------------

def calculate_report_trend(
    dataframe: pd.DataFrame,
    frequency: str = "M",
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    drop_partial_periods: bool = False,
) -> pd.DataFrame:
    """
    Calculate adverse-event report volume over time.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Normalized FDA adverse-event dataframe.

    frequency : str
        Pandas time frequency.

        Common values:
            "D" = daily
            "W" = weekly
            "M" = monthly
            "Q" = quarterly
            "Y" = yearly

    drug_name : str, optional
        Filter trend to a specific drug (case-insensitive).

    reaction : str, optional
        Filter trend to a specific reaction (case-insensitive).

    start_date : str, optional
        Inclusive lower bound for ``received_date`` (e.g. ``"2020-01-01"``).
        Rows before this date are excluded.

    end_date : str, optional
        Inclusive upper bound for ``received_date`` (e.g. ``"2023-12-31"``).
        Rows after this date are excluded.

    drop_partial_periods : bool
        When ``True``, the first and last periods in the result are removed.
        Useful when the boundary periods contain only a fraction of the
        expected reporting days, which would make those bars misleadingly low.

    Returns
    -------
    pandas.DataFrame
        Time-series dataframe with columns ``period`` and ``report_count``,
        sorted ascending by ``period``.
    """

    _validate_dataframe(dataframe)

    if not frequency:
        raise ValueError("frequency cannot be empty.")

    result = dataframe.copy()

    # ---------------------------------------------------------------
    # Convert date column
    # ---------------------------------------------------------------

    result["received_date"] = pd.to_datetime(
        result["received_date"],
        errors="coerce",
    )

    result = result.dropna(subset=["received_date"])

    # ---------------------------------------------------------------
    # Apply date range filter
    # ---------------------------------------------------------------

    if start_date is not None:
        try:
            start_ts = pd.Timestamp(start_date)
        except Exception as exc:
            raise ValueError(
                f"Invalid start_date: {start_date!r}"
            ) from exc
        result = result[result["received_date"] >= start_ts]

    if end_date is not None:
        try:
            end_ts = pd.Timestamp(end_date)
        except Exception as exc:
            raise ValueError(
                f"Invalid end_date: {end_date!r}"
            ) from exc
        result = result[result["received_date"] <= end_ts]

    # ---------------------------------------------------------------
    # Filter by drug
    # ---------------------------------------------------------------

    if drug_name:
        if "drug_name" not in result.columns:
            raise ValueError(
                "drug_name column is required for drug filtering."
            )

        normalized_drug = drug_name.strip().upper()

        result = result[
            result["drug_name"]
            .astype(str)
            .str.strip()
            .str.upper()
            == normalized_drug
        ]

    # ---------------------------------------------------------------
    # Filter by reaction
    # ---------------------------------------------------------------

    if reaction:
        if "reaction" not in result.columns:
            raise ValueError(
                "reaction column is required for reaction filtering."
            )

        normalized_reaction = reaction.strip().upper()

        result = result[
            result["reaction"]
            .astype(str)
            .str.strip()
            .str.upper()
            == normalized_reaction
        ]

    if result.empty:
        return pd.DataFrame(columns=["period", "report_count"])

    # ---------------------------------------------------------------
    # Remove duplicate report IDs.
    #
    # A single FDA report can contain multiple drug/reaction
    # combinations. For report-volume trends we count the report
    # once rather than counting every combination separately.
    # ---------------------------------------------------------------

    result = result.drop_duplicates(subset=["report_id"])

    # ---------------------------------------------------------------
    # Create time period
    # ---------------------------------------------------------------

    try:
        result = result.copy()
        result["period"] = result["received_date"].dt.to_period(frequency)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported frequency: {frequency!r}"
        ) from exc

    # ---------------------------------------------------------------
    # Count reports
    # ---------------------------------------------------------------

    trend = (
        result.groupby("period")
        .agg(report_count=("report_id", "nunique"))
        .reset_index()
    )

    # Convert Period to timestamp so Plotly can directly use it.
    trend["period"] = trend["period"].dt.to_timestamp()

    trend = trend.sort_values("period").reset_index(drop=True)

    # ---------------------------------------------------------------
    # Optionally drop the first and last (likely partial) periods.
    # ---------------------------------------------------------------

    if drop_partial_periods and len(trend) > 2:
        trend = trend.iloc[1:-1].reset_index(drop=True)

    return trend


# -------------------------------------------------------------------
# Monthly trend
# -------------------------------------------------------------------

def calculate_monthly_trend(
    dataframe: pd.DataFrame,
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate monthly adverse-event report volume.
    """

    return calculate_report_trend(
        dataframe=dataframe,
        frequency="M",
        drug_name=drug_name,
        reaction=reaction,
        start_date=start_date,
        end_date=end_date,
    )


# -------------------------------------------------------------------
# Weekly trend
# -------------------------------------------------------------------

def calculate_weekly_trend(
    dataframe: pd.DataFrame,
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate weekly adverse-event report volume.
    """

    return calculate_report_trend(
        dataframe=dataframe,
        frequency="W",
        drug_name=drug_name,
        reaction=reaction,
        start_date=start_date,
        end_date=end_date,
    )


# -------------------------------------------------------------------
# Daily trend
# -------------------------------------------------------------------

def calculate_daily_trend(
    dataframe: pd.DataFrame,
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate daily adverse-event report volume.
    """

    return calculate_report_trend(
        dataframe=dataframe,
        frequency="D",
        drug_name=drug_name,
        reaction=reaction,
        start_date=start_date,
        end_date=end_date,
    )


# -------------------------------------------------------------------
# Compare drug trends
# -------------------------------------------------------------------

def compare_drug_trends(
    dataframe: pd.DataFrame,
    drug_names: list[str],
    frequency: str = "M",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate report trends for multiple drugs.

    Returns a dataframe suitable for a multi-line Plotly chart.

    Example output:

        period       drug_name       report_count
        2026-01-01  DRUG A          120
        2026-01-01  DRUG B          95
        2026-02-01  DRUG A          140
        ...
    """

    if not drug_names:
        raise ValueError(
            "drug_names must contain at least one drug."
        )

    all_trends = []

    for drug in drug_names:
        trend = calculate_report_trend(
            dataframe=dataframe,
            frequency=frequency,
            drug_name=drug,
            start_date=start_date,
            end_date=end_date,
        )

        if trend.empty:
            continue

        trend["drug_name"] = drug.strip().upper()
        all_trends.append(trend)

    if not all_trends:
        return pd.DataFrame(
            columns=["period", "report_count", "drug_name"]
        )

    return pd.concat(all_trends, ignore_index=True)


# -------------------------------------------------------------------
# Compare reaction trends
# -------------------------------------------------------------------

def compare_reaction_trends(
    dataframe: pd.DataFrame,
    reactions: list[str],
    frequency: str = "M",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate report trends for multiple reactions.

    Returns a long-format dataframe suitable for a multi-line Plotly chart.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Normalized FDA adverse-event dataframe.
    reactions : list[str]
        Reaction names to compare (case-insensitive).
    frequency : str
        Pandas time frequency (default ``"M"`` = monthly).
    start_date : str, optional
        Inclusive lower bound for ``received_date``.
    end_date : str, optional
        Inclusive upper bound for ``received_date``.

    Returns
    -------
    pandas.DataFrame
        Columns: ``period``, ``report_count``, ``reaction``.
    """

    if not reactions:
        raise ValueError(
            "reactions must contain at least one reaction."
        )

    all_trends = []

    for rxn in reactions:
        trend = calculate_report_trend(
            dataframe=dataframe,
            frequency=frequency,
            reaction=rxn,
            start_date=start_date,
            end_date=end_date,
        )

        if trend.empty:
            continue

        trend["reaction"] = rxn.strip().upper()
        all_trends.append(trend)

    if not all_trends:
        return pd.DataFrame(
            columns=["period", "report_count", "reaction"]
        )

    return pd.concat(all_trends, ignore_index=True)


# -------------------------------------------------------------------
# Trend statistics
# -------------------------------------------------------------------

def get_trend_statistics(
    trend_dataframe: pd.DataFrame,
) -> dict:
    """
    Calculate summary statistics from trend data.

    Returns
    -------
    dict
        Keys:
            total_reports              – sum of all report counts
            period_count               – number of time periods
            average_reports_per_period – arithmetic mean
            median_reports_per_period  – median
            highest_period             – timestamp of peak period
            highest_report_count       – count at peak period
            lowest_period              – timestamp of lowest period
            lowest_report_count        – count at lowest period
    """

    if trend_dataframe is None or trend_dataframe.empty:
        return {
            "total_reports": 0,
            "period_count": 0,
            "average_reports_per_period": 0.0,
            "median_reports_per_period": 0.0,
            "highest_period": None,
            "highest_report_count": 0,
            "lowest_period": None,
            "lowest_report_count": 0,
        }

    trend = trend_dataframe.copy()

    highest_row = trend.loc[trend["report_count"].idxmax()]
    lowest_row = trend.loc[trend["report_count"].idxmin()]

    return {
        "total_reports": int(trend["report_count"].sum()),
        "period_count": len(trend),
        "average_reports_per_period": float(
            trend["report_count"].mean()
        ),
        "median_reports_per_period": float(
            trend["report_count"].median()
        ),
        "highest_period": highest_row["period"],
        "highest_report_count": int(highest_row["report_count"]),
        "lowest_period": lowest_row["period"],
        "lowest_report_count": int(lowest_row["report_count"]),
    }


# -------------------------------------------------------------------
# Calculate percentage change
# -------------------------------------------------------------------

def add_period_change(
    trend_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add period-over-period percentage change column.

    The first row will have ``NaN`` for ``percentage_change`` because
    there is no prior period to compare against.

    Example:
        Current month = 150
        Previous month = 100

        Change = 50%
    """

    if trend_dataframe is None or trend_dataframe.empty:
        return trend_dataframe.copy() if trend_dataframe is not None else pd.DataFrame()

    result = trend_dataframe.copy()

    result["percentage_change"] = (
        result["report_count"]
        .pct_change()
        .mul(100)
        .round(2)
    )

    return result


# -------------------------------------------------------------------
# Rolling average
# -------------------------------------------------------------------

def add_rolling_average(
    trend_dataframe: pd.DataFrame,
    window: int = 3,
    column_name: str = "rolling_avg",
) -> pd.DataFrame:
    """
    Append a rolling mean of ``report_count`` to the trend dataframe.

    Useful for smoothing noisy time-series data before rendering a
    Plotly chart.

    Parameters
    ----------
    trend_dataframe : pandas.DataFrame
        Output of any ``calculate_*_trend`` function.
    window : int
        Number of periods to include in the rolling window (default 3).
        Must be >= 1.
    column_name : str
        Name of the new column (default ``"rolling_avg"``).

    Returns
    -------
    pandas.DataFrame
        Original dataframe with the rolling average column appended.
        The first ``window - 1`` rows will contain ``NaN``.
    """

    if trend_dataframe is None or trend_dataframe.empty:
        return trend_dataframe.copy() if trend_dataframe is not None else pd.DataFrame()

    if window < 1:
        raise ValueError("window must be >= 1.")

    result = trend_dataframe.copy()

    result[column_name] = (
        result["report_count"]
        .rolling(window=window, min_periods=1)
        .mean()
        .round(2)
    )

    return result


# -------------------------------------------------------------------
# Prepare Plotly data
# -------------------------------------------------------------------

def prepare_trend_for_chart(
    trend_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare trend dataframe for Plotly visualization.

    Renames ``period`` to ``date`` and returns only the
    ``date`` and ``report_count`` columns, sorted ascending.
    """

    if trend_dataframe is None or trend_dataframe.empty:
        return pd.DataFrame(columns=["date", "report_count"])

    result = trend_dataframe.copy()

    result["date"] = pd.to_datetime(
        result["period"],
        errors="coerce",
    )

    result = result.dropna(subset=["date"])

    result = result.sort_values("date").reset_index(drop=True)

    return result[["date", "report_count"]]


# -------------------------------------------------------------------
# Internal validation
# -------------------------------------------------------------------

def _validate_dataframe(
    dataframe: pd.DataFrame,
    extra_columns: Optional[set] = None,
) -> None:
    """
    Validate the input dataframe.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        The dataframe to validate.
    extra_columns : set, optional
        Additional column names that must be present beyond
        ``REQUIRED_COLUMNS``.
    """

    if dataframe is None:
        raise ValueError("Dataframe cannot be None.")

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")

    required = REQUIRED_COLUMNS | (extra_columns or set())
    missing_columns = required - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing_columns))
        )


# -------------------------------------------------------------------
# Example execution
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("trend_analysis.py loaded successfully.")
    print(
        "Use calculate_monthly_trend(), "
        "calculate_weekly_trend(), or "
        "calculate_daily_trend() with a "
        "processed FDA dataframe."
    )
