"""
SQLite database layer for the Drug Safety Signal Detector.

The database is used primarily as a local cache for normalized FDA
adverse-event records retrieved by the application.

Database file:
    src/drug_safety.db
"""

from pathlib import Path
import sqlite3
from typing import Optional

import pandas as pd


# -------------------------------------------------------------------
# Database configuration
# -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "drug_safety.db"


# -------------------------------------------------------------------
# Connection
# -------------------------------------------------------------------

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create and return a SQLite database connection.

    Parameters
    ----------
    db_path : str, optional
        Custom database path. If not provided, the database is created
        at src/drug_safety.db.

    Returns
    -------
    sqlite3.Connection
        SQLite connection object.
    """

    path = Path(db_path) if db_path else DEFAULT_DB_PATH

    # Make sure the parent directory exists.
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path))

    # Return rows that can also be accessed by column name.
    connection.row_factory = sqlite3.Row

    # Enable foreign-key support.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# -------------------------------------------------------------------
# Database initialization
# -------------------------------------------------------------------

def initialize_database(db_path: Optional[str] = None) -> None:
    """
    Create the required database tables and indexes if they do not exist.
    """

    connection = get_connection(db_path)

    try:
        cursor = connection.cursor()

        # -----------------------------------------------------------
        # Main adverse-event records table
        # -----------------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS adverse_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                report_id TEXT NOT NULL,
                drug_name TEXT NOT NULL,
                reaction TEXT NOT NULL,

                received_date TEXT,

                serious INTEGER DEFAULT 0,
                death INTEGER DEFAULT 0,

                patient_age TEXT,
                patient_sex TEXT,
                reporter_country TEXT,

                UNIQUE(report_id, drug_name, reaction)
            )
            """
        )

        # -----------------------------------------------------------
        # Metadata table
        # -----------------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                cache_key TEXT UNIQUE NOT NULL,
                api_last_updated TEXT,
                disclaimer TEXT,
                terms TEXT,
                license TEXT,

                cached_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # -----------------------------------------------------------
        # Indexes
        # -----------------------------------------------------------
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_adverse_events_drug
            ON adverse_events(drug_name)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_adverse_events_reaction
            ON adverse_events(reaction)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_adverse_events_date
            ON adverse_events(received_date)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_adverse_events_drug_reaction
            ON adverse_events(drug_name, reaction)
            """
        )

        connection.commit()

    finally:
        connection.close()


# -------------------------------------------------------------------
# Save processed FDA records
# -------------------------------------------------------------------

def save_records(
    dataframe: pd.DataFrame,
    db_path: Optional[str] = None
) -> int:
    """
    Save normalized FDA adverse-event records into SQLite.

    Duplicate report/drug/reaction combinations are ignored.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Normalized dataframe produced by data_processor.py.

    db_path : str, optional
        Custom database path.

    Returns
    -------
    int
        Number of records successfully inserted.
    """

    if dataframe is None or dataframe.empty:
        return 0

    initialize_database(db_path)

    required_columns = [
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

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required dataframe columns: "
            + ", ".join(missing_columns)
        )

    connection = get_connection(db_path)

    try:
        records = []

        for _, row in dataframe.iterrows():
            records.append(
                (
                    _safe_value(row["report_id"]),
                    _safe_value(row["drug_name"]),
                    _safe_value(row["reaction"]),
                    _safe_value(row["received_date"]),
                    _to_integer_flag(row["serious"]),
                    _to_integer_flag(row["death"]),
                    _safe_value(row["patient_age"]),
                    _safe_value(row["patient_sex"]),
                    _safe_value(row["reporter_country"]),
                )
            )

        cursor = connection.cursor()

        cursor.executemany(
            """
            INSERT OR IGNORE INTO adverse_events (
                report_id,
                drug_name,
                reaction,
                received_date,
                serious,
                death,
                patient_age,
                patient_sex,
                reporter_country
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

        inserted_count = cursor.rowcount

        connection.commit()

        return inserted_count

    finally:
        connection.close()


# -------------------------------------------------------------------
# Retrieve cached records
# -------------------------------------------------------------------

def get_cached_records(
    drug_name: Optional[str] = None,
    reaction: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Retrieve cached adverse-event records using optional filters.

    Parameters
    ----------
    drug_name : str, optional
        Filter by drug name.

    reaction : str, optional
        Filter by reaction.

    start_date : str, optional
        Minimum received date in YYYY-MM-DD format.

    end_date : str, optional
        Maximum received date in YYYY-MM-DD format.

    db_path : str, optional
        Custom database path.

    Returns
    -------
    pandas.DataFrame
        Matching cached records.
    """

    initialize_database(db_path)

    connection = get_connection(db_path)

    try:
        query = """
            SELECT
                report_id,
                drug_name,
                reaction,
                received_date,
                serious,
                death,
                patient_age,
                patient_sex,
                reporter_country
            FROM adverse_events
            WHERE 1 = 1
        """

        parameters = []

        # -----------------------------------------------------------
        # Drug filter
        # -----------------------------------------------------------
        if drug_name:
            query += " AND drug_name = ?"
            parameters.append(drug_name.strip().upper())

        # -----------------------------------------------------------
        # Reaction filter
        # -----------------------------------------------------------
        if reaction:
            query += " AND reaction = ?"
            parameters.append(reaction.strip().upper())

        # -----------------------------------------------------------
        # Date filters
        # -----------------------------------------------------------
        if start_date:
            query += " AND received_date >= ?"
            parameters.append(start_date)

        if end_date:
            query += " AND received_date <= ?"
            parameters.append(end_date)

        query += " ORDER BY received_date DESC"

        return pd.read_sql_query(
            query,
            connection,
            params=parameters,
        )

    finally:
        connection.close()


# -------------------------------------------------------------------
# Get database statistics
# -------------------------------------------------------------------

def get_cache_stats(
    db_path: Optional[str] = None
) -> dict:
    """
    Return basic statistics about the local FDA data cache.

    Returns
    -------
    dict
        Database statistics.
    """

    initialize_database(db_path)

    connection = get_connection(db_path)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS total_records
            FROM adverse_events
            """
        )

        total_records = cursor.fetchone()["total_records"]

        cursor.execute(
            """
            SELECT COUNT(DISTINCT report_id) AS unique_reports
            FROM adverse_events
            """
        )

        unique_reports = cursor.fetchone()["unique_reports"]

        cursor.execute(
            """
            SELECT COUNT(DISTINCT drug_name) AS unique_drugs
            FROM adverse_events
            """
        )

        unique_drugs = cursor.fetchone()["unique_drugs"]

        cursor.execute(
            """
            SELECT COUNT(DISTINCT reaction) AS unique_reactions
            FROM adverse_events
            """
        )

        unique_reactions = cursor.fetchone()["unique_reactions"]

        return {
            "total_records": total_records,
            "unique_reports": unique_reports,
            "unique_drugs": unique_drugs,
            "unique_reactions": unique_reactions,
        }

    finally:
        connection.close()


# -------------------------------------------------------------------
# Save API metadata
# -------------------------------------------------------------------

def save_api_metadata(
    response: dict,
    cache_key: str,
    db_path: Optional[str] = None,
) -> None:
    """
    Save useful openFDA metadata associated with a cached response.

    Parameters
    ----------
    response : dict
        Raw response returned by fda_api.py.

    cache_key : str
        Identifier for the query/cache entry.

    db_path : str, optional
        Custom database path.
    """

    if not isinstance(response, dict):
        return

    initialize_database(db_path)

    metadata = response.get("meta", {})

    connection = get_connection(db_path)

    try:
        connection.execute(
            """
            INSERT INTO cache_metadata (
                cache_key,
                api_last_updated,
                disclaimer,
                terms,
                license
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(cache_key)
            DO UPDATE SET
                api_last_updated = excluded.api_last_updated,
                disclaimer = excluded.disclaimer,
                terms = excluded.terms,
                license = excluded.license,
                cached_at = CURRENT_TIMESTAMP
            """,
            (
                cache_key,
                metadata.get("last_updated"),
                metadata.get("disclaimer"),
                metadata.get("terms"),
                metadata.get("license"),
            ),
        )

        connection.commit()

    finally:
        connection.close()


# -------------------------------------------------------------------
# Retrieve API metadata
# -------------------------------------------------------------------

def get_api_metadata(
    cache_key: str,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """
    Retrieve metadata for a cached API query.

    Returns
    -------
    dict or None
        Metadata dictionary if found.
    """

    initialize_database(db_path)

    connection = get_connection(db_path)

    try:
        cursor = connection.execute(
            """
            SELECT
                cache_key,
                api_last_updated,
                disclaimer,
                terms,
                license,
                cached_at
            FROM cache_metadata
            WHERE cache_key = ?
            """,
            (cache_key,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


# -------------------------------------------------------------------
# Clear cached records
# -------------------------------------------------------------------

def clear_cache(db_path: Optional[str] = None) -> None:
    """
    Delete all cached adverse-event records and metadata.
    """

    initialize_database(db_path)

    connection = get_connection(db_path)

    try:
        connection.execute("DELETE FROM adverse_events")
        connection.execute("DELETE FROM cache_metadata")

        connection.commit()

    finally:
        connection.close()


# -------------------------------------------------------------------
# Internal helper functions
# -------------------------------------------------------------------

def _safe_value(value):
    """
    Convert pandas/NumPy missing values into SQLite-compatible None.
    """

    if pd.isna(value):
        return None

    return value


def _to_integer_flag(value) -> int:
    """
    Convert a boolean-like value into SQLite integer 0/1.
    """

    if pd.isna(value):
        return 0

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {"true", "yes", "1"}:
            return 1

        if normalized in {"false", "no", "0", ""}:
            return 0

    try:
        return int(bool(value))

    except (TypeError, ValueError):
        return 0


# -------------------------------------------------------------------
# Automatic initialization
# -------------------------------------------------------------------

if __name__ == "__main__":
    initialize_database()

    stats = get_cache_stats()

    print("Database initialized successfully.")
    print(f"Database location: {DEFAULT_DB_PATH}")
    print(f"Cached records: {stats['total_records']}")
    print(f"Unique reports: {stats['unique_reports']}")
    print(f"Unique drugs: {stats['unique_drugs']}")
    print(f"Unique reactions: {stats['unique_reactions']}")