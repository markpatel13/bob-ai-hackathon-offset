# 🚀 [Drug Safety Signal Detector]

> ⚠️ **Replace everything in `[ ]` brackets with your actual content before submission.**

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | [offset] |
| **Track** | [AI] |
| **Team Lead** | [Mark Patel] — [23dcs083@charusat.edu.in] |
| **Members** | [Mir Patel], [Samad Sama], [Keya Sonaiya] |

---

## 🎯 Problem Statement

> In 2–3 sentences: What problem does your project solve? Who experiences this problem?

[Millions of adverse drug event reports are collected in the FDA database, making it difficult for pharmacovigilance teams and analysts to identify unusual drug-reaction patterns from large volumes of data. Important safety signals can be difficult to recognize early because individual reports may contain multiple drugs and reactions and the overall reporting volume is very large.]

---

## 💡 Solution

> In 2–3 sentences: What did you build? How does it solve the problem above?

[Drug Safety Signal Detector is a Streamlit-based application that retrieves publicly available adverse-event reports from the FDA openFDA API, processes them into drug-reaction pairs, and calculates the Proportional Reporting Ratio (PRR) to identify disproportionate reporting signals. The application combines statistical analysis, ranked signal visualization, adverse-event trends, and plain-English explanations to help users explore potential safety signals while clearly distinguishing statistical association from confirmed causality.]

---

## ✨ Key Features

- **FDA Adverse-Event Search & Filtering:** [Search and filter FDA adverse-event reports by drug and reaction using the openFDA API.]
- **PRR-Based Statistical Signal Detection:** [Calculate the Proportional Reporting Ratio (PRR) for drug-reaction pairs to identify disproportionate reporting patterns.]
- **Ranked Safety Signal Dashboard:** [Rank detected signals according to signal strength and report counts, with the underlying statistical counts available for transparency.]
- **Adverse-Event Trend Visualization:** [Visualize adverse-event report volume over time using daily, weekly, or monthly trends, with optional drug and reaction filtering.]
- **Plain-English AI-Generated Summaries:** [Convert detected statistical signals and their verified numerical results into understandable explanations while avoiding unsupported causal claims.]

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | [Python] |
| **Frameworks** | [Streamlit] |
| **IBM Technologies** | [IBM Bob] |
| **Databases** | [SQlite] |
| **Other** | [Github,Pandas,NumPy,SciPy,Plotly,FDA-Open-api] |

---

## 📁 Repository Structure

```
├── src/                              # All source code
│   ├── app.py                        # Streamlit application
│   ├── fda_api.py                    # openFDA API integration
│   ├── data_processor.py             # FDA data processing
│   ├── database.py                   # SQLite caching/storage
│   ├── prr_engine.py                 # PRR calculations
│   ├── signal_detector.py            # Signal detection/ranking
│   ├── trend_analysis.py             # Trend analysis
│   ├── ai_summary.py                 # Plain-English summaries
│   └── README.md                     # Source-code documentation
│
├── docs/                             # Written documentation
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
│
├── demo/                             # Demo artifacts
│   ├── screenshots/                   # App screenshots
│   ├── demo-video-link.txt            # Link to demo video
│   └── live-demo-url.txt              # Link to live demo
│
├── presentation/                     # Presentation / slide deck
│
├── bob_sessions/                     # IBM Bob task session reports
│
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variable template
├── .gitignore                        # Git exclusions
└── submission.yaml                   # Structured submission metadata
```

---

## ⚡ How to Run

> **Copy these exact steps from your [`docs/setup-guide.md`](docs/setup-guide.md)**

```bash
# 1. Clone the repository
git clone https://github.com/[your-github-username]/bob-ai-hackathon-offset.git

# 2. Enter the project directory
cd bob-ai-hackathon-offset

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Streamlit application
streamlit run src/app.py
```

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/slides.pdf](presentation/) |

---

## ⚠️ Known Limitations

> Be honest — judges appreciate transparency over overclaiming.

-Statistical signal ≠ causality: [A high PRR does not establish that a drug caused an adverse reaction.]
-Reporting bias: [FDA spontaneous adverse-event reports can be influenced by differences in reporting behavior and awareness.]
-Incomplete information: [Individual reports may contain missing or incomplete patient, drug, or reaction information.]

---

## 🏅 What We're Most Proud Of

[Our strongest aspect is the combination of real-world FDA adverse-event data with a transparent and explainable statistical method.

Instead of presenting an opaque prediction, Drug Safety Signal Detector shows how a potential signal is identified through PRR, provides the underlying report counts, ranks the strongest drug-reaction patterns, visualizes how report volume changes over time, and translates the statistical findings into understandable plain-English explanations.

The project also deliberately separates statistical signal detection from causal claims, making the result easier to interpret responsibly.]

---
