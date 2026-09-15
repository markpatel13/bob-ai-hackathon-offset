"""
Drug Safety Signal Detector
---------------------------

Streamlit application for exploring FDA adverse-event reports,
calculating PRR-based statistical safety signals, visualizing
trends, and generating plain-English signal summaries.

Application flow:

    openFDA
       ↓
    fda_api.py
       ↓
    data_processor.py
       ↓
    database.py
       ↓
    prr_engine.py
       ↓
    signal_detector.py
       ↓
    trend_analysis.py
       ↓
    ai_summary.py
       ↓
    Streamlit dashboard
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# -------------------------------------------------------------------
# Make src imports work when app.py is executed directly
# -------------------------------------------------------------------

SRC_DIR = Path(__file__).resolve().parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from fda_api import (
    FDAAPIError,
    fetch_adverse_events,
)

from data_processor import (
    process_fda_response,
)

from database import (
    initialize_database,
    save_records,
    get_cached_records,
    get_cache_stats,
)

from prr_engine import (
    calculate_all_prrs,
)

from signal_detector import (
    detect_signals,
    prepare_dashboard_data,
    get_signal_summary,
)

from trend_analysis import (
    calculate_report_trend,
)

from ai_summary import (
    generate_summary,
)


# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------

st.set_page_config(
    page_title="Drug Safety Signal Detector",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------------------------------------------------
# Application constants
# -------------------------------------------------------------------

DEFAULT_LIMIT = 100
MAX_FETCH_LIMIT = 1000

DEFAULT_MIN_PRR = 2.0
DEFAULT_MIN_REPORTS = 3


# -------------------------------------------------------------------
# Custom styling
# -------------------------------------------------------------------

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.4rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            font-size: 1.05rem;
            opacity: 0.75;
            margin-bottom: 1.5rem;
        }

        .disclaimer {
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid rgba(128, 128, 128, 0.35);
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Session state
# -------------------------------------------------------------------

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame()

if "raw_response" not in st.session_state:
    st.session_state.raw_response = None

if "prr_results" not in st.session_state:
    st.session_state.prr_results = pd.DataFrame()

if "signals" not in st.session_state:
    st.session_state.signals = pd.DataFrame()

if "search_description" not in st.session_state:
    st.session_state.search_description = ""


# -------------------------------------------------------------------
# Database initialization
# -------------------------------------------------------------------

try:
    initialize_database()
except Exception as exc:
    st.error(f"Database initialization failed: {exc}")
    st.stop()


# -------------------------------------------------------------------
# Helper: fetch FDA data
# -------------------------------------------------------------------

def load_fda_data(
    drug_name: str | None,
    reaction: str | None,
    limit: int,
) -> tuple[pd.DataFrame, dict | None, str]:
    """
    Fetch FDA adverse-event data and convert it into a normalized
    dataframe.
    """

    search_parts = []

    if drug_name:
        search_parts.append(
            f"drug={drug_name}"
        )

    if reaction:
        search_parts.append(
            f"reaction={reaction}"
        )

    search_description = (
        " | ".join(search_parts)
        if search_parts
        else "All available reports"
    )

    # ---------------------------------------------------------------
    # Build the openFDA search query
    # ---------------------------------------------------------------

    search_query_parts = []

    if drug_name:
        search_query_parts.append(
            f'patient.drug.medicinalproduct:"{drug_name}"'
        )

    if reaction:
        search_query_parts.append(
            f'patient.reaction.reactionmeddrapt:"{reaction}"'
        )

    search_query = (
        " AND ".join(search_query_parts)
        if search_query_parts
        else None
    )

    # ---------------------------------------------------------------
    # Fetch data
    # ---------------------------------------------------------------

    response = fetch_adverse_events(
        search=search_query,
        limit=limit,
    )

    # ---------------------------------------------------------------
    # Normalize
    # ---------------------------------------------------------------

    dataframe = process_fda_response(
        response
    )

    return (
        dataframe,
        response,
        search_description,
    )


# -------------------------------------------------------------------
# Helper: calculate signals
# -------------------------------------------------------------------

def calculate_signals(
    dataframe: pd.DataFrame,
    min_prr: float,
    min_reports: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate PRR values and detect statistical signals.
    """

    if dataframe.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
        )

    prr_results = calculate_all_prrs(
        dataframe,
        min_reports=1,
    )

    signals = detect_signals(
        prr_results,
        min_prr=min_prr,
        min_reports=min_reports,
    )

    return (
        prr_results,
        signals,
    )


# -------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------

def _format_prr_value(value: float) -> str:
    """
    Format a PRR value for display on the dashboard.
    """

    try:

        if value == float("inf"):
            return "∞"

        if pd.isna(value):
            return "N/A"

        return f"{float(value):.2f}"

    except (TypeError, ValueError):

        return "N/A"


# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------

with st.sidebar:

    st.header("🔎 Search FDA Reports")

    drug_input = st.text_input(
        "Drug name",
        placeholder="e.g. DURAGESIC-100",
        help=(
            "Enter a drug name to search FDA adverse-event reports."
        ),
    )

    reaction_input = st.text_input(
        "Reaction",
        placeholder="e.g. OVERDOSE",
        help=(
            "Enter an adverse reaction to narrow the search."
        ),
    )

    st.divider()

    st.subheader("Analysis Settings")

    fetch_limit = st.slider(
        "Reports to retrieve",
        min_value=10,
        max_value=MAX_FETCH_LIMIT,
        value=DEFAULT_LIMIT,
        step=10,
        help=(
            "Number of reports requested from openFDA. "
            "Larger values provide more data but may take longer."
        ),
    )

    min_prr = st.number_input(
        "Minimum PRR",
        min_value=0.1,
        max_value=100.0,
        value=DEFAULT_MIN_PRR,
        step=0.1,
        help=(
            "Minimum PRR used to classify a pair as a "
            "statistical reporting signal."
        ),
    )

    min_reports = st.number_input(
        "Minimum reports",
        min_value=1,
        max_value=100,
        value=DEFAULT_MIN_REPORTS,
        step=1,
        help=(
            "Minimum number of drug-reaction reports required "
            "for a signal."
        ),
    )

    st.divider()

    search_button = st.button(
        "🔍 Search & Analyze",
        type="primary",
        use_container_width=True,
    )

    clear_button = st.button(
        "Clear Results",
        use_container_width=True,
    )


# -------------------------------------------------------------------
# Clear results
# -------------------------------------------------------------------

if clear_button:

    st.session_state.data = pd.DataFrame()
    st.session_state.raw_response = None
    st.session_state.prr_results = pd.DataFrame()
    st.session_state.signals = pd.DataFrame()
    st.session_state.search_description = ""

    st.rerun()


# -------------------------------------------------------------------
# Search button
# -------------------------------------------------------------------

if search_button:

    if not drug_input.strip() and not reaction_input.strip():

        st.warning(
            "Please enter a drug name, a reaction, or both."
        )

    else:

        with st.spinner(
            "Fetching FDA adverse-event reports..."
        ):

            try:

                dataframe, response, description = (
                    load_fda_data(
                        drug_name=(
                            drug_input.strip()
                            if drug_input.strip()
                            else None
                        ),
                        reaction=(
                            reaction_input.strip()
                            if reaction_input.strip()
                            else None
                        ),
                        limit=fetch_limit,
                    )
                )

                st.session_state.data = dataframe
                st.session_state.raw_response = response
                st.session_state.search_description = description

                # ---------------------------------------------------
                # Cache the normalized records
                # ---------------------------------------------------

                if not dataframe.empty:
                    save_records(dataframe)

                # ---------------------------------------------------
                # Calculate PRR
                # ---------------------------------------------------

                prr_results, signals = calculate_signals(
                    dataframe,
                    min_prr=min_prr,
                    min_reports=int(min_reports),
                )

                st.session_state.prr_results = prr_results
                st.session_state.signals = signals

            except FDAAPIError as exc:

                st.error(
                    f"openFDA request failed: {exc}"
                )

            except Exception as exc:

                st.error(
                    f"An unexpected error occurred: {exc}"
                )


# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------

st.markdown(
    '<div class="main-title">💊 Drug Safety Signal Detector</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
        Explore FDA adverse-event reports and identify
        disproportionate drug-reaction reporting signals using PRR.
    </div>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Important disclaimer
# -------------------------------------------------------------------

st.markdown(
    """
    <div class="disclaimer">
        <strong>⚠️ Important:</strong>
        This application identifies statistical reporting signals
        from FDA adverse-event data. A signal does not prove that a
        drug caused a reaction and should not be used as a substitute
        for medical or regulatory assessment.
    </div>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# No results state
# -------------------------------------------------------------------

if st.session_state.data.empty:

    st.info(
        "Enter a drug name and/or reaction in the sidebar, "
        "then click **Search & Analyze**."
    )

    st.subheader("How it works")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            ### 1️⃣ Search
            Retrieve publicly available adverse-event reports
            from the FDA openFDA API.
            """
        )

    with col2:
        st.markdown(
            """
            ### 2️⃣ Analyze
            Calculate the Proportional Reporting Ratio (PRR)
            for drug-reaction pairs.
            """
        )

    with col3:
        st.markdown(
            """
            ### 3️⃣ Understand
            Explore ranked signals, trends, and
            plain-English explanations.
            """
        )

    # ---------------------------------------------------------------
    # Cache information
    # ---------------------------------------------------------------

    stats = get_cache_stats()

    if stats["total_records"] > 0:

        st.divider()

        st.caption(
            f"Local cache: {stats['total_records']:,} records | "
            f"{stats['unique_reports']:,} unique reports | "
            f"{stats['unique_drugs']:,} drugs | "
            f"{stats['unique_reactions']:,} reactions"
        )

    st.stop()


# -------------------------------------------------------------------
# Data loaded
# -------------------------------------------------------------------

dataframe = st.session_state.data
prr_results = st.session_state.prr_results
signals = st.session_state.signals


# -------------------------------------------------------------------
# Search information
# -------------------------------------------------------------------

st.success(
    f"Loaded {len(dataframe):,} normalized drug-reaction records "
    f"for: **{st.session_state.search_description}**"
)


# -------------------------------------------------------------------
# Dashboard metrics
# -------------------------------------------------------------------

summary = get_signal_summary(
    signals
)

unique_reports = (
    dataframe["report_id"].nunique()
    if "report_id" in dataframe.columns
    else 0
)

unique_drugs = (
    dataframe["drug_name"].nunique()
    if "drug_name" in dataframe.columns
    else 0
)

unique_reactions = (
    dataframe["reaction"].nunique()
    if "reaction" in dataframe.columns
    else 0
)


metric1, metric2, metric3, metric4, metric5 = st.columns(5)

with metric1:
    st.metric(
        "FDA Reports",
        f"{unique_reports:,}",
    )

with metric2:
    st.metric(
        "Drug-Reaction Pairs",
        f"{len(prr_results):,}",
    )

with metric3:
    st.metric(
        "Signals",
        f"{summary['total_signals']:,}",
    )

with metric4:
    st.metric(
        "Strong Signals",
        f"{summary['strong_signals']:,}",
    )

with metric5:
    highest_prr = summary["highest_prr"]

    if highest_prr == float("inf"):
        highest_prr_display = "∞"
    else:
        highest_prr_display = f"{highest_prr:.2f}"

    st.metric(
        "Highest PRR",
        highest_prr_display,
    )


# -------------------------------------------------------------------
# Tabs
# -------------------------------------------------------------------

tab_signals, tab_trends, tab_reports, tab_about = st.tabs(
    [
        "🚨 Safety Signals",
        "📈 Trends",
        "📋 FDA Reports",
        "ℹ️ About",
    ]
)


# ===================================================================
# TAB 1 — SAFETY SIGNALS
# ===================================================================

with tab_signals:

    st.subheader(
        "Ranked Safety Signal Dashboard"
    )

    st.caption(
        f"Signals require PRR ≥ {min_prr:.1f} "
        f"and at least {int(min_reports)} drug-reaction reports."
    )

    if signals.empty:

        st.info(
            "No statistical signals met the current thresholds."
        )

        if not prr_results.empty:

            st.write(
                "You can lower the minimum PRR or minimum "
                "report count in the sidebar and analyze again."
            )

    else:

        dashboard_data = prepare_dashboard_data(
            signals
        )

        # -----------------------------------------------------------
        # Top signals table
        # -----------------------------------------------------------

        display_columns = [
            "rank",
            "drug_name",
            "reaction",
            "prr_display",
            "A",
            "drug_total_reports",
            "signal_class",
        ]

        display_columns = [
            column
            for column in display_columns
            if column in dashboard_data.columns
        ]

        st.dataframe(
            dashboard_data[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "rank": st.column_config.NumberColumn(
                    "Rank",
                    width="small",
                ),
                "drug_name": st.column_config.TextColumn(
                    "Drug",
                ),
                "reaction": st.column_config.TextColumn(
                    "Reaction",
                ),
                "prr_display": st.column_config.TextColumn(
                    "PRR",
                ),
                "A": st.column_config.NumberColumn(
                    "Pair Reports",
                ),
                "drug_total_reports": st.column_config.NumberColumn(
                    "Drug Reports",
                ),
                "signal_class": st.column_config.TextColumn(
                    "Classification",
                ),
            },
        )

        # -----------------------------------------------------------
        # Select signal for explanation
        # -----------------------------------------------------------

        st.divider()

        st.subheader(
            "🧠 Plain-English Signal Explanation"
        )

        signal_options = list(
            range(len(signals))
        )

        selected_index = st.selectbox(
            "Select a signal",
            options=signal_options,
            format_func=lambda index: (
                f"{index + 1}. "
                f"{signals.iloc[index]['drug_name']} — "
                f"{signals.iloc[index]['reaction']}"
            ),
        )

        selected_signal = signals.iloc[
            selected_index
        ]

        summary_style = st.radio(
            "Summary detail",
            options=[
                "short",
                "standard",
                "detailed",
            ],
            index=1,
            horizontal=True,
        )

        signal_summary = generate_summary(
            selected_signal,
            style=summary_style,
        )

        st.markdown(
            signal_summary
        )

        # -----------------------------------------------------------
        # Signal numbers
        # -----------------------------------------------------------

        st.divider()

        st.subheader(
            "Statistical Details"
        )

        detail_col1, detail_col2, detail_col3, detail_col4 = (
            st.columns(4)
        )

        with detail_col1:
            st.metric(
                "PRR",
                _format_prr_value(
                    selected_signal["prr"]
                ),
            )

        with detail_col2:
            st.metric(
                "Pair Reports (A)",
                f"{int(selected_signal['A']):,}",
            )

        with detail_col3:
            st.metric(
                "Drug Reports",
                f"{int(selected_signal['drug_total_reports']):,}",
            )

        with detail_col4:
            st.metric(
                "Comparison Reports",
                f"{int(selected_signal['other_drug_total_reports']):,}",
            )


# ===================================================================
# TAB 2 — TRENDS
# ===================================================================

with tab_trends:

    st.subheader(
        "📈 Adverse-Event Report Trends"
    )

    st.caption(
        "Report volume is counted by unique FDA report ID."
    )

    # ---------------------------------------------------------------
    # Trend controls
    # ---------------------------------------------------------------

    trend_col1, trend_col2, trend_col3 = st.columns(3)

    with trend_col1:

        trend_frequency = st.selectbox(
            "Time resolution",
            options=[
                "Monthly",
                "Weekly",
                "Daily",
            ],
            index=0,
        )

    with trend_col2:

        trend_drug = st.text_input(
            "Optional drug filter",
            placeholder="e.g. DURAGESIC-100",
        )

    with trend_col3:

        trend_reaction = st.text_input(
            "Optional reaction filter",
            placeholder="e.g. OVERDOSE",
        )

    # ---------------------------------------------------------------
    # Convert frequency
    # ---------------------------------------------------------------

    frequency_map = {
        "Monthly": "ME",
        "Weekly": "W",
        "Daily": "D",
    }

    frequency = frequency_map[
        trend_frequency
    ]

    try:

        trend = calculate_report_trend(
            dataframe=dataframe,
            frequency=frequency,
            drug_name=(
                trend_drug.strip()
                if trend_drug.strip()
                else None
            ),
            reaction=(
                trend_reaction.strip()
                if trend_reaction.strip()
                else None
            ),
        )

        if trend.empty:

            st.info(
                "No trend data is available for the selected filters."
            )

        else:

            # -------------------------------------------------------
            # Plot trend
            # -------------------------------------------------------

            fig = px.line(
                trend,
                x="period",
                y="report_count",
                markers=True,
                title=(
                    "Adverse-Event Report Volume Over Time"
                ),
                labels={
                    "period": "Date",
                    "report_count": "Report Count",
                },
            )

            fig.update_layout(
                hovermode="x unified",
                xaxis_title="Date",
                yaxis_title="FDA Reports",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

            # -------------------------------------------------------
            # Trend metrics
            # -------------------------------------------------------

            trend_metric1, trend_metric2, trend_metric3 = (
                st.columns(3)
            )

            with trend_metric1:
                st.metric(
                    "Total Reports",
                    f"{int(trend['report_count'].sum()):,}",
                )

            with trend_metric2:
                st.metric(
                    "Average / Period",
                    f"{trend['report_count'].mean():.1f}",
                )

            with trend_metric3:
                st.metric(
                    "Peak Reports",
                    f"{int(trend['report_count'].max()):,}",
                )

    except Exception as exc:

        st.error(
            f"Unable to calculate trend: {exc}"
        )


# ===================================================================
# TAB 3 — FDA REPORTS
# ===================================================================

with tab_reports:

    st.subheader(
        "📋 Retrieved FDA Adverse-Event Reports"
    )

    st.caption(
        "Normalized drug-reaction records retrieved from openFDA."
    )

    # ---------------------------------------------------------------
    # Report filters
    # ---------------------------------------------------------------

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:

        table_drug = st.text_input(
            "Filter by drug",
            key="table_drug_filter",
        )

    with filter_col2:

        table_reaction = st.text_input(
            "Filter by reaction",
            key="table_reaction_filter",
        )

    filtered_data = dataframe.copy()

    if table_drug.strip():

        filtered_data = filtered_data[
            filtered_data["drug_name"]
            .astype(str)
            .str.contains(
                table_drug.strip(),
                case=False,
                na=False,
            )
        ]

    if table_reaction.strip():

        filtered_data = filtered_data[
            filtered_data["reaction"]
            .astype(str)
            .str.contains(
                table_reaction.strip(),
                case=False,
                na=False,
            )
        ]

    # ---------------------------------------------------------------
    # Display
    # ---------------------------------------------------------------

    st.write(
        f"Showing **{len(filtered_data):,}** records."
    )

    st.dataframe(
        filtered_data,
        use_container_width=True,
        hide_index=True,
    )


# ===================================================================
# TAB 4 — ABOUT
# ===================================================================

with tab_about:

    st.subheader(
        "About Drug Safety Signal Detector"
    )

    st.markdown(
        """
        ### Purpose

        Drug Safety Signal Detector helps users explore publicly
        available FDA adverse-event reports and identify
        disproportionate drug-reaction reporting patterns.

        ### Statistical method

        The application uses the **Proportional Reporting Ratio
        (PRR)**.

        A PRR compares the proportion of a particular reaction
        among reports involving a selected drug with the proportion
        of that reaction among reports involving other drugs.

        ### Technology

        - Python
        - Streamlit
        - Pandas
        - NumPy
        - SciPy
        - Plotly
        - SQLite
        - Requests
        - openFDA API
        - IBM Bob
        - GitHub

        ### Important limitation

        A statistical reporting signal is **not proof of causality**.

        FDA adverse-event reports may be affected by reporting bias,
        duplicate reports, missing information, differences in
        reporting practices, co-medications, and other factors.

        The application is intended to support pharmacovigilance
        analysis and exploration, not to replace medical or
        regulatory judgment.
        """
    )

    st.divider()

    st.subheader(
        "Data Source"
    )

    st.markdown(
        """
        The application retrieves publicly available adverse-event
        data from the FDA's openFDA API.

        Always interpret results in accordance with the limitations
        and disclaimers associated with the underlying FDA data.
        """
    )

    # ---------------------------------------------------------------
    # API metadata
    # ---------------------------------------------------------------

    raw_response = st.session_state.raw_response

    if raw_response and isinstance(raw_response, dict):

        meta = raw_response.get(
            "meta",
            {},
        )

        if meta.get("last_updated"):

            st.caption(
                f"openFDA data last updated: "
                f"{meta['last_updated']}"
            )


# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------

st.divider()

st.caption(
    "Drug Safety Signal Detector • IBM BoB AI Innovation Hackathon 2026"
)

st.caption(
    "Statistical signals are not confirmed causal relationships."
)

