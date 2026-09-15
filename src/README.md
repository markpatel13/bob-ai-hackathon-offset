# Source Code

Place all the project's source code in this folder.

## Structure Guidelines

This project is a data/AI-focused Streamlit application. The source
code is organized into modules based on data ingestion, processing,
statistical analysis, safety signal detection, trend analysis,
AI-assisted summarization, database caching, and the user interface.

### Data / AI Project

```text
src/

    app.py              ← Streamlit application and dashboard UI

    fda_api.py          ← openFDA API integration and data retrieval

    data_processor.py   ← FDA report normalization and preprocessing

    database.py         ← SQLite database and local data caching

    prr_engine.py       ← Proportional Reporting Ratio (PRR) calculations

    signal_detector.py  ← Safety signal detection, filtering, and ranking

    trend_analysis.py   ← Adverse-event trend and time-series analysis

    ai_summary.py       ← Plain-English summaries of detected safety signals

    README.md           ← Source code documentation

```
### Web Application
```
openFDA API
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
app.py
     ↓
Streamlit Dashboard

```

### Project Architecture Diagram:

                         ┌──────────────────┐
                         │   openFDA API    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   fda_api.py     │
                         │ Data Retrieval   │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ data_processor.py│
                         │ Normalization    │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   database.py    │
                         │ SQLite Cache     │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   prr_engine.py  │
                         │ PRR Calculation  │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │signal_detector.py│
                         │ Signal Detection │
                         └───────┬───┬──────┘
                                 │   │
                    ┌────────────┘   └─────────────┐
                    ▼                              ▼
          ┌──────────────────┐           ┌──────────────────┐
          │trend_analysis.py │           │  ai_summary.py   │
          │ Trend Analysis   │           │ Plain-English    │
          └────────┬─────────┘           │ Summaries        │
                   │                     └────────┬─────────┘
                   │                              │
                   └──────────────┬───────────────┘
                                  ▼
                         ┌──────────────────┐
                         │     app.py       │
                         │ Streamlit UI     │
                         └──────────────────┘
