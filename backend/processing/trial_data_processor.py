"""
Trial Data Processor for HITL Integration
Handles data standardization and conversion between different trial formats
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from models.schemas import (
    ClinicalTrialResult, 
    UnifiedTrialResult, 
    TrialSuggestion, 
    TrialSelectionState
)
from agents.llm_agent import llm_agent
import logging

logger = logging.getLogger(__name__)

class TrialDataProcessor:
    """Processes and standardizes trial data from different sources"""
    
    def __init__(self):
        self.scoring_weights = {
            "query_relevance": 0.4,
            "therapeutic_area": 0.2,
            "phase_appropriateness": 0.15,
            "study_quality": 0.1,
            "recency": 0.1,
            "geographic_relevance": 0.05
        }
    
    def _safe_json_dumps(self, obj, indent=2):
        """Safely serialize objects to JSON, handling non-serializable objects"""
        try:
            return json.dumps(obj, indent=indent, default=str)
        except Exception as e:
            # Fallback to string representation
            return str(obj)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (conservative approximation: 1 token ≈ 3 characters)"""
        if not text:
            return 0
        # Conservative estimation to account for JSON formatting, whitespace, etc.
        return int(len(str(text)) / 3)
    
    def _truncate_json_data(self, json_str: str, target_tokens: int) -> str:
        """Truncate JSON data to fit within token limit"""
        try:
            # Parse JSON to understand structure
            data = json.loads(json_str)
            
            if isinstance(data, list):
                # Calculate how many items to keep
                current_tokens = self._estimate_tokens(json_str)
                if current_tokens <= target_tokens:
                    return json_str
                
                # Estimate tokens per item
                if len(data) > 0:
                    tokens_per_item = current_tokens / len(data)
                    target_items = max(1, int(target_tokens / tokens_per_item))
                    
                    # Keep the first N items
                    truncated_data = data[:target_items]
                    
                    # Add truncation info
                    truncated_data.append({
                        "truncation_info": f"Data truncated from {len(data)} to {len(truncated_data)} items to prevent token limit exceeded",
                        "original_count": len(data),
                        "truncated_count": len(truncated_data)
                    })
                    
                    return self._safe_json_dumps(truncated_data)
            
            elif isinstance(data, dict):
                # For dict, truncate string values
                truncated_data = {}
                remaining_tokens = target_tokens
                
                for key, value in data.items():
                    if isinstance(value, str):
                        value_tokens = self._estimate_tokens(value)
                        if value_tokens <= remaining_tokens:
                            truncated_data[key] = value
                            remaining_tokens -= value_tokens
                        else:
                            # Truncate the string value
                            target_length = int(len(value) * (remaining_tokens / value_tokens))
                            truncated_data[key] = value[:target_length] + "..."
                            break
                    else:
                        truncated_data[key] = value
                
                return self._safe_json_dumps(truncated_data)
            
            return json_str
            
        except Exception as e:
            # If JSON parsing fails, do simple string truncation
            target_length = int(len(json_str) * (target_tokens / self._estimate_tokens(json_str)))
            return json_str[:target_length] + "..."
    
    def _emergency_truncate_trials(self, trials_json: str) -> str:
        """Emergency truncation for trials - keep only essential fields"""
        try:
            data = json.loads(trials_json)
            if isinstance(data, list):
                # Keep only first 20 trials with minimal fields
                emergency_trials = []
                for trial in data[:20]:
                    if isinstance(trial, dict):
                        emergency_trial = {
                            'nct_id': trial.get('nct_id', ''),
                            'title': trial.get('title', '')[:100] + '...' if len(trial.get('title', '')) > 100 else trial.get('title', ''),
                            'condition': trial.get('condition', ''),
                            'phase': trial.get('phase', ''),
                            'status': trial.get('status', ''),
                            'enrollment': trial.get('enrollment', 0)
                        }
                        emergency_trials.append(emergency_trial)
                
                emergency_trials.append({
                    "emergency_truncation": f"Trials truncated to {len(emergency_trials)} items with minimal fields for token limit"
                })
                
                return self._safe_json_dumps(emergency_trials)
            return trials_json
        except Exception:
            return '[]'
    
    def _emergency_truncate_context(self, context_json: str) -> str:
        """Emergency truncation for context - keep only essential information"""
        try:
            data = json.loads(context_json)
            if isinstance(data, dict):
                emergency_context = {
                    'query': data.get('query', ''),
                    'execution_results': {
                        'summary': 'Context truncated for token limit - execution results available but truncated'
                    }
                }
                return self._safe_json_dumps(emergency_context)
            return context_json
        except Exception:
            return '{}'
    
    async def process_trial_data(self, source: str, raw_data: List[Any]) -> List[UnifiedTrialResult]:
        """Convert all trial data to unified format"""
        unified_trials = []
        
        for trial in raw_data:
            try:
                unified_trial = await self._convert_to_unified(trial, source)
                unified_trials.append(unified_trial)
            except Exception as e:
                logger.error(f"Error converting trial data: {e}")
                continue
        
        return unified_trials
    
    async def _convert_to_unified(self, trial: Any, source: str) -> UnifiedTrialResult:
        """Convert any trial format to unified format"""
        
        if isinstance(trial, ClinicalTrialResult):
            # ClinicalTrialResult object
            return UnifiedTrialResult.from_clinical_trial_result(trial, source)
        
        elif isinstance(trial, dict):
            # Dictionary format
            return UnifiedTrialResult.from_dict(trial, source)
        
        elif hasattr(trial, 'nct_id'):
            # Object with nct_id attribute
            return UnifiedTrialResult(
                nct_id=getattr(trial, 'nct_id', ''),
                title=getattr(trial, 'title', ''),
                condition=getattr(trial, 'condition', None),
                intervention=getattr(trial, 'intervention', None),
                sponsor=getattr(trial, 'sponsor', None),
                status=getattr(trial, 'status', None),
                phase=getattr(trial, 'phase', None),
                enrollment=getattr(trial, 'enrollment', None),
                start_date=getattr(trial, 'start_date', None),
                completion_date=getattr(trial, 'completion_date', None),
                description=getattr(trial, 'description', None),
                location=getattr(trial, 'location', None),
                source=source,
                relevance_score=getattr(trial, 'relevance_score', None),
                inclusion_criteria=getattr(trial, 'inclusion_criteria', None),
                exclusion_criteria=getattr(trial, 'exclusion_criteria', None),
                primary_endpoints=getattr(trial, 'primary_endpoints', None),
                secondary_endpoints=getattr(trial, 'secondary_endpoints', None),
                study_type=getattr(trial, 'study_type', None),
                allocation=getattr(trial, 'allocation', None),
                masking=getattr(trial, 'masking', None),
                primary_purpose=getattr(trial, 'primary_purpose', None),
                study_population=getattr(trial, 'study_population', None),
                metadata=getattr(trial, 'metadata', {}) or {}
            )
        
        else:
            raise ValueError(f"Unsupported trial data format: {type(trial)}")
    
    async def score_trials(self, trials: List[UnifiedTrialResult], query: str, context: Dict[str, Any]) -> List[UnifiedTrialResult]:
        """Score trials using AI-driven multi-criteria analysis"""
        
        if not trials:
            return trials
        
        # Prepare trial data for scoring
        trial_summaries = []
        for trial in trials[:50]:  # Limit to top 50 for LLM processing
            summary = {
                'nct_id': trial.nct_id,
                'title': trial.title[:100] + '...' if len(trial.title) > 100 else trial.title,
                'condition': trial.condition or 'Unknown',
                'phase': trial.phase or 'Unknown',
                'status': trial.status or 'Unknown',
                'enrollment': trial.enrollment or 0,
                'sponsor': trial.sponsor or 'Unknown',
                'start_date': trial.start_date,
                'source': trial.source
            }
            trial_summaries.append(summary)
        
        # Apply token limiting to prevent LLM errors
        context_json = self._safe_json_dumps(context)
        trials_json = self._safe_json_dumps(trial_summaries)
        
        # Estimate token usage
        query_tokens = self._estimate_tokens(query)
        context_tokens = self._estimate_tokens(context_json)
        trials_tokens = self._estimate_tokens(trials_json)
        instruction_tokens = 500  # Estimated tokens for instructions
        
        total_tokens = query_tokens + context_tokens + trials_tokens + instruction_tokens
        
        print(f"🔍 Pre-truncation token estimation for trial scoring:")
        print(f"   Query: {query_tokens:,} tokens")
        print(f"   Context: {context_tokens:,} tokens")
        print(f"   Trials: {trials_tokens:,} tokens")
        print(f"   Instructions: {instruction_tokens:,} tokens")
        print(f"   Total: {total_tokens:,} tokens")
        
        # Apply token limiting to prevent LLM errors (target: 180,000 tokens to stay close to 200,000 limit)
        if total_tokens > 180000:
            print(f"⚠️ Token limit exceeded ({total_tokens:,} > 180,000), applying truncation...")
            
            # Calculate reduction factor
            reduction_factor = 180000 / total_tokens
            print(f"📉 Reduction factor: {reduction_factor:.2f}")
            
            # Truncate trials data first (most likely culprit)
            if trials_tokens > 100000:
                target_trials_tokens = int(trials_tokens * reduction_factor)
                trials_json = self._truncate_json_data(trials_json, target_trials_tokens)
                trials_tokens = self._estimate_tokens(trials_json)
                print(f"📊 Trials truncated to {trials_tokens:,} tokens")
            
            # Truncate context if still needed
            new_total = query_tokens + self._estimate_tokens(context_json) + trials_tokens + instruction_tokens
            if new_total > 180000:
                context_reduction = 180000 / new_total
                target_context_tokens = int(self._estimate_tokens(context_json) * context_reduction)
                context_json = self._truncate_json_data(context_json, target_context_tokens)
                print(f"📊 Context truncated to {self._estimate_tokens(context_json):,} tokens")
            
            # Final check and emergency truncation if still too large
            final_check = query_tokens + self._estimate_tokens(context_json) + self._estimate_tokens(trials_json) + instruction_tokens
            if final_check > 190000:
                print(f"🚨 Emergency truncation needed - still {final_check:,} tokens")
                # Emergency truncation - keep only essential data
                emergency_trials_json = self._emergency_truncate_trials(trials_json)
                emergency_context_json = self._emergency_truncate_context(context_json)
                trials_json = emergency_trials_json
                context_json = emergency_context_json
                print(f"🚨 Emergency truncation applied")
        
        final_total = query_tokens + self._estimate_tokens(context_json) + self._estimate_tokens(trials_json) + instruction_tokens
        print(f"📏 Final scoring prompt estimated at {final_total:,} tokens")
        
        if final_total > 195000:
            print(f"⚠️ Warning: Prompt size ({final_total:,} tokens) is very close to limit (200,000 tokens)")
        else:
            print(f"✅ Prompt size ({final_total:,} tokens) is within safe limits")
        
        # Generate AI scoring
        scoring_prompt = f"""
        Score these clinical trials for relevance to the query using multiple criteria:
        
        QUERY: {query}
        CONTEXT: {context_json}
        
        TRIALS: {trials_json}
        
        Score each trial (0-100) on:
        1. Query Relevance (40%): How well does the trial match the search query?
        2. Therapeutic Area Match (20%): How well does it match the TA context?
        3. Phase Appropriateness (15%): Is the phase suitable for the query context?
        4. Study Quality (10%): Document quality, sponsor reputation, enrollment size
        5. Recency (10%): How recent is the trial?
        6. Geographic Relevance (5%): Does location match requirements?
        
        Return ONLY a valid JSON array with scores and explanations. Do not include any other text or formatting:
        [
            {{
                "nct_id": "NCT12345678",
                "total_score": 85,
                "scores": {{
                    "query_relevance": 90,
                    "therapeutic_area": 80,
                    "phase_appropriateness": 85,
                    "study_quality": 75,
                    "recency": 90,
                    "geographic_relevance": 80
                }},
                "explanation": "High relevance due to exact condition match and appropriate phase"
            }}
        ]
        """
        
        try:
            # Use simple text generation instead of structured response
            response = await llm_agent.generate_response(scoring_prompt)
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                scoring_results = json.loads(json_str)
            else:
                raise ValueError("No JSON array found in response")
            
            # Apply scores to trials
            scored_trials = []
            for trial in trials:
                # Find matching score result
                score_result = next(
                    (s for s in scoring_results if s['nct_id'] == trial.nct_id), 
                    None
                )
                
                if score_result:
                    # Update trial with scores
                    trial.relevance_score = score_result['total_score']
                    trial.selection_reason = score_result['explanation']
                    trial.scores = score_result['scores']
                else:
                    # Default scoring if not found
                    trial.relevance_score = 50.0
                    trial.selection_reason = "Standard relevance scoring applied"
                    trial.scores = {
                        "query_relevance": 50,
                        "therapeutic_area": 50,
                        "phase_appropriateness": 50,
                        "study_quality": 50,
                        "recency": 50,
                        "geographic_relevance": 50
                    }
                
                scored_trials.append(trial)
            
            # Sort by total score
            scored_trials.sort(key=lambda t: t.relevance_score or 0, reverse=True)
            
            # Normalize scores for better visualization
            normalized_trials = self._normalize_scores(scored_trials)
            
            return normalized_trials
            
        except Exception as e:
            logger.error(f"Error scoring trials: {e}")
            # Return trials with default scores
            for trial in trials:
                trial.relevance_score = 50.0
                trial.selection_reason = "Default scoring applied due to error"
                trial.scores = {key: 50.0 for key in self.scoring_weights.keys()}
            return trials
    
    def _normalize_scores(self, trials: List[UnifiedTrialResult]) -> List[UnifiedTrialResult]:
        """Normalize scores to improve visualization spread"""
        if not trials:
            return trials
        
        # Extract all scores for normalization
        all_scores = [trial.relevance_score for trial in trials if trial.relevance_score is not None]
        if not all_scores:
            return trials
        
        # Calculate min and max scores
        min_score = min(all_scores)
        max_score = max(all_scores)
        
        # Avoid division by zero
        if max_score == min_score:
            return trials
        
        # Normalize scores to 0-100 range with better spread
        for trial in trials:
            if trial.relevance_score is not None:
                # Normalize to 0-1 range first
                normalized = (trial.relevance_score - min_score) / (max_score - min_score)
                
                # Apply sigmoid-like transformation for better spread
                # This creates more differentiation in the middle range
                if normalized < 0.5:
                    # Lower half: compress towards 0-50
                    normalized = normalized * normalized * 2
                else:
                    # Upper half: expand towards 50-100
                    normalized = 0.5 + (normalized - 0.5) * (normalized - 0.5) * 2
                
                # Scale to 0-100 range
                trial.relevance_score = round(normalized * 100, 1)
                
                # Also normalize individual score components if they exist
                if hasattr(trial, 'scores') and trial.scores:
                    normalized_scores = {}
                    for score_key, score_value in trial.scores.items():
                        if isinstance(score_value, (int, float)):
                            # Normalize individual scores using the same method
                            if score_value is not None:
                                norm_val = (score_value - min_score) / (max_score - min_score)
                                if norm_val < 0.5:
                                    norm_val = norm_val * norm_val * 2
                                else:
                                    norm_val = 0.5 + (norm_val - 0.5) * (norm_val - 0.5) * 2
                                normalized_scores[score_key] = round(norm_val * 100, 1)
                            else:
                                normalized_scores[score_key] = score_value
                    trial.scores = normalized_scores
        
        return trials
    
    async def generate_suggestions(self, trials: List[UnifiedTrialResult], query: str, context: Dict[str, Any]) -> List[TrialSuggestion]:
        """Generate AI-driven trial suggestions"""
        
        # Score trials first
        scored_trials = await self.score_trials(trials, query, context)
        
        # Generate suggestions for top trials
        suggestions = []
        for i, trial in enumerate(scored_trials[:5]):
            suggestion = TrialSuggestion(
                trial=trial,
                suggestion_rank=i + 1,
                explanation=trial.selection_reason or "AI-recommended based on relevance scoring",
                confidence_score=min(1.0, (trial.relevance_score or 0) / 100.0)
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def deduplicate_trials(self, trials: List[UnifiedTrialResult]) -> List[UnifiedTrialResult]:
        """Remove duplicate trials based on NCT ID"""
        seen = set()
        unique_trials = []
        
        for trial in trials:
            if trial.nct_id not in seen:
                seen.add(trial.nct_id)
                unique_trials.append(trial)
        
        return unique_trials
    
    def filter_trials(self, trials: List[UnifiedTrialResult], filters: Dict[str, Any]) -> List[UnifiedTrialResult]:
        """Filter trials based on criteria"""
        filtered_trials = trials
        
        if filters.get('phase'):
            filtered_trials = [t for t in filtered_trials if t.phase == filters['phase']]
        
        if filters.get('sponsor'):
            sponsor_filter = filters['sponsor'].lower()
            filtered_trials = [t for t in filtered_trials if t.sponsor and sponsor_filter in t.sponsor.lower()]
        
        if filters.get('min_score'):
            min_score = float(filters['min_score'])
            filtered_trials = [t for t in filtered_trials if (t.relevance_score or 0) >= min_score]
        
        if filters.get('status'):
            filtered_trials = [t for t in filtered_trials if t.status == filters['status']]
        
        return filtered_trials

class TrialSelectionManager:
    """Manages HITL trial selection process"""
    
    def __init__(self):
        self.processor = TrialDataProcessor()
        self.active_selections: Dict[str, TrialSelectionState] = {}
        self.timeout_duration = 300  # 5 minutes
    
    async def create_selection_state(self, execution_id: str, query: str, 
                                   trials: List[Any], source: str, 
                                   context: Dict[str, Any]) -> TrialSelectionState:
        """Create a new trial selection state"""
        
        # Process and standardize trial data
        unified_trials = await self.processor.process_trial_data(source, trials)
        
        # Remove duplicates
        unique_trials = self.processor.deduplicate_trials(unified_trials)
        
        # Generate AI suggestions
        suggestions = await self.processor.generate_suggestions(unique_trials, query, context)
        
        # Create selection state
        timeout_datetime = datetime.now().timestamp() + self.timeout_duration
        selection_state = TrialSelectionState(
            execution_id=execution_id,
            query=query,
            total_trials=len(unique_trials),
            suggestions=suggestions,
            all_trials=unique_trials,
            timeout_at=datetime.fromtimestamp(timeout_datetime).isoformat()
        )
        
        # Store state
        self.active_selections[execution_id] = selection_state
        
        return selection_state
    
    async def complete_selection(self, execution_id: str, selected_nct_ids: List[str]) -> TrialSelectionState:
        """Complete trial selection with human choices"""
        
        if execution_id not in self.active_selections:
            raise ValueError(f"Selection state {execution_id} not found")
        
        selection_state = self.active_selections[execution_id]
        
        # Update selected trials
        selection_state.selected_trials = selected_nct_ids
        selection_state.status = "completed"
        selection_state.completed_at = datetime.now().isoformat()
        
        # Mark trials as selected
        for trial in selection_state.all_trials:
            trial.is_selected = trial.nct_id in selected_nct_ids
            if trial.is_selected:
                trial.selection_timestamp = datetime.now().isoformat()
        
        return selection_state
    
    def get_selection_state(self, execution_id: str) -> Optional[TrialSelectionState]:
        """Get current selection state"""
        return self.active_selections.get(execution_id)
    
    def cleanup_expired_selections(self):
        """Clean up expired selection states"""
        current_time = datetime.now().timestamp()
        expired_ids = []
        
        for execution_id, state in self.active_selections.items():
            if state.timeout_at and datetime.fromisoformat(state.timeout_at).timestamp() < current_time:
                expired_ids.append(execution_id)
        
        for execution_id in expired_ids:
            state = self.active_selections.pop(execution_id)
            state.status = "timeout"
            logger.info(f"Selection state {execution_id} expired and was cleaned up")
    
    def get_selected_trials(self, execution_id: str) -> List[UnifiedTrialResult]:
        """Get the selected trials for an execution"""
        state = self.get_selection_state(execution_id)
        if not state:
            return []
        
        return [trial for trial in state.all_trials if trial.nct_id in state.selected_trials]
