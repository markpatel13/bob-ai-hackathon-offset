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


# -------------------------------------------------------------------
# Main trend analysis
# -------------------------------------------------------------------

def calculate_report_trend(
    dataframe: pd.DataFrame,
    frequency: str = "M",
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
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
        Filter trend to a specific drug.

    reaction : str, optional
        Filter trend to a specific reaction.

    Returns
    -------
    pandas.DataFrame
        Time-series dataframe with report counts.
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

    result = result.dropna(
        subset=["received_date"]
    )

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
            .str.upper()
            == normalized_reaction
        ]

    if result.empty:
        return pd.DataFrame(
            columns=[
                "period",
                "report_count",
            ]
        )

    # ---------------------------------------------------------------
    # Remove duplicate report IDs.
    #
    # A single FDA report can contain multiple drug/reaction
    # combinations. For report-volume trends we count the report
    # once rather than counting every combination separately.
    # ---------------------------------------------------------------

    result = result.drop_duplicates(
        subset=["report_id"]
    )

    # ---------------------------------------------------------------
    # Create time period
    # ---------------------------------------------------------------

    try:
        result["period"] = result[
            "received_date"
        ].dt.to_period(frequency)

    except ValueError as exc:
        raise ValueError(
            f"Unsupported frequency: {frequency}"
        ) from exc

    # ---------------------------------------------------------------
    # Count reports
    # ---------------------------------------------------------------

    trend = (
        result.groupby("period")
        .agg(
            report_count=(
                "report_id",
                "nunique",
            )
        )
        .reset_index()
    )

    # Convert Period to timestamp so Plotly can directly use it.
    trend["period"] = trend["period"].dt.to_timestamp()

    trend = trend.sort_values(
        "period"
    ).reset_index(drop=True)

    return trend


# -------------------------------------------------------------------
# Monthly trend
# -------------------------------------------------------------------

def calculate_monthly_trend(
    dataframe: pd.DataFrame,
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate monthly adverse-event report volume.
    """

    return calculate_report_trend(
        dataframe=dataframe,
        frequency="M",
        drug_name=drug_name,
        reaction=reaction,
    )


# -------------------------------------------------------------------
# Weekly trend
# -------------------------------------------------------------------

def calculate_weekly_trend(
    dataframe: pd.DataFrame,
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate weekly adverse-event report volume.
    """

    return calculate_report_trend(
        dataframe=dataframe,
        frequency="W",
        drug_name=drug_name,
        reaction=reaction,
    )


# -------------------------------------------------------------------
# Daily trend
# -------------------------------------------------------------------

def calculate_daily_trend(
    dataframe: pd.DataFrame,
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate daily adverse-event report volume.
    """

    return calculate_report_trend(
        dataframe=dataframe,
        frequency="D",
        drug_name=drug_name,
        reaction=reaction,
    )


# -------------------------------------------------------------------
# Compare trends
# -------------------------------------------------------------------

def compare_drug_trends(
    dataframe: pd.DataFrame,
    drug_names: list[str],
    frequency: str = "M",
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

    for drug_name in drug_names:

        trend = calculate_report_trend(
            dataframe=dataframe,
            frequency=frequency,
            drug_name=drug_name,
        )

        if trend.empty:
            continue

        trend["drug_name"] = drug_name.strip().upper()

        all_trends.append(trend)

    if not all_trends:
        return pd.DataFrame(
            columns=[
                "period",
                "report_count",
                "drug_name",
            ]
        )

    return pd.concat(
        all_trends,
        ignore_index=True,
    )


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
        Trend statistics.
    """

    if (
        trend_dataframe is None
        or trend_dataframe.empty
    ):
        return {
            "total_reports": 0,
            "average_reports_per_period": 0.0,
            "highest_period": None,
            "highest_report_count": 0,
            "lowest_period": None,
            "lowest_report_count": 0,
        }

    trend = trend_dataframe.copy()

    highest_row = trend.loc[
        trend["report_count"].idxmax()
    ]

    lowest_row = trend.loc[
        trend["report_count"].idxmin()
    ]

    return {
        "total_reports": int(
            trend["report_count"].sum()
        ),
        "average_reports_per_period": float(
            trend["report_count"].mean()
        ),
        "highest_period": highest_row["period"],
        "highest_report_count": int(
            highest_row["report_count"]
        ),
        "lowest_period": lowest_row["period"],
        "lowest_report_count": int(
            lowest_row["report_count"]
        ),
    }


# -------------------------------------------------------------------
# Calculate percentage change
# -------------------------------------------------------------------

def add_period_change(
    trend_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add period-over-period percentage change.

    Example:
        Current month = 150
        Previous month = 100

        Change = 50%
    """

    if (
        trend_dataframe is None
        or trend_dataframe.empty
    ):
        return trend_dataframe.copy()

    result = trend_dataframe.copy()

    result["percentage_change"] = (
        result["report_count"]
        .pct_change()
        .mul(100)
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
    """

    if (
        trend_dataframe is None
        or trend_dataframe.empty
    ):
        return pd.DataFrame(
            columns=[
                "date",
                "report_count",
            ]
        )

    result = trend_dataframe.copy()

    result["date"] = pd.to_datetime(
        result["period"],
        errors="coerce",
    )

    result = result.dropna(
        subset=["date"]
    )

    result = result.sort_values(
        "date"
    ).reset_index(drop=True)

    return result[
        [
            "date",
            "report_count",
        ]
    ]


# -------------------------------------------------------------------
# Internal validation
# -------------------------------------------------------------------

def _validate_dataframe(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validate the input dataframe.
    """

    if dataframe is None:
        raise ValueError(
            "Dataframe cannot be None."
        )

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        raise TypeError(
            "dataframe must be a pandas DataFrame."
        )

    missing_columns = (
        REQUIRED_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )


# -------------------------------------------------------------------
# Example execution
# -------------------------------------------------------------------

if __name__ == "__main__":
    print(
        "trend_analysis.py loaded successfully."
    )
    print(
        "Use calculate_monthly_trend(), "
        "calculate_weekly_trend(), or "
        "calculate_daily_trend() with a "
        "processed FDA dataframe."
    )