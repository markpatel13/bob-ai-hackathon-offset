"""
Data processing utilities for the Drug Safety Signal Detector.

This module converts the nested JSON returned by the openFDA Drug
Adverse Event API into normalized records suitable for analysis.

Responsibilities:
- Extract report-level information.
- Extract drugs and reactions from each report.
- Create drug-reaction combinations.
- Normalize text and dates.
- Handle missing or malformed fields.
- Remove duplicate drug-reaction records when appropriate.

PRR calculations are handled separately by prr_engine.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


# Columns produced by this module.
PROCESSED_COLUMNS = [
    "report_id",
    "drug_name",
    "reaction",
    "received_date",
    "serious",
    "death",
    "patient_age",
    "patient_sex",
    "reporter_country",
]


def process_fda_response(
    response: dict[str, Any],
) -> pd.DataFrame:
    """
    Convert a complete openFDA API response into a normalized DataFrame.

    Each row represents one unique drug-reaction combination
    associated with an FDA adverse-event report.

    Args:
        response:
            Complete JSON response returned by fda_api.py.

    Returns:
        A pandas DataFrame containing normalized adverse-event records.
    """

    if not isinstance(response, dict):
        raise ValueError("FDA response must be a dictionary.")

    results = response.get("results", [])

    if not isinstance(results, list):
        raise ValueError(
            "FDA response contains an invalid 'results' field."
        )

    records: list[dict[str, Any]] = []

    for report in results:
        if not isinstance(report, dict):
            continue

        report_records = _process_report(report)
        records.extend(report_records)

    if not records:
        return pd.DataFrame(columns=PROCESSED_COLUMNS)

    dataframe = pd.DataFrame(records)

    dataframe = _normalize_dataframe(dataframe)

    return dataframe


def _process_report(
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extract normalized drug-reaction records from one FDA report.
    """

    report_id = _clean_text(
        report.get("safetyreportid")
    )

    received_date = _parse_fda_date(
        report.get("receivedate")
    )

    serious = _to_binary_flag(
        report.get("serious")
    )

    death = _to_binary_flag(
        report.get("seriousnessdeath")
    )

    patient = report.get("patient", {})

    if not isinstance(patient, dict):
        patient = {}

    patient_age = _clean_text(
        patient.get("patientonsetage")
    )

    patient_sex = _normalize_sex(
        patient.get("patientsex")
    )

    primary_source = report.get(
        "primarysource",
        {},
    )

    if not isinstance(primary_source, dict):
        primary_source = {}

    reporter_country = _clean_text(
        primary_source.get("reportercountry")
    )

    drugs = _extract_drugs(patient)
    reactions = _extract_reactions(patient)

    if not drugs or not reactions:
        return []

    records: list[dict[str, Any]] = []

    # A single report may contain multiple drugs and multiple reactions.
    # Create one normalized record for every drug-reaction combination.
    for drug_name in drugs:
        for reaction in reactions:
            records.append(
                {
                    "report_id": report_id,
                    "drug_name": drug_name,
                    "reaction": reaction,
                    "received_date": received_date,
                    "serious": serious,
                    "death": death,
                    "patient_age": patient_age,
                    "patient_sex": patient_sex,
                    "reporter_country": reporter_country,
                }
            )

    return records


def _extract_drugs(
    patient: dict[str, Any],
) -> list[str]:
    """
    Extract medicinal product names from a patient object.
    """

    drugs = patient.get("drug", [])

    if not isinstance(drugs, list):
        return []

    names: list[str] = []

    for drug in drugs:
        if not isinstance(drug, dict):
            continue

        name = _clean_text(
            drug.get("medicinalproduct")
        )

        if name:
            names.append(name)

    return _unique_values(names)


def _extract_reactions(
    patient: dict[str, Any],
) -> list[str]:
    """
    Extract MedDRA reaction terms from a patient object.
    """

    reactions = patient.get("reaction", [])

    if not isinstance(reactions, list):
        return []

    names: list[str] = []

    for reaction in reactions:
        if not isinstance(reaction, dict):
            continue

        name = _clean_text(
            reaction.get("reactionmeddrapt")
        )

        if name:
            names.append(name)

    return _unique_values(names)


def _normalize_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize data types, text fields and duplicate records.
    """

    for column in PROCESSED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[PROCESSED_COLUMNS].copy()

    dataframe["drug_name"] = (
        dataframe["drug_name"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    dataframe["reaction"] = (
        dataframe["reaction"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    dataframe["report_id"] = (
        dataframe["report_id"]
        .astype("string")
        .str.strip()
    )

    dataframe["received_date"] = pd.to_datetime(
        dataframe["received_date"],
        errors="coerce",
    )

    dataframe["serious"] = (
        pd.to_numeric(
            dataframe["serious"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    dataframe["death"] = (
        pd.to_numeric(
            dataframe["death"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    # Remove rows where the essential analytical fields are missing.
    dataframe = dataframe.dropna(
        subset=[
            "report_id",
            "drug_name",
            "reaction",
        ]
    )

    dataframe = dataframe[
        (dataframe["drug_name"] != "")
        & (dataframe["reaction"] != "")
    ]

    # One report should contribute only once to a particular
    # drug-reaction combination.
    dataframe = dataframe.drop_duplicates(
        subset=[
            "report_id",
            "drug_name",
            "reaction",
        ]
    )

    return dataframe.reset_index(drop=True)


def _clean_text(value: Any) -> str | None:
    """
    Convert a value to cleaned text.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def _to_binary_flag(value: Any) -> int:
    """
    Convert FDA-style binary values into 0/1.

    FDA commonly represents boolean fields using:
        1 = Yes
        2 = No
    """

    if value is None:
        return 0

    text = str(value).strip()

    if text == "1":
        return 1

    return 0


def _normalize_sex(value: Any) -> str:
    """
    Normalize FDA patient sex codes.

    FDA coding commonly uses:
        1 = Male
        2 = Female
        0 = Unknown
    """

    if value is None:
        return "Unknown"

    text = str(value).strip()

    mapping = {
        "1": "Male",
        "2": "Female",
        "0": "Unknown",
    }

    return mapping.get(text, "Unknown")


def _parse_fda_date(
    value: Any,
) -> str | None:
    """
    Convert an FDA YYYYMMDD date into ISO YYYY-MM-DD format.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        parsed = datetime.strptime(
            text,
            "%Y%m%d",
        )

        return parsed.strftime("%Y-%m-%d")

    except ValueError:
        return None


def _unique_values(
    values: list[str],
) -> list[str]:
    """
    Return unique values while preserving their original order.
    """

    seen: set[str] = set()
    unique: list[str] = []

    for value in values:
        normalized = value.strip()

        if not normalized:
            continue

        if normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)

    return unique


def get_processing_summary(
    dataframe: pd.DataFrame,
) -> dict[str, int]:
    """
    Return basic statistics about processed FDA records.

    Returns:
        Dictionary containing record, report, drug and reaction counts.
    """

    if dataframe.empty:
        return {
            "records": 0,
            "reports": 0,
            "drugs": 0,
            "reactions": 0,
        }

    return {
        "records": len(dataframe),
        "reports": dataframe["report_id"].nunique(),
        "drugs": dataframe["drug_name"].nunique(),
        "reactions": dataframe["reaction"].nunique(),
    }