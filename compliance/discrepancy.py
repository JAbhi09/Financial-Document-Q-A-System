import re

_UNIT_MULTIPLIERS = {
    'trillion': 1_000_000_000_000,
    'billion':  1_000_000_000,
    'million':  1_000_000,
    'thousand': 1_000,
}


def _is_table_artifact(sentence: str) -> bool:
    """Return True for garbled table rows that should not be treated as narrative claims."""
    s = sentence.strip()
    # Too short to carry a real claim
    if len(s) < 20:
        return True
    # Runs of 6+ consecutive digits signal merged year/number table headers (e.g. "202520242023")
    if re.search(r'\d{6,}', s):
        return True
    # Fewer than 3 real words (alpha tokens ≥ 2 chars) → table fragment, not prose
    if len(re.findall(r'[A-Za-z]{2,}', s)) < 3:
        return True
    return False


def _extract_dollar_value(sentence: str):
    """
    Extract a normalized dollar amount (raw dollars) from a narrative sentence.

    Recognized forms:
        $391 billion   → 391_000_000_000
        $1.5 trillion  → 1_500_000_000_000
        394 million    → 394_000_000

    Bare percentages ("36.8%") return None — they are rates, not dollar amounts.
    """
    m = re.search(
        r'\$\s*([\d,]+\.?\d*)\s*(trillion|billion|million|thousand)'
        r'|([\d,]+\.?\d*)\s+(trillion|billion|million)',
        sentence, re.I,
    )
    if not m:
        return None
    if m.group(1) is not None:
        num_str = m.group(1)
        unit = (m.group(2) or '').lower()
    else:
        num_str = m.group(3)
        unit = m.group(4).lower()
    num = float(num_str.replace(',', ''))
    return num * _UNIT_MULTIPLIERS.get(unit, 1)


def extract_claims_from_text(text: str) -> list:
    """
    Extract directional financial claims from MD&A text using pattern matching.

    Finds sentences that assert a metric went up or down, e.g.:
        "Revenue increased 12% to $394 billion"
        "Net income decreased due to higher operating expenses"

    Returns a list of claim dicts compatible with detect_discrepancies().
    """
    metric_patterns = {
        'revenue':          r'\b(revenue|revenues|net sales|total sales|net revenue)\b',
        'net_income':       r'\b(net income|net earnings|net loss|net profit)\b',
        'gross_profit':     r'\b(gross profit|gross margin)\b(?!\s*(percentage|percent|%|ratio))',
        'operating_income': r'\b(operating income|operating profit|operating loss|operating margin)\b',
        'cash':             r'\b(cash and cash equivalents|cash flow from operations|operating cash flow)\b',
    }
    increase_pat = re.compile(
        r'\b(increased?|grew|growth|higher|improved|rose|gain|up|expand)\b', re.I
    )
    decrease_pat = re.compile(
        r'\b(decreased?|declined?|lower|fell|drop|loss|reduction|down|contract)\b', re.I
    )

    seen_metrics: set = set()
    claims: list = []

    # Work on first 60k chars (MD&A is near the front)
    sentences = re.split(r'(?<=[.!?])\s+', text[:60_000])

    for sentence in sentences:
        if _is_table_artifact(sentence):
            continue

        sl = sentence.lower()
        for metric, pat in metric_patterns.items():
            if metric in seen_metrics:
                continue
            if not re.search(pat, sl):
                continue

            # Sentences about operating cash flow belong to the 'cash' metric; skip net_income
            # regardless of whether the cash-flow phrase appears before or after the net_income term.
            if metric == 'net_income' and re.search(
                r'\b(operating cash flow|cash flow from operations)\b', sl
            ):
                continue

            if increase_pat.search(sl):
                direction = 'increase'
            elif decrease_pat.search(sl):
                direction = 'decrease'
            else:
                continue

            # Only capture explicit dollar amounts; bare percentages are rates, not magnitudes.
            value = _extract_dollar_value(sentence)

            claims.append({
                'metric':    metric,
                'direction': direction,
                'value':     value,
                'sentence':  sentence.strip()[:200],
            })
            seen_metrics.add(metric)

    return claims


def build_financials_for_discrepancy(current: dict, prior: dict) -> dict:
    """
    Build the financials dict expected by detect_discrepancies() from raw
    SEC data returned by get_financial_data_for_year().

    Returns:
        {
            'revenue':    {'change': <current - prior>, 'value': <current>},
            'net_income': {'change': ..., 'value': ...},
            ...
        }
    """
    mapping = {
        'revenue':          'revenue',
        'net_income':       'net_income',
        'gross_profit':     None,   # derived below
        'operating_income': None,
        'cash':             'operating_cash_flow',
    }

    financials: dict = {}

    for claim_metric, raw_key in mapping.items():
        if raw_key is None:
            continue
        curr_val = current.get(raw_key)
        prior_val = prior.get(raw_key)
        if curr_val is not None and prior_val is not None:
            financials[claim_metric] = {
                'value':  curr_val,
                'change': curr_val - prior_val,
            }

    # Derive gross_profit = revenue - cogs
    curr_rev  = current.get('revenue')
    curr_cogs = current.get('cogs')
    prior_rev  = prior.get('revenue')
    prior_cogs = prior.get('cogs')
    if all(v is not None for v in [curr_rev, curr_cogs, prior_rev, prior_cogs]):
        curr_gp  = curr_rev  - curr_cogs
        prior_gp = prior_rev - prior_cogs
        financials['gross_profit'] = {
            'value':  curr_gp,
            'change': curr_gp - prior_gp,
        }

    return financials


def detect_discrepancies(mda_claims: list, financials: dict) -> list:
    """
    Detect inconsistencies between MD&A narrative claims and actual financials.

    Args:
        mda_claims:  List of claim dicts from extract_claims_from_text().
        financials:  Dict from build_financials_for_discrepancy() or manually built.

    Returns:
        List of discrepancy dicts, each with type, severity, and description.
    """
    discrepancies = []

    for claim in mda_claims:
        metric = claim.get('metric')
        actual = financials.get(metric)

        if not actual:
            continue

        # Directional check
        if claim.get('direction') == 'increase' and actual.get('change', 0) < 0:
            discrepancies.append({
                "type":        "DIRECTIONAL_MISMATCH",
                "claim":       claim,
                "actual":      actual,
                "severity":    "HIGH",
                "description": (
                    f"MD&A claims {metric} increased, but reported data shows a decrease "
                    f"(change: {actual['change']:+,.0f})."
                ),
            })
        elif claim.get('direction') == 'decrease' and actual.get('change', 0) > 0:
            discrepancies.append({
                "type":        "DIRECTIONAL_MISMATCH",
                "claim":       claim,
                "actual":      actual,
                "severity":    "HIGH",
                "description": (
                    f"MD&A claims {metric} decreased, but reported data shows an increase "
                    f"(change: {actual['change']:+,.0f})."
                ),
            })

        # Magnitude check (only when claim carries an explicit value)
        if claim.get('value') is not None and actual.get('value'):
            claimed_val = float(claim['value'])
            actual_val  = float(actual['value'])
            if actual_val != 0:
                diff_pct = abs(claimed_val - actual_val) / abs(actual_val)
                if diff_pct > 0.1:
                    discrepancies.append({
                        "type":        "MAGNITUDE_MISMATCH",
                        "claim":       claim,
                        "actual":      actual,
                        "severity":    "MEDIUM",
                        "description": (
                            f"MD&A states {metric} is {claimed_val:,.1f}, "
                            f"but data shows {actual_val:,.0f} "
                            f"({diff_pct:.1%} variance)."
                        ),
                    })

    return discrepancies
