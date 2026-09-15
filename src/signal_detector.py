"""
signal_detector.py
Detects disproportionate drug-reaction reporting signals from PRR results.
"""

from __future__ import annotations

import pandas as pd

from prr_engine import rank_signals, add_signal_classification


def detect_signals(
    prr_results: pd.DataFrame,
    min_prr: float = 2.0,
    min_reports: int = 3,
) -> pd.DataFrame:
    """
    Filter PRR results to rows that meet signal thresholds.

    Delegates to :func:`prr_engine.rank_signals` which applies
    classification and returns only Signal / Strong Signal rows,
    sorted by PRR descending with a human-readable rank column.

    Parameters
    ----------
    prr_results : pd.DataFrame
        Output of :func:`prr_engine.calculate_all_prrs`.
    min_prr : float
        Minimum PRR required for a pair to be classified as a signal.
    min_reports : int
        Minimum drug-reaction report count required.

    Returns
    -------
    pd.DataFrame
        Ranked signals DataFrame, or an empty DataFrame when no pairs
        meet the thresholds.
    """

    if prr_results is None or prr_results.empty:
        return pd.DataFrame()

    return rank_signals(
        prr_results,
        min_prr=min_prr,
        min_reports=min_reports,
    )


def prepare_dashboard_data(signals: pd.DataFrame) -> pd.DataFrame:
    """
    Add display columns for the Streamlit signals table.

    Adds:
    - ``prr_display`` — formatted PRR string (e.g. ``"3.45"`` or ``"∞"``)
    - ``signal_class`` — if not already present, via
      :func:`prr_engine.add_signal_classification`

    Parameters
    ----------
    signals : pd.DataFrame
        Ranked signals DataFrame from :func:`detect_signals`.

    Returns
    -------
    pd.DataFrame
        Copy of signals with display columns added.
    """

    if signals is None or signals.empty:
        return pd.DataFrame()

    result = signals.copy()

    if "signal_class" not in result.columns:
        result = add_signal_classification(result)

    result["prr_display"] = result["prr"].apply(_format_prr)

    return result


def get_signal_summary(signals: pd.DataFrame) -> dict[str, int | float]:
    """
    Return aggregate statistics for a signals DataFrame.

    Keys
    ----
    total_signals  : int   — total number of signal rows
    strong_signals : int   — rows where signal_class == "Strong Signal"
                             (0 when the column is absent)
    highest_prr    : float — maximum prr value (0.0 when DataFrame is empty)
    """
    if signals is None or signals.empty:
        return {
            "total_signals": 0,
            "strong_signals": 0,
            "highest_prr": 0.0,
        }

    total_signals = len(signals)

    if "signal_class" in signals.columns:
        strong_signals = int(
            (signals["signal_class"] == "Strong Signal").sum()
        )
    else:
        strong_signals = 0

    highest_prr = (
        float(signals["prr"].max()) if "prr" in signals.columns else 0.0
    )

    return {
        "total_signals": total_signals,
        "strong_signals": strong_signals,
        "highest_prr": highest_prr,
    }


def _format_prr(value: float) -> str:
    """Format a raw PRR float for display."""
    try:
        if value == float("inf"):
            return "∞"
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "N/A"
