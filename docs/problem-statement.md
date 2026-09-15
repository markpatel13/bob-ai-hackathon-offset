# Problem Statement

## Background

Every time a patient takes a prescription drug and experiences an unexpected side
effect, that incident can be submitted to the FDA as an **adverse event report**.
The FDA's MedWatch programme has accumulated over **20 million such reports**
in its public database (FAERS — the FDA Adverse Event Reporting System), going back
decades. These reports are freely available through the **openFDA API** and represent
one of the most complete pharmacovigilance datasets in existence.

Drug regulators, pharmaceutical companies, and academic researchers call the process
of finding hidden danger patterns in this data **signal detection** — and it is the
front line of post-market drug safety monitoring.

## The Problem

Dangerous drug-reaction patterns can lie dormant in the FAERS database for years
before anyone notices them. The most infamous example is **Vioxx (rofecoxib)**: the
drug remained on the market for five years after early adverse-event data already
showed a statistically elevated rate of heart attacks (myocardial infarction). By the
time Merck voluntarily withdrew it in 2004, an estimated **27,000 patients** had
suffered fatal or near-fatal cardiovascular events that may have been preventable.

The underlying signal was buried in thousands of individual reports spread across
many drugs and many reactions. Without a systematic, quantitative way to scan for
disproportionate patterns, investigators had no practical tool to surface it quickly.

Today, the raw data is public and free — but it is still a firehose of semi-structured
JSON. Turning it into actionable safety intelligence requires:

1. Retrieving and normalising tens of thousands of records from the API
2. Aggregating drug-reaction co-occurrence counts
3. Applying statistical pharmacovigilance methods (PRR, ROR, etc.)
4. Ranking and presenting the strongest signals in a way a human can act on

No easy, open-source, point-and-click tool existed to do all of this together.

## Who Is Affected

- **Pharmacovigilance analysts at pharmaceutical companies** who must monitor their
  drugs post-launch and report signals to regulators — currently a largely manual,
  time-consuming process.
- **Independent researchers and public health scientists** who want to study drug
  safety trends but lack access to enterprise signal-detection software (e.g., Oracle
  Argus or WHO VigiBase), which can cost hundreds of thousands of dollars per year.
- **Regulatory reviewers at agencies like the FDA and EMA** who triage incoming
  signal reports and need to prioritise which drug-reaction pairs deserve deeper
  investigation.
- **Patients and advocacy groups** who have a fundamental interest in understanding
  whether a drug they rely on is accumulating a concerning safety profile.

## Why It Matters

The cost of a missed signal is not abstract:

| Impact | Scale |
|---|---|
| Vioxx cardiovascular events | ~27,000 deaths or heart attacks (FDA estimate) |
| Fen-phen cardiac valve disease | ~5 million patients exposed before recall |
| Thalidomide birth defects | ~10,000 affected children in 46 countries |

Beyond individual harm, delayed signal detection erodes public trust in medicines,
triggers billion-dollar litigation, and forces costly product recalls that could have
been avoided with earlier intervention.

## Why Existing Solutions Fall Short

- **Manual case review** — Analysts read individual reports one by one. Completely
  impractical at the scale of millions of records; only practical for reviewing a
  handful of flagged cases, not for discovering new ones.
- **Enterprise pharmacovigilance platforms (Argus, Empirica Signal)** — Powerful but
  extremely expensive, requiring institutional licenses. Completely inaccessible to
  independent researchers, small biotech firms, or public-health investigators in
  lower-income countries.
- **Static FDA FAERS dashboards** — The FDA provides summary statistics online but
  no tool for a user to ask "does *this specific drug* show an unusual rate of *this
  specific reaction*?" and get a statistically grounded answer in seconds.
- **Raw API access** — The openFDA API is publicly accessible but returns
  unprocessed JSON. Converting it into a ranked, statistically validated signal
  table requires non-trivial data-engineering and pharmacovigilance knowledge that
  most users do not have.
