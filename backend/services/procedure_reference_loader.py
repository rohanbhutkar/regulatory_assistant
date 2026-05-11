"""
Load procedure reference data from B&C CSV
Uses the same fuzzy matching algorithms as B&C project
"""

import csv
import os
import re
from typing import Dict, List, Any, Optional
import logging

# Try thefuzz first (modern version), fall back to fuzzywuzzy
try:
    from thefuzz import fuzz
except ImportError:
    from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)


class ProcedureReferenceLoader:
    """
    Load and manage procedure reference data from CSV
    Uses B&C fuzzy matching algorithms for high accuracy
    """
    
    # Common medical abbreviations (from B&C project)
    MEDICAL_ABBREVIATIONS = {
        'bp': 'blood pressure',
        'hr': 'heart rate',
        'ecg': 'electrocardiogram',
        'ekg': 'electrocardiogram',
        'mri': 'magnetic resonance imaging',
        'ct': 'computed tomography',
        'cbc': 'complete blood count',
        'ae': 'adverse event',
        'aes': 'adverse events',
        'sae': 'serious adverse event',
        'saes': 'serious adverse events',
        'qol': 'quality of life',
        'vs': 'vital signs',
        'rr': 'respiratory rate',
        'temp': 'temperature',
        'wt': 'weight',
        'ht': 'height',
        'bmi': 'body mass index',
        'pe': 'physical exam',
        'hx': 'history',
        'dx': 'diagnosis',
        'tx': 'treatment',
        'rx': 'prescription',
        'lab': 'laboratory',
        'xray': 'x ray',
        'echo': 'echocardiogram',
        'eeg': 'electroencephalogram',
        'emg': 'electromyography',
        'ua': 'urinalysis',
        'bmp': 'basic metabolic panel',
        'cmp': 'comprehensive metabolic panel',
        'pt': 'prothrombin time',
        'ptt': 'partial thromboplastin time',
        'inr': 'international normalized ratio',
        'esr': 'erythrocyte sedimentation rate',
        'crp': 'c reactive protein',
        'tsh': 'thyroid stimulating hormone',
        'ft4': 'free thyroxine',
        'hba1c': 'hemoglobin a1c',
        'psa': 'prostate specific antigen',
        'ldl': 'low density lipoprotein',
        'hdl': 'high density lipoprotein',
        'vldl': 'very low density lipoprotein',
        'pk': 'pharmacokinetics',
        'pd': 'pharmacodynamics',
    }
    
    # Common noise words that don't help matching (from B&C project)
    NOISE_WORDS = {
        'please', 'should', 'must', 'will', 'may', 'can', 'could', 'would',
        'study', 'trial', 'visit', 'ensure', 'confirm', 'verify',
        'hand', 'out', 'instruct', 'in', 'use', 'for', 'of', 'the', 'a', 'an',
        'and', 'or', 'but', 'with', 'without', 'register', 'complete', 'perform',
    }
    
    def __init__(self, csv_path: str = None):
        if csv_path is None:
            # Use local project data folder
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, '..', 'data', 'cpp', 'clinical_procedures', 'Reference_Clinical_Procedures_2025_Q2.csv')
        
        self.csv_path = csv_path
        self.procedures = {}
        self.short_desc_to_code = {}
        self.load_procedures()
    
    def load_procedures(self):
        """Load procedures from CSV file"""
        if not os.path.exists(self.csv_path):
            logger.warning(f"⚠️  Procedure reference file not found: {self.csv_path}")
            return
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                
                for row in reader:
                    cpt_code = row.get('CPT_CODE', '').strip()
                    long_desc = row.get('LONG_DESC', '').strip()
                    short_desc = row.get('SHORT_DESC', '').strip()
                    proc_level = row.get('PROCEDURE_LEVEL', '').strip()
                    proc_group = row.get('PROC_GROUP', '').strip()
                    
                    if cpt_code and short_desc:
                        self.procedures[cpt_code] = {
                            'code': cpt_code,
                            'long_desc': long_desc,
                            'short_desc': short_desc,
                            'level': proc_level,
                            'group': proc_group,
                            # Estimate cost based on group (placeholder)
                            'estimated_cost': self._estimate_cost(proc_group, proc_level)
                        }
                        
                        # Index by short description for faster lookup
                        self.short_desc_to_code[short_desc.lower()] = cpt_code
                        
                        # Also index by long description
                        if long_desc:
                            self.short_desc_to_code[long_desc.lower()] = cpt_code
                        
                        # Index common keywords
                        for word in short_desc.lower().split():
                            if len(word) > 3:  # Skip short words
                                if word not in self.short_desc_to_code:
                                    self.short_desc_to_code[word] = cpt_code
                        
                        count += 1
                
                logger.info(f"✅ Loaded {count} procedures from reference data")
                
        except Exception as e:
            logger.error(f"❌ Error loading procedure reference: {e}")
    
    def _estimate_cost(self, proc_group: str, proc_level: str) -> float:
        """
        Estimate procedure cost based on group and level
        These are rough estimates - actual costs should come from pricing data
        """
        # Cost estimates by group
        group_costs = {
            'Laboratory': 100.0,
            'Imaging': 800.0,
            'Cardiac': 500.0,
            'Evaluation and Management Services': 200.0,
            'Questionnaires, Scales and Assessments': 50.0,
            'Procedures': 1500.0,
            'Surgery': 3000.0,
            'Pathology': 400.0,
            'Radiology': 800.0,
            'Anesthesia': 600.0,
        }
        
        base_cost = group_costs.get(proc_group, 250.0)
        
        # Adjust by level
        if proc_level.lower() == 'study':
            base_cost *= 10  # Study-level procedures are much more expensive
        elif proc_level.lower() == 'patient':
            base_cost *= 2  # Patient-level are moderately more expensive
        
        return base_cost
    
    def _normalize_text(self, text: str, apply_enhancements: bool = False) -> str:
        """
        Normalize text for matching (B&C algorithm)
        
        Args:
            text: Raw text to normalize
            apply_enhancements: If True, apply abbreviation expansion and noise removal
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove special characters but keep spaces
        normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Apply enhancements if requested (for two-pass matching)
        if apply_enhancements:
            normalized = self._expand_abbreviations(normalized)
            normalized = self._remove_noise_words(normalized)
        
        return normalized
    
    def _expand_abbreviations(self, text: str) -> str:
        """Expand common medical abbreviations (B&C algorithm)"""
        words = text.split()
        expanded = []
        for word in words:
            if word in self.MEDICAL_ABBREVIATIONS:
                expanded.append(self.MEDICAL_ABBREVIATIONS[word])
            else:
                expanded.append(word)
        return ' '.join(expanded)
    
    def _remove_noise_words(self, text: str) -> str:
        """Remove common noise words that don't help matching (B&C algorithm)"""
        words = [w for w in text.split() if w not in self.NOISE_WORDS]
        return ' '.join(words) if words else text  # Keep original if all words removed
    
    def _apply_length_penalty(self, input_text: str, ontology_text: str, score: float, winning_algo: str) -> float:
        """
        Apply length-aware penalty to prevent single words from matching long phrases at 100%
        (B&C algorithm)
        
        Issues without penalty:
        - "weight" matches "pain on weightbearing" at 100% (substring)
        - "harris" matches "harris rating scale" at 100% (substring)
        """
        # No penalty needed for exact matches or ratio algorithm
        if score >= 99.5 and winning_algo in ['ratio', 'exact']:
            return score
        
        input_len = len(input_text)
        ontology_len = len(ontology_text)
        input_words = input_text.split()
        ontology_words = ontology_text.split()
        
        # Factor 1: Length ratio penalty
        length_ratio = input_len / ontology_len if ontology_len > 0 else 1.0
        
        if length_ratio < 0.5:
            length_penalty = 0.5 + (length_ratio * 0.5)  # 0.5 to 0.75
        elif length_ratio < 0.7:
            length_penalty = 0.7 + (length_ratio * 0.3)  # 0.7 to 0.91
        else:
            length_penalty = 0.9 + (length_ratio * 0.1)  # 0.9 to 1.0
        
        # Factor 2: Word count ratio penalty
        if len(input_words) == 1 and len(ontology_words) >= 3:
            word_count_penalty = 0.6  # Single word matching multi-word phrase
        elif len(input_words) == 1 and len(ontology_words) == 2:
            word_count_penalty = 0.8  # Single word matching two-word phrase
        else:
            word_count_ratio = len(input_words) / len(ontology_words) if len(ontology_words) > 0 else 1.0
            if word_count_ratio < 0.5:
                word_count_penalty = 0.7 + (word_count_ratio * 0.3)
            else:
                word_count_penalty = 0.9 + (word_count_ratio * 0.1)
        
        # Factor 3: Token coverage
        input_tokens_set = set(input_words)
        ontology_tokens_set = set(ontology_words)
        tokens_found = len(input_tokens_set & ontology_tokens_set)
        token_coverage = tokens_found / len(input_tokens_set) if len(input_tokens_set) > 0 else 0
        
        if token_coverage >= 0.8:
            token_penalty = 1.0
        elif token_coverage >= 0.5:
            token_penalty = 0.85
        else:
            token_penalty = 0.7
        
        # Apply combined penalty (use minimum to be conservative)
        combined_penalty = min(length_penalty, word_count_penalty, token_penalty)
        adjusted_score = score * combined_penalty
        
        return adjusted_score
    
    def fuzzy_match(self, procedure_text: str, threshold: float = 40) -> Dict[str, Any]:
        """
        Match procedure using B&C's two-pass composite multi-algorithm strategy
        
        Pass 1: Try with basic normalization
        Pass 2: If score < 70%, try with enhanced text (abbreviations + noise removal)
        
        Uses MAX of 4 algorithms:
        - ratio: Character-level similarity (Levenshtein)
        - partial_ratio: Substring matching
        - token_sort_ratio: Word order invariant
        - token_set_ratio: Set-based matching
        
        Returns best match with confidence score
        """
        # PASS 1: Basic normalization
        normalized = self._normalize_text(procedure_text, apply_enhancements=False)
        
        # Try exact match first
        for cpt_code, proc in self.procedures.items():
            if normalized == self._normalize_text(proc['short_desc'], apply_enhancements=False):
                return {
                    'matched': True,
                    'confidence': 1.0,
                    'code': proc['code'],
                    'short_desc': proc['short_desc'],
                    'long_desc': proc['long_desc'],
                    'group': proc['group'],
                    'estimated_cost': proc['estimated_cost'],
                    'match_type': 'exact'
                }
        
        # Fuzzy matching (pass 1)
        best_match_pass1 = self._fuzzy_match_multi_algo(normalized, threshold)
        
        # PASS 2: Try with enhancements if score is low
        if best_match_pass1 and best_match_pass1['confidence'] < 0.70:
            enhanced = self._normalize_text(procedure_text, apply_enhancements=True)
            if enhanced != normalized:
                logger.debug(f"Pass 2 triggered for '{procedure_text}': '{normalized}' → '{enhanced}'")
                best_match_pass2 = self._fuzzy_match_multi_algo(enhanced, threshold)
                
                # Use pass 2 if better
                if best_match_pass2 and best_match_pass2['confidence'] > best_match_pass1['confidence']:
                    logger.debug(f"Pass 2 improved: {best_match_pass1['confidence']:.0%} → {best_match_pass2['confidence']:.0%}")
                    return best_match_pass2
                else:
                    if best_match_pass2:
                        logger.debug(f"Pass 2 did not improve: {best_match_pass1['confidence']:.0%} vs {best_match_pass2['confidence']:.0%}")
                    else:
                        logger.debug("Pass 2 found no matches")
        
        if best_match_pass1:
            return best_match_pass1
        
        # No match found
        return {
            'matched': False,
            'confidence': 0.0,
            'code': None,
            'short_desc': procedure_text,
            'long_desc': procedure_text,
            'group': 'Unknown',
            'estimated_cost': 0.0,
            'match_type': 'none'
        }
    
    def _fuzzy_match_multi_algo(self, normalized_text: str, threshold: float) -> Dict[str, Any]:
        """
        Perform fuzzy matching using composite multi-algorithm approach (B&C algorithm)
        
        Uses MAX of 4 algorithms with length-aware penalties
        """
        best_match = None
        best_score = 0.0
        winning_algo = None
        
        for cpt_code, proc in self.procedures.items():
            # Normalize reference text
            short_normalized = self._normalize_text(proc['short_desc'], apply_enhancements=False)
            long_normalized = self._normalize_text(proc['long_desc'], apply_enhancements=False)
            
            # Try both short and long descriptions
            for ontology_text in [short_normalized, long_normalized]:
                if not ontology_text:
                    continue
                
                # Calculate all 4 algorithm scores
                ratio_score = fuzz.ratio(normalized_text, ontology_text)
                partial_score = fuzz.partial_ratio(normalized_text, ontology_text)
                token_sort_score = fuzz.token_sort_ratio(normalized_text, ontology_text)
                token_set_score = fuzz.token_set_ratio(normalized_text, ontology_text)
                
                # Use the best score from any algorithm
                raw_score = max(ratio_score, partial_score, token_sort_score, token_set_score)
                
                # Determine which algorithm won
                scores_map = {
                    'ratio': ratio_score,
                    'partial': partial_score,
                    'token_sort': token_sort_score,
                    'token_set': token_set_score
                }
                algo = max(scores_map, key=scores_map.get)
                
                # Apply length-aware penalty
                adjusted_score = self._apply_length_penalty(
                    normalized_text,
                    ontology_text,
                    raw_score,
                    algo
                )
                
                if adjusted_score > best_score and adjusted_score >= threshold:
                    best_score = adjusted_score
                    winning_algo = algo
                    best_match = {
                        'matched': True,
                        'confidence': adjusted_score / 100.0,  # Convert to 0-1 scale
                        'code': proc['code'],
                        'short_desc': proc['short_desc'],
                        'long_desc': proc['long_desc'],
                        'group': proc['group'],
                        'estimated_cost': proc['estimated_cost'],
                        'match_type': f'fuzzy_{algo}'
                    }
        
        return best_match
    
    def get_alternatives(self, procedure_text: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Get alternative procedure matches using B&C multi-algorithm approach
        Returns top N alternatives sorted by score
        """
        normalized = self._normalize_text(procedure_text, apply_enhancements=False)
        
        # Calculate scores for all procedures
        scored_matches = []
        
        for cpt_code, proc in self.procedures.items():
            short_normalized = self._normalize_text(proc['short_desc'], apply_enhancements=False)
            
            # Calculate all 4 algorithm scores
            ratio_score = fuzz.ratio(normalized, short_normalized)
            partial_score = fuzz.partial_ratio(normalized, short_normalized)
            token_sort_score = fuzz.token_sort_ratio(normalized, short_normalized)
            token_set_score = fuzz.token_set_ratio(normalized, short_normalized)
            
            # Use best score
            raw_score = max(ratio_score, partial_score, token_sort_score, token_set_score)
            
            # Determine winning algorithm
            scores_map = {
                'ratio': ratio_score,
                'partial': partial_score,
                'token_sort': token_sort_score,
                'token_set': token_set_score
            }
            algo = max(scores_map, key=scores_map.get)
            
            # Apply length penalty
            adjusted_score = self._apply_length_penalty(normalized, short_normalized, raw_score, algo)
            
            if adjusted_score >= 30:  # Lower threshold for alternatives
                scored_matches.append({
                    'code': proc['code'],
                    'short_desc': proc['short_desc'],
                    'group': proc['group'],
                    'estimated_cost': proc['estimated_cost'],
                    'confidence': adjusted_score / 100.0  # 0-1 scale
                })
        
        # Sort by confidence and return top matches
        scored_matches.sort(key=lambda x: x['confidence'], reverse=True)
        return scored_matches[:max_results]
    
    def get_procedure(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get procedure information by CPT code
        
        Args:
            code: CPT code to look up
            
        Returns:
            Dictionary with procedure information or None if not found
        """
        return self.procedures.get(code)


# Global instance
_procedure_loader = None

def get_procedure_loader() -> ProcedureReferenceLoader:
    """Get or create global procedure loader instance"""
    global _procedure_loader
    if _procedure_loader is None:
        _procedure_loader = ProcedureReferenceLoader()
    return _procedure_loader

