"""
fda_api.py
Fetches adverse event reports from the openFDA Drug Event API.
Endpoint: https://api.fda.gov/drug/event.json
"""

from __future__ import annotations

import requests
from typing import Any

FDA_BASE_URL = "https://api.fda.gov/drug/event.json"
DEFAULT_LIMIT = 100


def fetch_adverse_events(
    drug_name: str,
    limit: int = DEFAULT_LIMIT,
    skip: int = 0,
    date_start: str | None = None,
    date_end: str | None = None,
) -> dict[str, Any]:
    """
    Fetch adverse event reports for a given drug from openFDA.

    Args:
        drug_name:   Brand or generic drug name to search for.
        limit:       Number of records to return (max 1000 per request).
        skip:        Offset for pagination.
        date_start:  Start date filter in YYYYMMDD format (e.g. '20200101').
        date_end:    End date filter in YYYYMMDD format (e.g. '20231231').

    Returns:
        Parsed JSON response dict with keys 'meta' and 'results'.

    Raises:
        requests.HTTPError: on non-2xx responses.
        ValueError:         if the API returns no results field.
    """
    # Build the search query
    search_parts = [f'patient.drug.medicinalproduct:"{drug_name}"']

    if date_start and date_end:
        search_parts.append(
            f"receivedate:[{date_start}+TO+{date_end}]"
        )
    elif date_start:
        search_parts.append(f"receivedate:[{date_start}+TO+99991231]")
    elif date_end:
        search_parts.append(f"receivedate:[19000101+TO+{date_end}]")

    search_query = "+AND+".join(search_parts)

    params = {
        "search": search_query,
        "limit": limit,
        "skip": skip,
    }

    response = requests.get(FDA_BASE_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    if "results" not in data:
        raise ValueError(
            f"No results in FDA response for drug '{drug_name}'. "
            f"Meta: {data.get('meta', {})}"
        )

    return data


def fetch_reaction_counts(drug_name: str, limit: int = 1000) -> dict[str, int]:
    """
    Use the openFDA count endpoint to get reaction term frequencies for a drug.
    Returns a dict mapping reaction term -> count.

    Args:
        drug_name: Drug name to query.
        limit:     Max number of reaction terms to return.

    Returns:
        Dict of {reaction_term: count}
    """
    params = {
        "search": f'patient.drug.medicinalproduct:"{drug_name}"',
        "count": "patient.reaction.reactionmeddrapt.exact",
        "limit": limit,
    }

    response = requests.get(FDA_BASE_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    if "results" not in data:
        return {}

    return {item["term"]: item["count"] for item in data["results"]}


def fetch_total_report_count() -> int:
    """
    Fetch total number of adverse event reports in the FDA database.
    Used as the denominator in PRR calculations.

    Returns:
        Total report count as an integer.
    """
    params = {"limit": 1}
    response = requests.get(FDA_BASE_URL, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()
    return data["meta"]["results"]["total"]


# ── quick smoke-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_drug = "aspirin"
    print(f"Testing openFDA API with drug: '{test_drug}'\n")

    # 1. Total DB size
    total = fetch_total_report_count()
    print(f"Total adverse event reports in FDA database : {total:,}")

    # 2. Reaction counts
    print(f"\nTop 10 reactions for '{test_drug}':")
    reactions = fetch_reaction_counts(test_drug, limit=10)
    for term, count in reactions.items():
        print(f"  {term:<40} {count:>8,}")

    # 3. Raw event records (first 3)
    print(f"\nFetching first 3 raw event records for '{test_drug}'...")
    raw = fetch_adverse_events(test_drug, limit=3)
    print(f"  Records returned : {len(raw['results'])}")
    print(f"  Total matching   : {raw['meta']['results']['total']:,}")
    first = raw["results"][0]
    print(f"  Sample report ID : {first.get('safetyreportid', 'N/A')}")
    print(f"  Receive date     : {first.get('receivedate', 'N/A')}")
    drugs_in_report = [
        d.get("medicinalproduct", "?")
        for d in first.get("patient", {}).get("drug", [])
    ]
    print(f"  Drugs in report  : {drugs_in_report}")
    reactions_in_report = [
        r.get("reactionmeddrapt", "?")
        for r in first.get("patient", {}).get("reaction", [])
    ]
    print(f"  Reactions        : {reactions_in_report}")

    print("\n[OK] FDA API is reachable and returning data.")
