"""
Fuzzy Matching Service
Maps procedure text to standardized codes using fuzzy string matching
"""

import re
from typing import List, Dict, Optional, Tuple
from fuzzywuzzy import fuzz, process
import logging

from models.cpp_models import Procedure, ProcedureMatch
from services.cpp_data_loaders import get_cpp_data_loader

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """
    Fuzzy matcher for procedure text to standardized codes
    
    Uses multiple matching strategies:
    - Exact match
    - Token sort ratio (order-independent)
    - Partial ratio (substring matching)
    - Token set ratio (best for multi-word matches)
    """
    
    # Medical abbreviations expansion
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
        'ivrs': 'interactive voice response system',
        'iwrs': 'interactive web response system',
        'irt': 'interactive response technology',
        'ect': 'electroconvulsive therapy',
        'prn': 'as needed',
        'po': 'by mouth',
        'iv': 'intravenous',
        'im': 'intramuscular',
        'sc': 'subcutaneous',
        'bid': 'twice daily',
        'tid': 'three times daily',
        'qid': 'four times daily',
        'qd': 'once daily',
        'hs': 'at bedtime',
    }
    
    # Noise words to filter out
    NOISE_WORDS = {
        'please', 'should', 'must', 'will', 'may', 'can', 'could', 'would',
        'study', 'trial', 'visit', 'ensure', 'confirm', 'verify',
        'hand', 'out', 'instruct', 'in', 'use', 'for', 'of', 'the', 'a', 'an',
        'and', 'or', 'but', 'with', 'without', 'register', 'complete', 'perform',
        'conduct', 'administer', 'obtain', 'collect', 'record', 'document',
    }
    
    def __init__(self, threshold: float = 70.0, max_alternatives: int = 5):
        """
        Initialize fuzzy matcher
        
        Args:
            threshold: Minimum confidence score (0-100) to consider a match
            max_alternatives: Maximum number of alternative matches to return
        """
        self.threshold = threshold
        self.max_alternatives = max_alternatives
        self.data_loader = get_cpp_data_loader()
        self._build_search_index()
    
    def _build_search_index(self):
        """Build searchable index of procedures"""
        self.search_index = {}
        
        for code, procedure in self.data_loader.clinical_procedures.items():
            # Index by short description
            if procedure.short_description:
                normalized = self._normalize_text(procedure.short_description)
                self.search_index[normalized] = (code, procedure.short_description, 'short')
            
            # Index by long description
            if procedure.long_description:
                normalized = self._normalize_text(procedure.long_description)
                self.search_index[normalized] = (code, procedure.long_description, 'long')
            
            # Index by code itself
            code_normalized = self._normalize_text(code)
            self.search_index[code_normalized] = (code, procedure.short_description, 'code')
        
        logger.info(f"Built search index with {len(self.search_index)} entries")
    
    def match(self, text: str, return_alternatives: bool = True) -> ProcedureMatch:
        """
        Match procedure text to standardized code
        
        Args:
            text: Raw procedure text
            return_alternatives: Whether to return alternative matches
        
        Returns:
            ProcedureMatch with best match and alternatives
        """
        if not text or not text.strip():
            return ProcedureMatch(
                raw_text=text,
                normalized_text="",
                requires_review=True
            )
        
        raw_text = text.strip()
        normalized_text = self._normalize_text(raw_text)
        
        # Try exact match first
        exact_match = self._exact_match(normalized_text)
        if exact_match:
            code, description = exact_match
            return ProcedureMatch(
                raw_text=raw_text,
                normalized_text=normalized_text,
                matched_code=code,
                matched_description=description,
                confidence_score=100.0,
                match_type='exact',
                alternatives=[],
                requires_review=False
            )
        
        # Try fuzzy matching
        matches = self._fuzzy_match(normalized_text)
        
        if not matches:
            return ProcedureMatch(
                raw_text=raw_text,
                normalized_text=normalized_text,
                requires_review=True
            )
        
        # Best match
        best_match = matches[0]
        code, description, score = best_match
        
        # Determine confidence level
        requires_review = score < 90.0
        match_type = 'fuzzy' if score >= 80.0 else 'partial'
        
        # Alternatives
        alternatives = []
        if return_alternatives and len(matches) > 1:
            for alt_code, alt_desc, alt_score in matches[1:self.max_alternatives + 1]:
                alternatives.append({
                    'code': alt_code,
                    'description': alt_desc,
                    'score': alt_score
                })
        
        return ProcedureMatch(
            raw_text=raw_text,
            normalized_text=normalized_text,
            matched_code=code,
            matched_description=description,
            confidence_score=score,
            match_type=match_type,
            alternatives=alternatives,
            requires_review=requires_review
        )
    
    def match_batch(self, texts: List[str]) -> List[ProcedureMatch]:
        """Match multiple procedure texts"""
        return [self.match(text) for text in texts]
    
    def _exact_match(self, normalized_text: str) -> Optional[Tuple[str, str]]:
        """Try exact match in search index"""
        if normalized_text in self.search_index:
            code, description, _ = self.search_index[normalized_text]
            return (code, description)
        return None
    
    def _fuzzy_match(self, normalized_text: str) -> List[Tuple[str, str, float]]:
        """
        Fuzzy match using multiple algorithms
        
        Returns list of (code, description, score) tuples
        """
        # Get all searchable texts
        searchable_texts = list(self.search_index.keys())
        
        if not searchable_texts:
            return []
        
        # Try different matching algorithms
        results = {}
        
        # Token sort ratio (good for word order differences)
        token_sort_matches = process.extract(
            normalized_text,
            searchable_texts,
            scorer=fuzz.token_sort_ratio,
            limit=self.max_alternatives * 2
        )
        
        for match_text, score in token_sort_matches:
            if score >= self.threshold:
                code, description, _ = self.search_index[match_text]
                if code not in results or results[code][1] < score:
                    results[code] = (description, score)
        
        # Token set ratio (good for subset matching)
        token_set_matches = process.extract(
            normalized_text,
            searchable_texts,
            scorer=fuzz.token_set_ratio,
            limit=self.max_alternatives * 2
        )
        
        for match_text, score in token_set_matches:
            if score >= self.threshold:
                code, description, _ = self.search_index[match_text]
                if code not in results or results[code][1] < score:
                    results[code] = (description, score)
        
        # Partial ratio (good for substring matching)
        partial_matches = process.extract(
            normalized_text,
            searchable_texts,
            scorer=fuzz.partial_ratio,
            limit=self.max_alternatives * 2
        )
        
        for match_text, score in partial_matches:
            # Lower threshold for partial matches
            if score >= self.threshold * 0.8:
                code, description, _ = self.search_index[match_text]
                if code not in results:
                    # Boost score slightly if exact substring
                    if normalized_text in match_text or match_text in normalized_text:
                        score = min(score + 5, 100)
                    results[code] = (description, score)
        
        # Convert to list and sort by score
        matches = [(code, desc, score) for code, (desc, score) in results.items()]
        matches.sort(key=lambda x: x[2], reverse=True)
        
        return matches[:self.max_alternatives * 2]
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for matching
        
        - Lowercase
        - Expand abbreviations
        - Remove noise words
        - Remove special characters
        - Normalize whitespace
        """
        if not text:
            return ""
        
        # Lowercase
        text = text.lower().strip()
        
        # Expand abbreviations
        words = text.split()
        expanded_words = []
        for word in words:
            # Remove punctuation for abbreviation matching
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.MEDICAL_ABBREVIATIONS:
                expanded_words.append(self.MEDICAL_ABBREVIATIONS[clean_word])
            elif word not in self.NOISE_WORDS:
                expanded_words.append(word)
        
        text = ' '.join(expanded_words)
        
        # Remove special characters (keep alphanumeric and spaces)
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    def get_confidence_level(self, score: float) -> str:
        """Convert numerical score to confidence level"""
        if score >= 90:
            return "high"
        elif score >= 70:
            return "medium"
        else:
            return "low"


# Global singleton
_fuzzy_matcher = None

def get_fuzzy_matcher() -> FuzzyMatcher:
    """Get or create global fuzzy matcher instance"""
    global _fuzzy_matcher
    if _fuzzy_matcher is None:
        _fuzzy_matcher = FuzzyMatcher(threshold=70.0, max_alternatives=5)
    return _fuzzy_matcher







