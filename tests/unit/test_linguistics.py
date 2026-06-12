"""
Unit tests for compliance/linguistics.py — linguistic fraud indicator analysis.

Covers:
  - Empty / very short input edge cases
  - Return structure and value ranges
  - Passive voice detection and EXCESSIVE_PASSIVE_VOICE flag
  - Hedging language detection and EXCESSIVE_HEDGING flag
  - Lexical diversity (TTR) and LOW_LEXICAL_DIVERSITY flag
  - Self-reference ratio ("we / our / us")
  - Positive-affect ratio (Loughran-McDonald word list)
  - Multiple simultaneous red flags
  - Clean text that produces zero red flags
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from compliance.linguistics import analyze_linguistic_fraud_indicators


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CLEAN_FILING_TEXT = (
    "Apple Inc. reported total revenue of 394 billion dollars for fiscal 2024. "
    "The company achieved record earnings per share of 6.11 dollars. "
    "Management executed on strategic priorities across all product segments. "
    "Capital expenditures reached 11 billion dollars, supporting infrastructure growth. "
    "The board authorized a new share repurchase program of 110 billion dollars."
)

PASSIVE_FILING_TEXT = (
    "Revenue was recognized in accordance with ASC 606. "
    "Expenses were allocated across business segments by the finance team. "
    "Results were reported to investors and regulators quarterly. "
    "Disclosures were reviewed and approved by external auditors."
)

HEDGING_FILING_TEXT = (
    "Results may possibly improve in future periods. "
    "The company might typically consider these risks. "
    "Outcomes could approximately be expected to vary. "
    "Management generally and usually seems cautious about guidance."
)

LOW_DIVERSITY_TEXT = "the " * 100 + "cat"  # 101 words, 2 unique → TTR ≈ 0.02


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLinguisticFraudIndicators:
    """Tests for analyze_linguistic_fraud_indicators()."""

    # --- Edge cases ----------------------------------------------------------

    @pytest.mark.unit
    def test_empty_string_returns_empty_dict(self):
        """Empty input should return {} immediately (no words to analyse)."""
        result = analyze_linguistic_fraud_indicators("")
        assert result == {}

    @pytest.mark.unit
    def test_whitespace_only_returns_empty_dict(self):
        """Whitespace-only string tokenises to zero words."""
        result = analyze_linguistic_fraud_indicators("   \n\t  ")
        assert result == {}

    @pytest.mark.unit
    def test_single_word_returns_full_structure(self):
        """Even a single word should produce a valid result dict, not {}."""
        result = analyze_linguistic_fraud_indicators("hello")
        assert "metrics" in result
        assert "red_flags" in result

    # --- Return structure ----------------------------------------------------

    @pytest.mark.unit
    def test_return_structure_has_required_keys(self):
        """Result must contain 'metrics' and 'red_flags' at top level."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        assert "metrics" in result
        assert "red_flags" in result
        assert isinstance(result["red_flags"], list)
        assert isinstance(result["metrics"], dict)

    @pytest.mark.unit
    def test_metrics_contains_all_five_indicators(self):
        """All five metric keys must be present."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        expected_keys = {
            "lexical_diversity",
            "passive_voice_ratio",
            "hedging_ratio",
            "self_ref_ratio",
            "positive_ratio",
        }
        assert expected_keys == set(result["metrics"].keys())

    @pytest.mark.unit
    def test_ratio_metrics_are_non_negative(self):
        """Every metric ratio must be >= 0."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        for key, value in result["metrics"].items():
            assert value >= 0, f"{key} should be non-negative, got {value}"

    @pytest.mark.unit
    def test_lexical_diversity_at_most_one(self):
        """TTR cannot exceed 1.0 (unique words ≤ total words)."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        assert result["metrics"]["lexical_diversity"] <= 1.0

    @pytest.mark.unit
    def test_lexical_diversity_equals_one_for_all_unique_words(self):
        """A sentence where every word is unique should give TTR = 1.0."""
        text = "Apple Microsoft Google Amazon Tesla JPMorgan Walmart Netflix."
        result = analyze_linguistic_fraud_indicators(text)
        assert result["metrics"]["lexical_diversity"] == pytest.approx(1.0)

    # --- Clean text (no red flags) -------------------------------------------

    @pytest.mark.unit
    def test_clean_text_produces_no_red_flags(self):
        """Direct, active, non-hedging financial text should raise zero red flags."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        assert result["red_flags"] == []

    # --- Passive voice -------------------------------------------------------

    @pytest.mark.unit
    def test_passive_voice_flag_triggered(self):
        """Text with predominantly passive constructions raises EXCESSIVE_PASSIVE_VOICE."""
        result = analyze_linguistic_fraud_indicators(PASSIVE_FILING_TEXT)
        assert "EXCESSIVE_PASSIVE_VOICE" in result["red_flags"]

    @pytest.mark.unit
    def test_passive_voice_ratio_above_threshold_for_passive_text(self):
        """Passive ratio for the passive sample should exceed the 0.30 threshold."""
        result = analyze_linguistic_fraud_indicators(PASSIVE_FILING_TEXT)
        assert result["metrics"]["passive_voice_ratio"] > 0.30

    @pytest.mark.unit
    def test_no_passive_flag_for_active_text(self):
        """Active-voice text should not raise the passive voice flag."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        assert "EXCESSIVE_PASSIVE_VOICE" not in result["red_flags"]

    # --- Hedging language ----------------------------------------------------

    @pytest.mark.unit
    def test_excessive_hedging_flag_triggered(self):
        """Text dense with hedging words raises EXCESSIVE_HEDGING."""
        result = analyze_linguistic_fraud_indicators(HEDGING_FILING_TEXT)
        assert "EXCESSIVE_HEDGING" in result["red_flags"]

    @pytest.mark.unit
    def test_hedging_ratio_above_threshold_for_hedged_text(self):
        """Hedging ratio for the hedged sample must exceed 0.04."""
        result = analyze_linguistic_fraud_indicators(HEDGING_FILING_TEXT)
        assert result["metrics"]["hedging_ratio"] > 0.04

    @pytest.mark.unit
    def test_no_hedging_flag_for_direct_text(self):
        """Text with no hedging vocabulary must not raise EXCESSIVE_HEDGING."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        assert "EXCESSIVE_HEDGING" not in result["red_flags"]

    @pytest.mark.unit
    def test_individual_hedging_words_counted(self):
        """Each distinct hedging word ('may', 'might', 'could', etc.) must be counted."""
        # One hedging word per sentence to confirm they are all caught
        text = "Results may vary. Outcomes might differ. Costs could increase. Performance seems uncertain."
        result = analyze_linguistic_fraud_indicators(text)
        # 4 hedging tokens out of ~16 total ≈ 0.25 > 0.04
        assert result["metrics"]["hedging_ratio"] > 0.04
        assert "EXCESSIVE_HEDGING" in result["red_flags"]

    # --- Lexical diversity ---------------------------------------------------

    @pytest.mark.unit
    def test_low_lexical_diversity_flag_triggered(self):
        """Highly repetitive text (TTR < 0.20) raises LOW_LEXICAL_DIVERSITY."""
        result = analyze_linguistic_fraud_indicators(LOW_DIVERSITY_TEXT)
        assert "LOW_LEXICAL_DIVERSITY" in result["red_flags"]

    @pytest.mark.unit
    def test_lexical_diversity_below_threshold_for_repetitive_text(self):
        """TTR for the repetitive sample must be below 0.20."""
        result = analyze_linguistic_fraud_indicators(LOW_DIVERSITY_TEXT)
        assert result["metrics"]["lexical_diversity"] < 0.20

    @pytest.mark.unit
    def test_no_low_diversity_flag_for_varied_text(self):
        """Varied vocabulary in clean text should not raise LOW_LEXICAL_DIVERSITY."""
        result = analyze_linguistic_fraud_indicators(CLEAN_FILING_TEXT)
        assert "LOW_LEXICAL_DIVERSITY" not in result["red_flags"]

    # --- Self-reference ratio ------------------------------------------------

    @pytest.mark.unit
    def test_self_reference_ratio_nonzero_for_first_person_text(self):
        """Text using 'we', 'our', 'us' must produce a nonzero self_ref_ratio."""
        text = (
            "We achieved our targets this year. Our team delivered strong results. "
            "We invested in our people and our infrastructure."
        )
        result = analyze_linguistic_fraud_indicators(text)
        assert result["metrics"]["self_ref_ratio"] > 0

    @pytest.mark.unit
    def test_self_reference_ratio_zero_for_third_person_text(self):
        """Third-person-only text should give a near-zero self_ref_ratio."""
        text = (
            "The company achieved its targets. Management delivered strong results. "
            "The board invested in infrastructure and technology assets."
        )
        result = analyze_linguistic_fraud_indicators(text)
        # 'i' may appear as the letter alone (e.g. tokenised from contractions) —
        # use a generous threshold rather than asserting exactly 0.
        assert result["metrics"]["self_ref_ratio"] < 0.05

    # --- Positive affect ratio -----------------------------------------------

    @pytest.mark.unit
    def test_positive_ratio_nonzero_for_positive_text(self):
        """Text containing Loughran-McDonald positive words must have positive_ratio > 0."""
        text = (
            "We achieve excellent results and gain significant benefit. "
            "Our success and opportunity improve the good outlook. "
            "Great performance demonstrates our ability to enhance shareholder value."
        )
        result = analyze_linguistic_fraud_indicators(text)
        assert result["metrics"]["positive_ratio"] > 0

    @pytest.mark.unit
    def test_positive_ratio_zero_for_neutral_text(self):
        """Neutral text with none of the LM positive words should give ratio = 0."""
        text = (
            "The company filed its annual report with the SEC. "
            "Total revenue was 394 billion dollars for the fiscal period. "
            "The filing date was October fifteenth."
        )
        result = analyze_linguistic_fraud_indicators(text)
        assert result["metrics"]["positive_ratio"] == 0.0

    # --- Multiple simultaneous red flags ------------------------------------

    @pytest.mark.unit
    def test_multiple_red_flags_simultaneously(self):
        """
        A text that combines heavy hedging AND dominant passive voice should
        raise both EXCESSIVE_HEDGING and EXCESSIVE_PASSIVE_VOICE.
        """
        combined = (
            "Revenue was recognized by staff. Expenses were reported by auditors. "
            "Results were communicated to stakeholders. Costs were allocated by management. "
            "The company may possibly perhaps might generally consider these factors. "
            "Outcomes could typically seem to vary based on conditions."
        )
        result = analyze_linguistic_fraud_indicators(combined)
        flags = result["red_flags"]
        assert "EXCESSIVE_PASSIVE_VOICE" in flags
        assert "EXCESSIVE_HEDGING" in flags
