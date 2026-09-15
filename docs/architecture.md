# Architecture

## System Architecture

The Drug Safety Signal Detector is a **single-process Python application** built on
Streamlit. There is no separate frontend build, no microservices, and no database.
All state is held in Streamlit session state for the duration of a user session.

```mermaid
graph TD
    U[User / Browser]           -->|HTTP :8501| APP

    subgraph "Python Process — Streamlit"
        APP[app.py\nStreamlit UI]

        APP -->|drug name + date range| FDA
        FDA -->|raw JSON response|      DP

        APP -->|normalised DataFrame|   PRR
        PRR -->|PRR result rows|        SD
        SD  -->|ranked signals|         AI
        SD  -->|ranked signals|         TA

        APP -->|selected signal|        AI
        AI  -->|plain-English text|     APP
        TA  -->|time-series DataFrame|  APP
    end

    subgraph "External"
        OFDA[(openFDA API\napi.fda.gov/drug/event.json)]
        LLM[(LLM API — optional\nClaude / GPT)]
    end

    FDA[fda_api.py]         -->|HTTPS GET| OFDA
    AI[ai_summary.py]       -->|HTTPS POST — optional| LLM

    DP[data_processor.py\nJSON → DataFrame]
    PRR[prr_engine.py\nPRR calculation]
    SD[signal_detector.py\nfilter + rank]
    TA[trend_analysis.py\ntime-series grouping]
```

## Components

| Component | File | Technology | Responsibility |
|---|---|---|---|
| **Streamlit UI** | `app.py` | Python 3.11 · Streamlit · Plotly | Full web dashboard: search bar, signal table, trend chart, report explorer, summary panel |
| **FDA API client** | `fda_api.py` | `requests` | Fetches adverse-event reports and reaction-count aggregates from openFDA |
| **Data processor** | `data_processor.py` | `pandas` | Flattens nested JSON into a normalised drug-reaction DataFrame; handles text normalisation, date parsing, deduplication |
| **PRR engine** | `prr_engine.py` | `pandas` | Calculates Proportional Reporting Ratio for every drug-reaction pair in the DataFrame; classifies signal strength |
| **Signal detector** | `signal_detector.py` | `pandas` | Filters PRR results by threshold (min PRR, min report count); ranks and prepares dashboard display data |
| **Trend analyser** | `trend_analysis.py` | `pandas` | Groups reports by calendar period; computes rolling averages and period-over-period change for flagged signals |
| **AI summary** | `ai_summary.py` | Pure Python · optional LLM API | Converts raw PRR stats into plain-English risk summaries; supports three verbosity styles and optional LLM enrichment |

## Data Flow

```
openFDA REST API
      │
      │  JSON: { meta: {…}, results: [ report, report, … ] }
      ▼
fda_api.py
  fetch_adverse_events()         — paged records for a drug
  fetch_reaction_counts()        — count-aggregated reaction terms
      │
      │  raw API dict
      ▼
data_processor.py
  process_fda_response()
      │  Normalises: report_id, drug_name, reaction,
      │              received_date, serious, death,
      │              patient_age, patient_sex, reporter_country
      │  Deduplicates on (report_id, drug_name, reaction)
      ▼
  pandas.DataFrame  [N rows × 9 columns]
      │
      ├──────────────────────────────────────────────┐
      ▼                                              ▼
prr_engine.py                              trend_analysis.py
  calculate_all_prrs()                       calculate_report_trend()
  add_signal_classification()                add_rolling_average()
  rank_signals()                             prepare_trend_for_chart()
      │                                              │
      ▼                                              ▼
signal_detector.py                       time-series DataFrame
  detect_signals(min_prr=2.0,            [period, count, rolling_avg,
                 min_reports=3)           period_change]
  prepare_dashboard_data()
      │
      │  ranked signals DataFrame
      ▼
ai_summary.py
  generate_summary()   — rule-based (always available)
  generate_llm_summary() — LLM enrichment (optional, requires API key)
      │
      │  plain-English risk summary string
      ▼
app.py  (Streamlit)
  ┌──────────────────────────────────────┐
  │  Tab 1: Signal Dashboard             │
  │    • ranked signal table             │
  │    • signal detail panel             │
  │    • plain-English summary           │
  │  Tab 2: Trend Analysis               │
  │    • Plotly line chart               │
  │    • period metrics                  │
  │  Tab 3: Raw Report Explorer          │
  │    • filterable record table         │
  │  Tab 4: About                        │
  └──────────────────────────────────────┘
```

### Step-by-step narrative

1. The user enters a drug name (e.g., `VIOXX`) and optional parameters in the
   Streamlit sidebar and clicks **Search**.
2. `app.py` calls `fda_api.fetch_adverse_events()`, which issues one or more
   paginated HTTPS GET requests to `https://api.fda.gov/drug/event.json` and
   returns a JSON dict.
3. `data_processor.process_fda_response()` converts the nested JSON into a flat
   DataFrame. Each row is one `(drug, reaction)` co-occurrence within one report.
4. `prr_engine.calculate_all_prrs()` iterates over every unique
   `(drug_name, reaction)` pair in the DataFrame and computes A, B, C, D counts
   plus PRR. `add_signal_classification()` assigns a strength label.
5. `signal_detector.detect_signals()` retains only pairs where
   `PRR ≥ min_prr AND report_count ≥ min_reports`, then calls
   `prepare_dashboard_data()` to add rank and display columns.
6. `trend_analysis.calculate_report_trend()` groups the same data by the chosen
   time frequency, adds a rolling average, and returns a chart-ready DataFrame.
7. `ai_summary.generate_summary()` formats the top signal into a plain-English
   sentence. If `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` is set,
   `generate_llm_summary()` sends a structured prompt to the LLM for a richer
   clinical interpretation.
8. All results are rendered in the four-tab Streamlit dashboard.

## Security Considerations

- **No credentials stored in code.** All API keys (`OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`) are read from environment variables at runtime.
  The `.env` file is in `.gitignore` and must never be committed.
- **openFDA requires no authentication** for the public endpoints used here
  (standard rate limit: 240 requests/minute per IP with no key; 1,000/minute
  with a free API key).
- **No user data is persisted.** The application holds all state in
  Streamlit session state, which is scoped to a single browser session and
  discarded when the tab is closed.
- **Input sanitisation.** Drug name and reaction inputs are stripped and
  URL-encoded before being sent to the openFDA API; they never reach a
  database or shell command.

## Scalability Notes

The current architecture is designed as a single-user research prototype.
For production use it would benefit from:

- **Caching layer** — a Redis or SQLite cache for FDA responses, reducing
  repeated API calls for popular drug queries.
- **Background job queue** — offloading the PRR calculation (potentially
  tens of thousands of pairs) to a Celery/RQ worker so the UI remains
  responsive during computation.
- **Persistent results database** — storing historical PRR snapshots so the
  system can track how a signal's strength changes over time across different
  FDA data vintages.
- **Rate-limit handling** — exponential back-off and request batching for
  high-volume scans across many drugs simultaneously.
