import nltk
import re

# Download required NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

def analyze_linguistic_fraud_indicators(text: str) -> dict:
    """
    Extract linguistic features correlated with fraudulent filings.
    Based on research by Humpherys et al. (2011).
    """
    
    sentences = nltk.sent_tokenize(text)
    words = nltk.word_tokenize(text.lower())
    
    if not words:
        return {}

    # 1. Lexical diversity (Type-Token Ratio)
    unique_words = set(words)
    ttr = len(unique_words) / len(words)
    
    # 2. Passive voice ratio
    # Simple regex approximation
    passive_patterns = [
        r'\b(was|were|been|being|is|are|am)\s+\w+ed\b',
        r'\b(was|were|been|being|is|are|am)\s+\w+en\b'
    ]
    passive_count = sum(len(re.findall(p, text, re.I)) for p in passive_patterns)
    passive_ratio = passive_count / len(sentences) if sentences else 0
    
    # 3. Hedging language
    hedging_words = ['may', 'might', 'could', 'possibly', 'perhaps', 
                     'approximately', 'generally', 'typically', 'usually', 'seem']
    hedging_count = sum(words.count(w) for w in hedging_words)
    hedging_ratio = hedging_count / len(words)
    
    # 4. Self-reference reduction (fewer "I", "we" in deception)
    self_refs = words.count('we') + words.count('our') + words.count('i') + words.count('us')
    self_ref_ratio = self_refs / len(words)
    
    # 5. Positive affect anomaly
    # Loughran-McDonald positive words (subset)
    lm_positive = ['achieve', 'benefit', 'better', 'enhance', 'excellent',
                   'gain', 'good', 'great', 'improve', 'opportunity', 'success', 'successful']
    positive_count = sum(words.count(w) for w in lm_positive)
    positive_ratio = positive_count / len(words)
    
    red_flags = []
    # Thresholds (Example based, tuning required)
    if ttr < 0.20: # Example threshold
        red_flags.append("LOW_LEXICAL_DIVERSITY")
    if passive_ratio > 0.30:
        red_flags.append("EXCESSIVE_PASSIVE_VOICE")
    if hedging_ratio > 0.04:
        red_flags.append("EXCESSIVE_HEDGING")

    return {
        "metrics": {
            "lexical_diversity": ttr,
            "passive_voice_ratio": passive_ratio,
            "hedging_ratio": hedging_ratio,
            "self_ref_ratio": self_ref_ratio,
            "positive_ratio": positive_ratio
        },
        "red_flags": red_flags
    }
