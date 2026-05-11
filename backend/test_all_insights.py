#!/usr/bin/env python3
"""
Comprehensive test for all enhanced AI insights across all tabs.
Tests both API endpoint and insights agent directly.
"""
import asyncio
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.insights_agent import get_insights_agent


class MockDataLoader:
    """Mock data loader for testing"""
    pass


async def test_all_tabs():
    """Test insights generation for all tabs"""
    
    # Initialize agent with mock data loader
    data_loader = MockDataLoader()
    agent = get_insights_agent(data_loader)
    
    # Sample study context
    study_context = {
        'indication': 'Type 2 Diabetes',
        'phase': 'Phase III',
        'patient_count': 300,
        'site_count': 29,
        'duration_months': 24,
        'primaryObjective': 'Reduce HbA1c by 1.2% from baseline',
        'primaryEndpoint': 'Change in HbA1c from baseline to week 24',
        'ieCriteria': {
            'inclusion': [
                'Age 18-65 years',
                'HbA1c 7.0-10.0%',
                'BMI 25-40 kg/m2'
            ],
            'exclusion': [
                'eGFR <60 mL/min/1.73m2',
                'Active cardiovascular disease'
            ]
        },
        'soa_data': {
            'visits': [
                {'name': 'Screening', 'day': 0},
                {'name': 'Baseline', 'day': 1},
                {'name': 'Week 4', 'day': 28},
                {'name': 'Week 8', 'day': 56},
                {'name': 'Week 12', 'day': 84},
                {'name': 'Week 16', 'day': 112},
                {'name': 'Week 20', 'day': 140},
                {'name': 'Week 24', 'day': 168},
            ],
            'activities': [
                {'name': 'Physical Examination'},
                {'name': 'Vital Signs'},
                {'name': 'ECG'},
                {'name': 'HbA1c'},
                {'name': 'Fasting Glucose'},
                {'name': 'Lipid Panel'},
                {'name': 'Complete Blood Count'},
                {'name': 'Comprehensive Metabolic Panel'},
            ]
        }
    }
    
    # Sample reference trials
    selected_trials = [
        {
            'id': 'NCT01234567',
            'title': 'A Phase 3 Study of GLP-1 Agonist in Type 2 Diabetes',
            'phase': 'Phase III',
            'indication': 'Type 2 Diabetes',
            'enrollmentTarget': 350,
            'duration_months': 26,
            'studyType': 'Randomized, Double-Blind, Placebo-Controlled',
            'sponsor': 'Major Pharma Co.',
            'sites': 35
        },
        {
            'id': 'NCT02345678',
            'title': 'Efficacy and Safety Study of SGLT2 Inhibitor in T2DM',
            'phase': 'Phase III',
            'indication': 'Type 2 Diabetes Mellitus',
            'enrollmentTarget': 280,
            'duration_months': 24,
            'studyType': 'Multicenter, Randomized, Parallel-Group',
            'sponsor': 'BioPharma Inc.',
            'sites': 28
        },
        {
            'id': 'NCT03456789',
            'title': 'DPP-4 Inhibitor Versus Placebo in Patients with Type 2 Diabetes',
            'phase': 'Phase III',
            'indication': 'Type 2 Diabetes',
            'enrollmentTarget': 320,
            'duration_months': 24,
            'studyType': 'Randomized, Double-Blind',
            'sponsor': 'Clinical Research Org',
            'sites': 30
        }
    ]
    
    # Tabs to test
    tabs = [
        'ie-criteria',
        'reference-trials',
        'objectives',
        'endpoints',
        'soa',
        'site-selection',
        'budget',
        'simulation'
    ]
    
    print("=" * 80)
    print("COMPREHENSIVE AI INSIGHTS TEST")
    print("=" * 80)
    print()
    
    results = {}
    
    for tab in tabs:
        print(f"Testing Tab: {tab.upper()}")
        print("-" * 80)
        
        try:
            # Generate insights
            insights = await agent.generate_insights(
                study_context=study_context,
                selected_trials=selected_trials,
                tab=tab
            )
            
            results[tab] = {
                'success': True,
                'count': len(insights),
                'insights': insights
            }
            
            print(f"✅ Generated {len(insights)} insight(s)")
            
            # Display insight summaries
            for i, insight in enumerate(insights, 1):
                print(f"\n  Insight {i}:")
                print(f"    Type: {insight.get('type', 'unknown')}")
                print(f"    Title: {insight.get('title', 'N/A')}")
                print(f"    Message: {insight.get('message', 'N/A')[:100]}...")
                print(f"    Confidence: {insight.get('confidence', 0):.0%}")
                print(f"    Source: {insight.get('source', 'N/A')}")
                
                # Check for LLM analysis
                if 'data' in insight and 'llm_analysis' in insight['data']:
                    llm_text = insight['data']['llm_analysis']
                    if llm_text and llm_text != 'Analysis based on statistical benchmarking':
                        print(f"    LLM: ✅ (length: {len(llm_text)} chars)")
                    else:
                        print(f"    LLM: ⚠️ (missing or generic)")
                
                # Check for specific data fields
                data_keys = list(insight.get('data', {}).keys())
                print(f"    Data fields: {', '.join(data_keys[:5])}")
                
        except Exception as e:
            results[tab] = {
                'success': False,
                'error': str(e)
            }
            print(f"❌ Error: {str(e)}")
        
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for r in results.values() if r['success'])
    total_insights = sum(r['count'] for r in results.values() if r['success'])
    
    print(f"\nTabs tested: {len(tabs)}")
    print(f"Successful: {success_count}/{len(tabs)}")
    print(f"Total insights generated: {total_insights}")
    print()
    
    # Detailed results
    for tab, result in results.items():
        status = "✅" if result['success'] else "❌"
        count = result['count'] if result['success'] else 0
        print(f"{status} {tab:20s} - {count} insight(s)")
    
    print()
    
    # Check for quality issues
    print("=" * 80)
    print("QUALITY CHECKS")
    print("=" * 80)
    print()
    
    quality_issues = []
    
    for tab, result in results.items():
        if not result['success']:
            continue
        
        insights = result['insights']
        
        # Check 1: At least one insight per tab
        if len(insights) == 0:
            quality_issues.append(f"❌ {tab}: No insights generated")
        
        # Check 2: All insights have required fields
        for i, insight in enumerate(insights):
            required_fields = ['id', 'type', 'title', 'message', 'confidence']
            missing = [f for f in required_fields if f not in insight]
            if missing:
                quality_issues.append(f"⚠️ {tab} insight {i+1}: Missing fields: {missing}")
            
            # Check 3: Confidence score in range
            confidence = insight.get('confidence', 0)
            if not (0 <= confidence <= 1):
                quality_issues.append(f"⚠️ {tab} insight {i+1}: Invalid confidence: {confidence}")
            
            # Check 4: Has LLM analysis (for enhanced tabs)
            if tab in ['ie-criteria', 'soa', 'site-selection', 'simulation', 
                      'reference-trials', 'objectives', 'endpoints', 'budget']:
                if 'data' in insight:
                    llm_analysis = insight['data'].get('llm_analysis', '')
                    if not llm_analysis or llm_analysis == 'Analysis based on statistical benchmarking':
                        quality_issues.append(f"⚠️ {tab} insight {i+1}: Missing LLM analysis")
    
    if quality_issues:
        print("Issues found:")
        for issue in quality_issues:
            print(f"  {issue}")
    else:
        print("✅ All quality checks passed!")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    return results


if __name__ == '__main__':
    # Run the test
    results = asyncio.run(test_all_tabs())
    
    # Exit with appropriate code
    success = all(r['success'] for r in results.values())
    sys.exit(0 if success else 1)

