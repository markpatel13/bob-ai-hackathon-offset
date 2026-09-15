"""
AI-assisted plain-English summaries for detected FDA safety signals.

The primary implementation is deterministic and requires no API key.
It converts verified statistical results from the PRR engine into
plain-English explanations.

Important:
    This module does NOT calculate PRR values itself.
    It does NOT infer causality.
    It does NOT invent medical conclusions.

Optional LLM integration can be added later without changing the
rest of the application.
"""

from typing import Any, Dict, Optional

import math
import pandas as pd


# -------------------------------------------------------------------
# Summary configuration
# -------------------------------------------------------------------

DEFAULT_SUMMARY_STYLE = "standard"

SUPPORTED_STYLES = {
    "short",
    "standard",
    "detailed",
}


# -------------------------------------------------------------------
# Main summary function
# -------------------------------------------------------------------

def generate_summary(
    signal: Any,
    style: str = DEFAULT_SUMMARY_STYLE,
) -> str:
    """
    Generate a plain-English summary for a detected safety signal.

    This version does not require an API key or external AI model.

    Parameters
    ----------
    signal : dict or pandas.Series
        A signal produced by signal_detector.py.

    style : str
        Summary style:
            "short"
            "standard"
            "detailed"

    Returns
    -------
    str
        Plain-English signal explanation.
    """

    _validate_style(style)

    data = _convert_signal_to_dict(signal)

    _validate_signal_data(data)

    drug = str(data["drug_name"]).strip()
    reaction = str(data["reaction"]).strip()

    prr = _safe_number(data.get("prr"))
    signal_class = data.get(
        "signal_class",
        "Signal",
    )

    A = _safe_integer(data.get("A"))
    B = _safe_integer(data.get("B"))
    C = _safe_integer(data.get("C"))
    D = _safe_integer(data.get("D"))

    drug_total = _safe_integer(
        data.get(
            "drug_total_reports",
            A + B,
        )
    )

    other_drug_total = _safe_integer(
        data.get(
            "other_drug_total_reports",
            C + D,
        )
    )

    drug_rate = _safe_number(
        data.get("drug_reaction_rate")
    )

    other_drug_rate = _safe_number(
        data.get("other_drug_reaction_rate")
    )

    # ---------------------------------------------------------------
    # Calculate rates if they weren't supplied.
    # ---------------------------------------------------------------

    if drug_rate is None:
        drug_rate = (
            A / drug_total
            if drug_total > 0
            else 0.0
        )

    if other_drug_rate is None:
        other_drug_rate = (
            C / other_drug_total
            if other_drug_total > 0
            else 0.0
        )

    # ---------------------------------------------------------------
    # Short summary
    # ---------------------------------------------------------------

    if style == "short":
        return _build_short_summary(
            drug=drug,
            reaction=reaction,
            prr=prr,
            report_count=A,
            signal_class=signal_class,
        )

    # ---------------------------------------------------------------
    # Standard summary
    # ---------------------------------------------------------------

    if style == "standard":
        return _build_standard_summary(
            drug=drug,
            reaction=reaction,
            prr=prr,
            signal_class=signal_class,
            A=A,
            drug_total=drug_total,
            drug_rate=drug_rate,
            other_drug_rate=other_drug_rate,
        )

    # ---------------------------------------------------------------
    # Detailed summary
    # ---------------------------------------------------------------

    return _build_detailed_summary(
        drug=drug,
        reaction=reaction,
        prr=prr,
        signal_class=signal_class,
        A=A,
        B=B,
        C=C,
        D=D,
        drug_total=drug_total,
        other_drug_total=other_drug_total,
        drug_rate=drug_rate,
        other_drug_rate=other_drug_rate,
    )


# -------------------------------------------------------------------
# Short summary
# -------------------------------------------------------------------

def _build_short_summary(
    drug: str,
    reaction: str,
    prr: Optional[float],
    report_count: int,
    signal_class: str,
) -> str:
    """
    Build a concise signal summary.
    """

    prr_text = _format_prr(prr)

    return (
        f"{drug} has a statistical reporting signal for "
        f"{reaction}. There are {report_count} reports for this "
        f"drug-reaction pair, with a PRR of {prr_text}. "
        f"Classification: {signal_class}. "
        f"This is a statistical signal and does not establish "
        f"causality."
    )


# -------------------------------------------------------------------
# Standard summary
# -------------------------------------------------------------------

def _build_standard_summary(
    drug: str,
    reaction: str,
    prr: Optional[float],
    signal_class: str,
    A: int,
    drug_total: int,
    drug_rate: float,
    other_drug_rate: float,
) -> str:
    """
    Build the main dashboard-friendly summary.
    """

    prr_text = _format_prr(prr)

    drug_rate_text = _format_percentage(
        drug_rate
    )

    other_rate_text = _format_percentage(
        other_drug_rate
    )

    comparison = _describe_prr(prr)

    return (
        f"**{drug} — {reaction}**\n\n"
        f"The dataset contains **{A} reports** involving "
        f"this drug-reaction pair. The calculated **PRR is "
        f"{prr_text}**, indicating that {reaction} represents "
        f"{comparison} among reports involving {drug} compared "
        f"with reports involving other drugs.\n\n"
        f"For {drug}, the reaction accounts for approximately "
        f"**{drug_rate_text}** of its {drug_total:,} analyzed "
        f"reports, compared with **{other_rate_text}** among "
        f"reports involving other drugs.\n\n"
        f"**Classification:** {signal_class}.\n\n"
        f"This result is a statistical reporting signal. It does "
        f"not establish that {drug} caused {reaction} and should "
        f"be interpreted alongside reporting bias, missing data, "
        f"duplicates, and expert pharmacovigilance assessment."
    )


# -------------------------------------------------------------------
# Detailed summary
# -------------------------------------------------------------------

def _build_detailed_summary(
    drug: str,
    reaction: str,
    prr: Optional[float],
    signal_class: str,
    A: int,
    B: int,
    C: int,
    D: int,
    drug_total: int,
    other_drug_total: int,
    drug_rate: float,
    other_drug_rate: float,
) -> str:
    """
    Build a detailed explanation including the PRR contingency
    table counts.
    """

    prr_text = _format_prr(prr)

    drug_rate_text = _format_percentage(
        drug_rate
    )

    other_rate_text = _format_percentage(
        other_drug_rate
    )

    comparison = _describe_prr(prr)

    return (
        f"### Safety Signal Summary\n\n"
        f"**Drug:** {drug}\n\n"
        f"**Reaction:** {reaction}\n\n"
        f"**PRR:** {prr_text}\n\n"
        f"**Classification:** {signal_class}\n\n"
        f"### What the numbers show\n\n"
        f"- **A — Drug + reaction:** {A:,} reports\n"
        f"- **B — Drug + other reactions:** {B:,} reports\n"
        f"- **C — Other drugs + reaction:** {C:,} reports\n"
        f"- **D — Other drugs + other reactions:** {D:,} reports\n\n"
        f"The reaction appears in approximately **{drug_rate_text}** "
        f"of the analyzed reports involving {drug}, compared with "
        f"**{other_rate_text}** among reports involving other drugs.\n\n"
        f"A PRR of **{prr_text}** means that the reporting proportion "
        f"for this reaction is {comparison} for this drug than in "
        f"the comparison group.\n\n"
        f"### Interpretation\n\n"
        f"The result meets the configured statistical signal "
        f"criteria used by the application. It indicates "
        f"disproportionate reporting in the analyzed dataset.\n\n"
        f"### Important limitation\n\n"
        f"A statistical reporting signal does **not** prove that "
        f"{drug} caused {reaction}. The result may be influenced by "
        f"reporting bias, duplicate or incomplete reports, patient "
        f"characteristics, co-medications, underlying conditions, "
        f"and differences in reporting practices. The result is "
        f"intended to support pharmacovigilance analysis rather than "
        f"replace expert medical or regulatory assessment."
    )


# -------------------------------------------------------------------
# Batch summaries
# -------------------------------------------------------------------

def generate_summaries(
    signals: pd.DataFrame,
    style: str = DEFAULT_SUMMARY_STYLE,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Generate summaries for multiple detected signals.

    Parameters
    ----------
    signals : pandas.DataFrame
        Dataframe containing detected signals.

    style : str
        Summary style.

    limit : int, optional
        Maximum number of summaries to generate.

    Returns
    -------
    pandas.DataFrame
        Copy of signal dataframe with a "summary" column.
    """

    _validate_style(style)

    if signals is None or signals.empty:
        return pd.DataFrame()

    result = signals.copy()

    if limit is not None:

        if limit < 1:
            raise ValueError(
                "limit must be at least 1."
            )

        result = result.head(limit).copy()

    result["summary"] = result.apply(
        lambda row: generate_summary(
            row,
            style=style,
        ),
        axis=1,
    )

    return result


# -------------------------------------------------------------------
# Structured explanation
# -------------------------------------------------------------------

def get_signal_facts(
    signal: Any,
) -> Dict[str, Any]:
    """
    Extract verified statistical facts from a signal.

    This function is useful if an external LLM is added later.

    The LLM should receive these facts and explain them rather than
    calculate or invent statistical values.
    """

    data = _convert_signal_to_dict(signal)

    return {
        "drug_name": data.get("drug_name"),
        "reaction": data.get("reaction"),
        "prr": data.get("prr"),
        "signal_class": data.get("signal_class"),
        "drug_reaction_reports": data.get("A", 0),
        "drug_other_reaction_reports": data.get("B", 0),
        "other_drug_reaction_reports": data.get("C", 0),
        "other_drug_other_reaction_reports": data.get("D", 0),
        "drug_total_reports": data.get(
            "drug_total_reports"
        ),
        "other_drug_total_reports": data.get(
            "other_drug_total_reports"
        ),
        "drug_reaction_rate": data.get(
            "drug_reaction_rate"
        ),
        "other_drug_reaction_rate": data.get(
            "other_drug_reaction_rate"
        ),
    }


# -------------------------------------------------------------------
# Optional LLM interface
# -------------------------------------------------------------------

def generate_llm_summary(
    signal: Any,
    provider: Optional[Any] = None,
) -> str:
    """
    Optional extension point for an external/local LLM.

    The current project does not require an API key, so if no
    provider is supplied this function falls back to the
    deterministic summary.

    A future provider should expose a callable interface such as:

        provider(facts) -> str

    The provider receives verified statistical facts only.
    """

    facts = get_signal_facts(signal)

    if provider is None:
        return generate_summary(
            signal,
            style="standard",
        )

    if not callable(provider):
        raise TypeError(
            "provider must be callable."
        )

    generated = provider(facts)

    if not generated:
        return generate_summary(
            signal,
            style="standard",
        )

    return str(generated).strip()


# -------------------------------------------------------------------
# Prompt builder for future LLM integration
# -------------------------------------------------------------------

def build_llm_prompt(
    signal: Any,
) -> str:
    """
    Build a safe prompt for a future LLM provider.

    The prompt explicitly prevents the model from making causal
    claims or changing the statistical values.
    """

    facts = get_signal_facts(signal)

    return f"""
You are explaining a pharmacovigilance statistical signal.

Use ONLY the verified facts provided below.

Do not:
- claim that the drug caused the reaction
- diagnose a patient
- recommend treatment
- invent statistics
- change any numerical value
- present the signal as confirmed causality

Explain the result in clear, non-technical language.

Verified facts:
Drug: {facts.get("drug_name")}
Reaction: {facts.get("reaction")}
PRR: {facts.get("prr")}
Classification: {facts.get("signal_class")}
Drug + reaction reports: {facts.get("drug_reaction_reports")}
Drug + other reaction reports: {facts.get("drug_other_reaction_reports")}
Other drug + reaction reports: {facts.get("other_drug_reaction_reports")}
Other drug + other reaction reports: {facts.get("other_drug_other_reaction_reports")}
Drug total reports: {facts.get("drug_total_reports")}
Other drug total reports: {facts.get("other_drug_total_reports")}
Drug reaction rate: {facts.get("drug_reaction_rate")}
Other drug reaction rate: {facts.get("other_drug_reaction_rate")}

Return a concise plain-English explanation of what the statistical
signal means and clearly state that it does not establish causality.
""".strip()


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

def _convert_signal_to_dict(
    signal: Any,
) -> Dict[str, Any]:
    """
    Convert a Series or dictionary into a normal dictionary.
    """

    if isinstance(signal, pd.Series):
        return signal.to_dict()

    if isinstance(signal, dict):
        return signal.copy()

    raise TypeError(
        "signal must be a pandas Series or dictionary."
    )


def _validate_signal_data(
    data: Dict[str, Any],
) -> None:
    """
    Validate required signal fields.
    """

    required_fields = [
        "drug_name",
        "reaction",
    ]

    missing = [
        field
        for field in required_fields
        if field not in data
        or data[field] is None
    ]

    if missing:
        raise ValueError(
            "Missing required signal fields: "
            + ", ".join(missing)
        )


def _validate_style(
    style: str,
) -> None:
    """
    Validate summary style.
    """

    if style not in SUPPORTED_STYLES:
        raise ValueError(
            f"Unsupported summary style '{style}'. "
            f"Choose from: "
            f"{', '.join(sorted(SUPPORTED_STYLES))}"
        )


def _safe_integer(
    value: Any,
) -> int:
    """
    Safely convert a value to an integer.
    """

    if value is None:
        return 0

    try:
        if pd.isna(value):
            return 0
    except (TypeError, ValueError):
        pass

    try:
        return int(value)

    except (TypeError, ValueError):
        return 0


def _safe_number(
    value: Any,
) -> Optional[float]:
    """
    Safely convert a value to a float.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def _format_prr(
    value: Optional[float],
) -> str:
    """
    Format PRR for natural-language output.
    """

    if value is None:
        return "N/A"

    if math.isinf(value):
        return "infinite"

    return f"{value:.2f}"


def _format_percentage(
    value: Optional[float],
) -> str:
    """
    Convert a decimal rate to a percentage string.
    """

    if value is None:
        return "N/A"

    return f"{value * 100:.2f}%"


def _describe_prr(
    prr: Optional[float],
) -> str:
    """
    Convert a PRR into a plain-English comparison.
    """

    if prr is None:
        return "not available"

    if math.isinf(prr):
        return (
            "an infinitely higher observed reporting proportion "
            "because the comparison reaction rate is zero in "
            "the analyzed data"
        )

    if prr > 1:
        return (
            f"approximately {prr:.2f} times higher"
        )

    if prr == 1:
        return (
            "approximately the same"
        )

    if prr > 0:
        return (
            f"lower, at approximately {prr:.2f} times "
            "the comparison proportion"
        )

    return "zero relative to the comparison proportion"


# -------------------------------------------------------------------
# Example execution
# -------------------------------------------------------------------

if __name__ == "__main__":

    example_signal = {
        "drug_name": "DURAGESIC-100",
        "reaction": "OVERDOSE",
        "prr": 4.72,
        "signal_class": "Strong Signal",
        "A": 25,
        "B": 100,
        "C": 50,
        "D": 500,
        "drug_total_reports": 125,
        "other_drug_total_reports": 550,
        "drug_reaction_rate": 0.20,
        "other_drug_reaction_rate": 0.0909,
    }

    print(
        generate_summary(
            example_signal,
            style="standard",
        )
    )