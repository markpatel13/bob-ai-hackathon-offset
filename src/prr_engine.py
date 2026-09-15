"""
PRR-based statistical signal detection.

PRR (Proportional Reporting Ratio) compares the proportion of a
specific reaction among reports for a drug with the proportion of
that reaction among reports for all other drugs.

Important:
    PRR identifies a statistical reporting signal.
    It does NOT establish that a drug caused a reaction.
"""

import pandas as pd


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "report_id",
    "drug_name",
    "reaction",
}


# -------------------------------------------------------------------
# Single drug-reaction PRR
# -------------------------------------------------------------------

def calculate_prr(
    dataframe: pd.DataFrame,
    drug_name: str,
    reaction: str,
) -> dict:
    """
    Calculate PRR for one drug-reaction pair.

    PRR formula:

        A = reports containing the drug AND reaction
        B = reports containing the drug AND other reactions
        C = reports containing other drugs AND reaction
        D = reports containing other drugs AND other reactions

        PRR = [A / (A + B)] / [C / (C + D)]

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Normalized adverse-event dataframe.

    drug_name : str
        Drug to analyze.

    reaction : str
        Reaction to analyze.

    Returns
    -------
    dict
        PRR result and supporting counts.
    """

    _validate_dataframe(dataframe)

    drug_name = _normalize_text(drug_name)
    reaction = _normalize_text(reaction)

    if not drug_name:
        raise ValueError("drug_name cannot be empty.")

    if not reaction:
        raise ValueError("reaction cannot be empty.")

    # ---------------------------------------------------------------
    # Create unique report-level drug/reaction observations.
    #
    # This prevents the same report-drug-reaction combination from
    # being counted multiple times.
    # ---------------------------------------------------------------

    records = dataframe[
        ["report_id", "drug_name", "reaction"]
    ].drop_duplicates()

    # ---------------------------------------------------------------
    # Reports containing the selected drug
    # ---------------------------------------------------------------

    drug_reports = set(
        records.loc[
            records["drug_name"] == drug_name,
            "report_id",
        ]
    )

    # ---------------------------------------------------------------
    # Reports containing the selected reaction
    # ---------------------------------------------------------------

    reaction_reports = set(
        records.loc[
            records["reaction"] == reaction,
            "report_id",
        ]
    )

    # ---------------------------------------------------------------
    # A:
    # Drug + selected reaction
    # ---------------------------------------------------------------

    a_reports = drug_reports.intersection(reaction_reports)

    A = len(a_reports)

    # ---------------------------------------------------------------
    # B:
    # Drug + other reactions
    #
    # Reports containing the selected drug but NOT the selected
    # reaction.
    # ---------------------------------------------------------------

    B = len(drug_reports - reaction_reports)

    # ---------------------------------------------------------------
    # C:
    # Other drugs + selected reaction
    #
    # A report may contain multiple drugs, so we determine whether
    # the report contains at least one drug other than the selected
    # drug.
    # ---------------------------------------------------------------

    reaction_other_drug_reports = set(
        records.loc[
            (records["reaction"] == reaction)
            & (records["drug_name"] != drug_name),
            "report_id",
        ]
    )

    C = len(reaction_other_drug_reports)

    # ---------------------------------------------------------------
    # D:
    # Other drugs + other reactions
    #
    # Universe is all reports represented in the dataset.
    # ---------------------------------------------------------------

    other_drug_reports = set(
        records.loc[
            records["drug_name"] != drug_name,
            "report_id",
        ]
    )

    D = len(other_drug_reports - reaction_reports)

    # ---------------------------------------------------------------
    # Calculate proportions
    # ---------------------------------------------------------------

    drug_total = A + B
    other_drug_total = C + D

    drug_reaction_rate = (
        A / drug_total
        if drug_total > 0
        else 0.0
    )

    other_drug_reaction_rate = (
        C / other_drug_total
        if other_drug_total > 0
        else 0.0
    )

    # ---------------------------------------------------------------
    # Calculate PRR
    # ---------------------------------------------------------------

    if other_drug_reaction_rate == 0:
        prr = float("inf") if drug_reaction_rate > 0 else 0.0
    else:
        prr = drug_reaction_rate / other_drug_reaction_rate

    return {
        "drug_name": drug_name,
        "reaction": reaction,
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "drug_total_reports": drug_total,
        "other_drug_total_reports": other_drug_total,
        "drug_reaction_rate": drug_reaction_rate,
        "other_drug_reaction_rate": other_drug_reaction_rate,
        "prr": prr,
    }


# -------------------------------------------------------------------
# Calculate PRR for all drug-reaction pairs
# -------------------------------------------------------------------

def calculate_all_prrs(
    dataframe: pd.DataFrame,
    min_reports: int = 1,
) -> pd.DataFrame:
    """
    Calculate PRR for every drug-reaction pair in the dataframe.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Normalized FDA adverse-event dataframe.

    min_reports : int
        Minimum number of drug-reaction reports required for a pair
        to be included.

    Returns
    -------
    pandas.DataFrame
        Dataframe containing PRR results for all eligible pairs.
    """

    _validate_dataframe(dataframe)

    if min_reports < 1:
        raise ValueError("min_reports must be at least 1.")

    records = dataframe[
        ["report_id", "drug_name", "reaction"]
    ].drop_duplicates()

    # Pre-build lookup indexes so each per-pair calculation is O(1)
    # set operations rather than repeated DataFrame scans.
    drug_index: dict = (
        records.groupby("drug_name")["report_id"]
        .apply(set)
        .to_dict()
    )
    reaction_index: dict = (
        records.groupby("reaction")["report_id"]
        .apply(set)
        .to_dict()
    )

    # Count reports for every drug-reaction pair.
    pair_counts = (
        records.groupby(
            ["drug_name", "reaction"]
        )["report_id"]
        .nunique()
        .reset_index(name="pair_reports")
    )

    pair_counts = pair_counts[
        pair_counts["pair_reports"] >= min_reports
    ]

    results = []

    for _, pair in pair_counts.iterrows():

        result = _calculate_prr_from_index(
            drug_index,
            reaction_index,
            pair["drug_name"],
            pair["reaction"],
        )

        results.append(result)

    if not results:
        return pd.DataFrame(
            columns=[
                "drug_name",
                "reaction",
                "A",
                "B",
                "C",
                "D",
                "drug_total_reports",
                "other_drug_total_reports",
                "drug_reaction_rate",
                "other_drug_reaction_rate",
                "prr",
            ]
        )

    result_df = pd.DataFrame(results)

    # Strongest signals first.
    result_df = result_df.sort_values(
        by="prr",
        ascending=False,
        na_position="last",
    ).reset_index(drop=True)

    return result_df


# -------------------------------------------------------------------
# Signal classification
# -------------------------------------------------------------------

def classify_signal(
    prr: float,
    report_count: int,
    min_prr: float = 2.0,
    min_reports: int = 3,
) -> str:
    """
    Classify the strength of a statistical reporting signal.

    These thresholds are configurable application thresholds.
    They should not be interpreted as regulatory causality criteria.

    Returns
    -------
    str
        Signal classification.
    """

    if report_count < min_reports:
        return "Insufficient Reports"

    if prr == float("inf"):
        return "Strong Signal"

    if prr >= min_prr:
        return "Signal"

    return "No Signal"


def add_signal_classification(
    prr_dataframe: pd.DataFrame,
    min_prr: float = 2.0,
    min_reports: int = 3,
) -> pd.DataFrame:
    """
    Add a signal classification column to PRR results.
    """

    if prr_dataframe is None or prr_dataframe.empty:
        return pd.DataFrame()

    result = prr_dataframe.copy()

    a = result["A"]
    prr_col = result["prr"]

    insufficient = a < min_reports
    strong = (~insufficient) & (prr_col == float("inf"))
    signal = (~insufficient) & (~strong) & (prr_col >= min_prr)

    result["signal_class"] = "No Signal"
    result.loc[signal, "signal_class"] = "Signal"
    result.loc[strong, "signal_class"] = "Strong Signal"
    result.loc[insufficient, "signal_class"] = "Insufficient Reports"

    return result


# -------------------------------------------------------------------
# Ranking
# -------------------------------------------------------------------

def rank_signals(
    prr_dataframe: pd.DataFrame,
    min_prr: float = 2.0,
    min_reports: int = 3,
) -> pd.DataFrame:
    """
    Filter and rank statistical safety signals.

    Signals are ranked primarily by PRR and secondarily by the
    number of drug-reaction reports.

    Returns
    -------
    pandas.DataFrame
        Ranked signal dataframe.
    """

    if prr_dataframe is None or prr_dataframe.empty:
        return pd.DataFrame()

    result = add_signal_classification(
        prr_dataframe,
        min_prr=min_prr,
        min_reports=min_reports,
    )

    # Keep only pairs meeting the configured signal criteria.
    signals = result[
        (
            result["signal_class"].isin(
                ["Signal", "Strong Signal"]
            )
        )
    ].copy()

    signals = signals.sort_values(
        by=["prr", "A"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    # Human-friendly rank.
    signals.insert(
        0,
        "rank",
        range(1, len(signals) + 1),
    )

    return signals


# -------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------

def get_top_signals(
    prr_dataframe: pd.DataFrame,
    top_n: int = 10,
    min_prr: float = 2.0,
    min_reports: int = 3,
) -> pd.DataFrame:
    """
    Return the top N ranked statistical signals.
    """

    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    ranked = rank_signals(
        prr_dataframe,
        min_prr=min_prr,
        min_reports=min_reports,
    )

    return ranked.head(top_n).copy()


def _calculate_prr_from_index(
    drug_index: dict,
    reaction_index: dict,
    drug_name: str,
    reaction: str,
) -> dict:
    """
    Calculate PRR using pre-built report-set indexes.

    Avoids repeated DataFrame scans when computing PRR for many pairs.

    Parameters
    ----------
    drug_index : dict
        Mapping of drug_name -> set of report_ids.

    reaction_index : dict
        Mapping of reaction -> set of report_ids.

    drug_name : str
        Already-normalized drug name.

    reaction : str
        Already-normalized reaction name.
    """

    drug_reports = drug_index.get(drug_name, set())
    reaction_reports = reaction_index.get(reaction, set())

    a_reports = drug_reports & reaction_reports
    A = len(a_reports)
    B = len(drug_reports - reaction_reports)

    # All reports for the given reaction that come from *other* drugs.
    # A report may list multiple drugs; we count it if any other drug
    # is present, mirroring the original logic.
    other_drug_reaction_reports: set = set()
    for d, d_reports in drug_index.items():
        if d != drug_name:
            other_drug_reaction_reports |= d_reports & reaction_reports

    C = len(other_drug_reaction_reports)

    # D: other drugs + other reactions.
    all_other_drug_reports: set = set()
    for d, d_reports in drug_index.items():
        if d != drug_name:
            all_other_drug_reports |= d_reports

    D = len(all_other_drug_reports - reaction_reports)

    drug_total = A + B
    other_drug_total = C + D

    drug_reaction_rate = A / drug_total if drug_total > 0 else 0.0
    other_drug_reaction_rate = C / other_drug_total if other_drug_total > 0 else 0.0

    if other_drug_reaction_rate == 0:
        prr = float("inf") if drug_reaction_rate > 0 else 0.0
    else:
        prr = drug_reaction_rate / other_drug_reaction_rate

    return {
        "drug_name": drug_name,
        "reaction": reaction,
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "drug_total_reports": drug_total,
        "other_drug_total_reports": other_drug_total,
        "drug_reaction_rate": drug_reaction_rate,
        "other_drug_reaction_rate": other_drug_reaction_rate,
        "prr": prr,
    }


def _validate_dataframe(dataframe: pd.DataFrame) -> None:
    """
    Validate that the dataframe contains the required columns.
    """

    if dataframe is None:
        raise ValueError("Dataframe cannot be None.")

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")

    missing = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    if dataframe.empty:
        raise ValueError("Dataframe is empty.")


def _normalize_text(value: str) -> str:
    """
    Normalize drug/reaction names for matching.
    """

    if value is None:
        return ""

    return str(value).strip().upper()