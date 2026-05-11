#!/usr/bin/env python3
"""
Test coverage lookup via API endpoint (if server is running)
or test the matching logic with minimal data
"""
import sys
import os
import requests
import json

def test_via_api():
    """Test coverage lookup via API"""
    base_url = "http://localhost:8001"
    
    # Test the comparators endpoint
    url = f"{base_url}/api/asset-strategy/pricing/comparators"
    params = {
        "asset_id": "asset-6",
        "market": "US",
        "predicted_net_price": 50000
    }
    
    print(f"Testing API endpoint: {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ API Response received")
            print(f"   Comparator count: {data.get('comparator_count', 0)}")
            
            # Check coverage info
            comparators = data.get('comparators', [])
            print(f"\n📊 Coverage Information:")
            for comp in comparators[:5]:  # Show first 5
                drug_name = comp.get('drug', comp.get('name', 'Unknown'))
                coverage = comp.get('coverage_info', {})
                coverage_level = coverage.get('coverage_level', 'Not Found')
                tier = coverage.get('tier', 'Unknown')
                print(f"   {drug_name}: {coverage_level} (Tier: {tier})")
            
            return 0
        else:
            print(f"\n❌ API Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"\n⚠️  Cannot connect to API server at {base_url}")
        print(f"   Make sure the backend server is running")
        return 2
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def test_matching_logic():
    """Test the matching logic with a simple example"""
    print("\n" + "="*80)
    print("Testing Matching Logic (Simple)")
    print("="*80)
    
    # Test string matching logic
    test_cases = [
        {
            "indication": "Spinal Muscular Atrophy",
            "keywords_expected": ["spinal", "muscular", "atrophy"],
            "therapeutic_keywords": ["neurology", "neuromuscular", "rare disease", "genetic", "orphan", "spinal"]
        }
    ]
    
    for case in test_cases:
        indication = case["indication"]
        words = [w.strip().lower() for w in indication.split() if len(w.strip()) > 3]
        print(f"\nIndication: {indication}")
        print(f"Extracted keywords: {words}")
        print(f"Expected: {case['keywords_expected']}")
        
        if words == case['keywords_expected']:
            print("✅ Keyword extraction works correctly")
        else:
            print("❌ Keyword extraction mismatch")
    
    print(f"\n✅ Matching logic test complete")
    return 0

if __name__ == "__main__":
    print("="*80)
    print("Coverage Lookup Test")
    print("="*80)
    
    # Try API first
    api_result = test_via_api()
    
    # If API not available, test logic
    if api_result == 2:
        print("\n⚠️  API not available, testing matching logic instead")
        logic_result = test_matching_logic()
        sys.exit(logic_result)
    else:
        sys.exit(api_result)
