"""
Data processing utilities for text extraction, NER, and relevance scoring
"""
import re
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from config import MEDICAL_TERMS
from utils.logger import log_error
from agents.llm_agent import llm_agent

# Fewer LLM round-trips; keep chunks small so each batch prompt stays bounded (~650 chars/snippet in llm_agent).
_RELEVANCE_SCORE_CHUNK = 12


class DataProcessor:
    def __init__(self):
        self.medical_terms_pattern = re.compile(r'\b(' + '|'.join(MEDICAL_TERMS) + r')\b', re.IGNORECASE)
    
    def extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            log_error(e, "HTML text extraction")
            return html_content
    
    def extract_medical_entities(self, text: str) -> List[str]:
        """Extract medical entities using regex patterns"""
        try:
            entities = self.medical_terms_pattern.findall(text)
            return list(set(entities))  # Remove duplicates
        except Exception as e:
            log_error(e, "Medical entity extraction")
            return []
    
    async def calculate_relevance_scores(self, query: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate relevance scores for items using LLM (batched where possible)."""
        try:
            contents: List[str] = []
            item_indices: List[int] = []
            for i, item in enumerate(items):
                content = ""
                if "title" in item:
                    content += item["title"] + " "
                if "description" in item:
                    content += item["description"] + " "
                if "abstract" in item:
                    content += item["abstract"] + " "
                text = content.strip()
                if text:
                    contents.append(text)
                    item_indices.append(i)
                else:
                    item["relevance_score"] = 0.1

            for start in range(0, len(contents), _RELEVANCE_SCORE_CHUNK):
                chunk = contents[start : start + _RELEVANCE_SCORE_CHUNK]
                idx_chunk = item_indices[start : start + _RELEVANCE_SCORE_CHUNK]
                try:
                    scores = await llm_agent.calculate_relevance_scores_batch(query, chunk)
                except Exception as e:
                    log_error(e, "Batch relevance scoring chunk")
                    scores = [0.3] * len(chunk)
                if len(scores) != len(chunk):
                    scores = [0.3] * len(chunk)
                for item_i, sc in zip(idx_chunk, scores):
                    items[item_i]["relevance_score"] = sc

            return items

        except Exception as e:
            log_error(e, "Batch relevance scoring")
            for item in items:
                item["relevance_score"] = 0.3
            return items
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better processing"""
        try:
            # Convert to lowercase
            text = text.lower()
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove special characters but keep medical terms
            text = re.sub(r'[^\w\s\-]', ' ', text)
            
            return text.strip()
        except Exception as e:
            log_error(e, "Text normalization")
            return text
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        try:
            # Normalize text
            normalized_text = self.normalize_text(text)
            
            # Split into words
            words = normalized_text.split()
            
            # Remove common stop words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
            }
            
            # Filter words
            keywords = [word for word in words if len(word) > 2 and word not in stop_words]
            
            # Count frequency
            from collections import Counter
            word_counts = Counter(keywords)
            
            # Return most common keywords
            return [word for word, count in word_counts.most_common(max_keywords)]
            
        except Exception as e:
            log_error(e, "Keyword extraction")
            return []
    
    def filter_by_relevance(self, items: List[Dict[str, Any]], min_score: float = 0.3) -> List[Dict[str, Any]]:
        """Filter items by relevance score"""
        try:
            return [item for item in items if item.get("relevance_score", 0) >= min_score]
        except Exception as e:
            log_error(e, "Relevance filtering")
            return items
    
    def sort_by_relevance(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort items by relevance score (descending)"""
        try:
            return sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True)
        except Exception as e:
            log_error(e, "Relevance sorting")
            return items
    
    def deduplicate_results(self, items: List[Dict[str, Any]], key_field: str = "title") -> List[Dict[str, Any]]:
        """Remove duplicate items based on a key field"""
        try:
            seen = set()
            unique_items = []
            
            for item in items:
                key = item.get(key_field, "").lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    unique_items.append(item)
            
            return unique_items
        except Exception as e:
            log_error(e, "Result deduplication")
            return items
    
    def format_results(self, items: List[Dict[str, Any]], max_length: int = 200) -> List[Dict[str, Any]]:
        """Format results for consistent output"""
        try:
            formatted_items = []
            
            for item in items:
                formatted_item = item.copy()
                
                # Truncate long text fields
                for field in ["title", "description", "abstract"]:
                    if field in formatted_item and formatted_item[field]:
                        text = formatted_item[field]
                        if len(text) > max_length:
                            formatted_item[field] = text[:max_length] + "..."
                
                # Ensure all required fields exist
                if "relevance_score" not in formatted_item:
                    formatted_item["relevance_score"] = 0.5
                
                formatted_items.append(formatted_item)
            
            return formatted_items
        except Exception as e:
            log_error(e, "Result formatting")
            return items
    
    async def process_search_results(self, query: str, results: Dict[str, List]) -> Dict[str, List]:
        """Process and enhance search results"""
        try:
            processed_results = {}
            
            for source, items in results.items():
                if not items:
                    processed_results[source] = []
                    continue
                
                # Convert items to dictionaries if they're Pydantic models
                items_dict = []
                for item in items:
                    if hasattr(item, 'dict'):
                        items_dict.append(item.dict())
                    else:
                        items_dict.append(item)
                
                # Calculate relevance scores
                scored_items = await self.calculate_relevance_scores(query, items_dict)
                
                # Filter by relevance
                filtered_items = self.filter_by_relevance(scored_items)
                
                # Sort by relevance
                sorted_items = self.sort_by_relevance(filtered_items)
                
                # Deduplicate
                unique_items = self.deduplicate_results(sorted_items)
                
                # Format results
                formatted_items = self.format_results(unique_items)
                
                processed_results[source] = formatted_items
            
            return processed_results
            
        except Exception as e:
            log_error(e, "Search results processing")
            return results

# Global data processor instance
data_processor = DataProcessor() 