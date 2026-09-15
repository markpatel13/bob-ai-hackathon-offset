"""
signal_detector.py
Detects disproportionate drug-reaction reporting signals from PRR results.
"""

from __future__ import annotations

import pandas as pd


def detect_signals(
    prr_results: pd.DataFrame,
    min_prr: float = 2.0,
    min_reports: int = 3,
) -> pd.DataFrame:
    """Filter PRR results to rows that meet signal thresholds."""
    raise NotImplementedError


def prepare_dashboard_data(signals: pd.DataFrame) -> pd.DataFrame:
    """Add rank, prr_display, and signal_class columns for display."""
    raise NotImplementedError


def get_signal_summary(signals: pd.DataFrame) -> dict[str, int | float]:
    """
    Return aggregate statistics for a signals DataFrame.

    Keys
    ----
    total_signals  : int   — total number of signal rows
    strong_signals : int   — rows where signal_class == "Strong"
                             (0 when the column is absent)
    highest_prr    : float — maximum prr value (0.0 when DataFrame is empty)
    """
    if signals.empty:
        return {
            "total_signals": 0,
            "strong_signals": 0,
            "highest_prr": 0.0,
        }

    total_signals = len(signals)

    if "signal_class" in signals.columns:
        strong_signals = int((signals["signal_class"] == "Strong").sum())
    else:
        strong_signals = 0

    highest_prr = float(signals["prr"].max()) if "prr" in signals.columns else 0.0

    return {
        "total_signals": total_signals,
        "strong_signals": strong_signals,
        "highest_prr": highest_prr,
    }
