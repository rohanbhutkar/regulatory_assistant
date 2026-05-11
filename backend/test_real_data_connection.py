#!/usr/bin/env python3
"""
Quick test to verify real data agents are accessible and loaded
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("REAL DATA AGENTS CONNECTION TEST")
print("=" * 80)
print()

# Test 1: Claims Data Agent
print("1. Testing Claims Data Agent...")
try:
    from agents.claims_data_agent import claims_data_agent
    if hasattr(claims_data_agent, 'claims_df'):
        df = claims_data_agent.claims_df
        print(f"   ✅ Claims data loaded: {len(df):,} records")
        print(f"   Columns: {', '.join(list(df.columns)[:10])}...")
        
        # Test diabetes search
        mask = df['D1'].astype(str).str.contains('diabetes', case=False, na=False) | \
               df['D2'].astype(str).str.contains('diabetes', case=False, na=False)
        diabetes_count = mask.sum()
        print(f"   Diabetes patients: {diabetes_count:,}")
    else:
        print("   ❌ Claims data not loaded (claims_df attribute missing)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test 2: FDA Labels Agent
print("2. Testing FDA Labels Agent...")
try:
    from agents.fda_labels_agent import fda_labels_agent
    if hasattr(fda_labels_agent, 'labels_df'):
        df = fda_labels_agent.labels_df
        print(f"   ✅ FDA labels loaded: {len(df):,} drug labels")
        print(f"   Columns: {', '.join(list(df.columns)[:10])}...")
        
        # Test diabetes search
        if 'indications_and_usage' in df.columns:
            diabetes_labels = df[df['indications_and_usage'].astype(str).str.contains('diabetes', case=False, na=False)]
            print(f"   Diabetes drugs: {len(diabetes_labels)}")
    else:
        print("   ❌ FDA labels not loaded (labels_df attribute missing)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test 3: TrialTrove Agent
print("3. Testing TrialTrove Agent...")
try:
    from agents.trialtrove_agent import trialtrove_agent
    if hasattr(trialtrove_agent, 'trials_df'):
        df = trialtrove_agent.trials_df
        print(f"   ✅ TrialTrove data loaded: {len(df):,} trials")
        print(f"   Columns: {', '.join(list(df.columns)[:10])}...")
        
        # Test Phase III trials
        if 'phase' in df.columns:
            phase3 = df[df['phase'].astype(str).str.contains('Phase III', case=False, na=False)]
            print(f"   Phase III trials: {len(phase3):,}")
    else:
        print("   ❌ TrialTrove data not loaded (trials_df attribute missing)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test 4: SiteTrove Agent  
print("4. Testing SiteTrove Agent...")
try:
    from agents.site_trove_agent import site_trove_agent
    if hasattr(site_trove_agent, 'sites_df'):
        df = site_trove_agent.sites_df
        print(f"   ✅ SiteTrove data loaded: {len(df):,} sites")
        print(f"   Columns: {', '.join(list(df.columns)[:10])}...")
    else:
        print("   ❌ SiteTrove data not loaded (sites_df attribute missing)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

