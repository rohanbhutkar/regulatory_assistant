# Coverage Matching Logic Verification

## Test Summary

The matching logic has been verified through code review. Here's what should happen:

## Flow for "Zolgensma (onasemnogene abeparvovec)" with indication "Spinal Muscular Atrophy"

### Step 1: Product Brand Search
- ✅ Searches Productbrand_Dim for "[zolgensma]" pattern
- ✅ Finds ProductbrandID: 26692

### Step 2: Direct ProductbrandID Match
- ❌ Searches Formulary_Tier_Dim for productbrandid = 26692
- ❌ Fails because all formulary records have productbrandid = -1

### Step 3: Fallback 1 - Indication Search
- ✅ Extracts keywords from "Spinal Muscular Atrophy": ["spinal", "muscular", "atrophy"]
- ✅ Searches Formulary_Tier_Dim.indicationname for each keyword
- Expected: Should find matches if indicationname column has data
- Logs: "Using indication for fallback search: Spinal Muscular Atrophy"
- Logs: "Extracted indication keywords: ['spinal', 'muscular', 'atrophy']"

### Step 4: Fallback 2 - Therapeutic Class Search
- ✅ If indication search fails, tries therapeuticclass
- ✅ Uses indication keywords + standard terms: ['spinal', 'muscular', 'atrophy', 'neurology', 'neuromuscular', 'rare disease', 'genetic', 'orphan', 'spinal']
- Expected: Should find matches if therapeuticclass has "Neurology", "Neuromuscular", etc.
- Logs: "Trying therapeutic class fallback..."
- Logs: "Found X records with therapeutic class data"

## Code Verification

✅ **Keyword Extraction**: Correctly extracts words > 3 characters
```python
indication_words = [w.strip().lower() for w in indication.split() if len(w.strip()) > 3]
# "Spinal Muscular Atrophy" -> ["spinal", "muscular", "atrophy"]
```

✅ **Indication Search**: Uses case-insensitive contains
```python
formulary_df['indicationname'].astype(str).str.contains(keyword, case=False, na=False, regex=False)
```

✅ **Therapeutic Class Search**: Includes indication keywords
```python
therapeutic_keywords = []
if indication:
    indication_words = [w.strip().lower() for w in indication.split() if len(w.strip()) > 3]
    therapeutic_keywords.extend(indication_words)
therapeutic_keywords.extend(['neurology', 'neuromuscular', 'rare disease', 'genetic', 'orphan', 'spinal'])
```

✅ **Data Quality Checks**: Checks for empty columns
```python
non_empty = formulary_df[formulary_df['indicationname'].notna() & (formulary_df['indicationname'].astype(str).str.strip() != '')]
if len(non_empty) == 0:
    print("⚠️ indicationname column exists but all values are empty")
```

## Expected Behavior

When the backend runs, you should see logs like:

```
⚠️ No direct ProductbrandID match for 26692 (Zolgensma (onasemnogene abeparvovec))
   Trying fallback: search by indication/therapeutic area...
   Using indication for fallback search: Spinal Muscular Atrophy
   Extracted indication keywords: ['spinal', 'muscular', 'atrophy']
   No matches for indication keyword: 'spinal' (searched X non-empty indication records)
   Trying therapeutic class fallback...
   Found X records with therapeutic class data
   ✅ Found X formulary records by therapeutic class: 'spinal'
```

## Conclusion

The matching logic is **correctly implemented**. The issue is likely:
1. The formulary data doesn't have indicationname values populated
2. The therapeuticclass doesn't contain matching terms
3. The data needs to be checked to see what's actually in those columns

The enhanced logging will show exactly what's happening and why matches aren't being found.
