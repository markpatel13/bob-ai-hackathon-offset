# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Prerequisites

Before you begin, ensure you have the following installed:

- [ ] **Python 3.11+** — `python --version` must print `3.11.x` or higher
- [ ] **pip** (comes with Python) — `pip --version`
- [ ] **Git** — `git --version`
- [ ] **(Optional) A free openFDA API key** — increases the rate limit from
      240 to 1,000 requests/minute. Register at
      [open.fda.gov/apis/authentication](https://open.fda.gov/apis/authentication/).
      The app works without one.
- [ ] **(Optional) An OpenAI or Anthropic API key** — only needed if you want
      LLM-generated plain-English summaries. The app is fully functional without one.

No Docker, no Node.js, no database(chromadb optional) required.

---

## Environment Variables

Copy `src/.env.example` to `src/.env` and fill in the values you have:

```bash
cp src/.env.example src/.env
```

| Variable | Description | Required |
|---|---|---|
| `FDA_API_KEY` | openFDA API key (higher rate limit) | No |
| `OPENAI_API_KEY` | OpenAI API key for LLM summaries | No |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API key for LLM summaries | No |

> The core signal-detection workflow — fetching FDA data, calculating PRR,
> and displaying the dashboard — requires **no API keys at all**.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/bob-ai-hackathon-offset.git
cd bob-ai-hackathon-offset

# 2. (Recommended) Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r src/requirements.txt
```

### `src/requirements.txt` (minimum)

If a `requirements.txt` is not present, install these packages manually:

```bash
pip install streamlit pandas requests plotly python-dotenv
```

---

## Running the Application

```bash
# From the repo root (with the virtual environment active)
streamlit run src/app.py
```

Streamlit will print two URLs:

```
  Local URL:  http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Open **http://localhost:8501** in your browser.

---

## Using the Application

1. **Enter a drug name** in the search bar in the left sidebar
   (e.g., `VIOXX`, `ASPIRIN`, `IBUPROFEN`).
2. Optionally adjust **date range**, **fetch limit** (10–1000 reports),
   **minimum PRR threshold** (default 2.0), and **minimum report count**
   (default 3).
3. Click **Search**.
4. The app will:
   - Fetch reports from openFDA (takes 2–10 seconds depending on limit)
   - Calculate PRR for every drug-reaction pair
   - Display the ranked signal table in **Tab 1 — Signals**
5. Select any row in the signal table to see the **plain-English risk summary**
   and **trend chart** for that signal.
6. Switch to **Tab 2 — Trend Analysis** to explore the report volume over time.
7. Switch to **Tab 3 — Raw Reports** to browse individual adverse-event records.

---

## Running Tests

```bash
# From the repo root (with the virtual environment active)
pytest src/ -v
```

If pytest is not installed:

```bash
pip install pytest
pytest src/ -v
```

---

## Quick Demo

To reproduce the Vioxx heart-attack signal that is central to this project's
motivating story:

1. Start the app (`streamlit run src/app.py`).
2. Enter drug name: **`VIOXX`**
3. Set fetch limit to **500** and date range **20000101 – 20041001**.
4. Click **Search**.
5. Look for **MYOCARDIAL INFARCTION** in the signal table — it should appear
   with a high PRR and a **Strong** classification.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'streamlit'` | Run `pip install streamlit pandas requests plotly python-dotenv` |
| `ModuleNotFoundError: No module named 'src'` | Run `streamlit run src/app.py` from the repo **root**, not from inside `src/` |
| openFDA returns `{"error": "Not Found"}` | The drug name returned zero results. Try a different spelling (e.g., `ROFECOXIB` instead of `VIOXX`) or expand the date range. |
| openFDA returns HTTP 429 Too Many Requests | You have exceeded the rate limit. Add your `FDA_API_KEY` to `.env`, or wait 60 seconds and try again with a smaller fetch limit. |
| `ValueError: No results in FDA response` | No reports found for that drug / date combination. Try removing the date filter. |
| Dashboard shows "No signals detected" | Lower the **Min PRR** threshold (try 1.5) or **Min Reports** threshold (try 1), or fetch more records by raising the limit. |
| LLM summary not appearing | The LLM feature requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`. The rule-based summary always works without a key — select "Standard" or "Detailed" style in the Summary Style radio button. |
| Streamlit port 8501 already in use | Run `streamlit run src/app.py --server.port 8502` |

---

## Verifying It Is Working

After starting the app and searching for **ASPIRIN** with default settings
you should see:

- At least one row in the **Signals** table with a non-zero PRR value
- A trend chart in **Tab 2** showing at least a few data points
- Raw report rows in **Tab 3**
- A plain-English summary sentence at the bottom of the Signals tab

If all four are present, the installation is successful.
