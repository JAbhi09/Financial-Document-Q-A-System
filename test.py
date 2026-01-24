from compliance.beneish import calculate_beneish_m_score_with_ticker
import json

# Test with Netflix
ticker = "NFLX"
print(f"Testing M-Score calculation for {ticker}")
print("="*80)

result = calculate_beneish_m_score_with_ticker(ticker, current_year=2024)

print("\n" + "="*80)
print("RESULTS:")
print("="*80)
print(json.dumps(result, indent=2))

if result.get('data_source') == 'real':
    print("\n✅ SUCCESS - Using real SEC data!")
else:
    print("\n⚠️ Using demo data")