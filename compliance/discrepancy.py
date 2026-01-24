def detect_discrepancies(mda_claims: list, financials: dict) -> list:
    """
    Detects inconsistencies between extracted claims and actual financial numbers.
    
    Args:
        mda_claims: List of dicts, e.g. [{"metric": "revenue", "direction": "increase", "value": ...}]
        financials: Dict of actual values e.g. {"revenue": {"change": 100, "value": 1000}}
    """
    discrepancies = []
    
    for claim in mda_claims:
        metric = claim.get('metric')
        actual = financials.get(metric)
        
        if actual:
            # Check directional consistency
            # If claim says increase, but actual change is negative
            if claim.get('direction') == 'increase' and actual.get('change', 0) < 0:
                discrepancies.append({
                    "type": "DIRECTIONAL_MISMATCH",
                    "claim": claim,
                    "actual": actual,
                    "severity": "HIGH",
                    "description": f"MD&A claims {metric} increased, but data shows decrease."
                })
            elif claim.get('direction') == 'decrease' and actual.get('change', 0) > 0:
                discrepancies.append({
                    "type": "DIRECTIONAL_MISMATCH",
                    "claim": claim,
                    "actual": actual,
                    "severity": "HIGH",
                     "description": f"MD&A claims {metric} decreased, but data shows increase."
                })
                
            # Check magnitude (if claim has a specific value)
            if claim.get('value') is not None and actual.get('value') is not None:
                claimed_val = float(claim['value'])
                actual_val = float(actual['value'])
                
                # Check for > 10% discrepancy
                if actual_val != 0:
                    diff_pct = abs(claimed_val - actual_val) / actual_val
                    if diff_pct > 0.1:
                        discrepancies.append({
                            "type": "MAGNITUDE_MISMATCH",
                            "claim": claim,
                            "actual": actual,
                            "severity": "MEDIUM",
                            "description": f"MD&A claims {metric} is {claimed_val}, data shown {actual_val}."
                        })
    
    return discrepancies
