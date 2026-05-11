"""
Human-in-the-Loop Trial Selection Agent
Integrates with the dynamic reasoning engine as a first-class agent
"""
import asyncio
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.schemas import (
    ClinicalTrialResult, 
    UnifiedTrialResult, 
    TrialSuggestion, 
    TrialSelectionState
)
from processing.trial_data_processor import TrialDataProcessor
from agents.llm_agent import llm_agent
import logging

logger = logging.getLogger(__name__)

class HITLAgent:
    """Human-in-the-Loop Agent for trial selection"""
    
    def __init__(self):
        self.name = "hitl_trial_selection"
        self.description = "Human-in-the-loop trial selection with AI suggestions"
        self.trial_processor = TrialDataProcessor()
        self.active_selections: Dict[str, TrialSelectionState] = {}
        self.timeout_duration = 300  # 5 minutes
        self.pending_selections: Dict[str, asyncio.Future] = {}
    
    async def process_request(self, query: str, context: Dict[str, Any], 
                            max_results: int = 50, progress_callback=None, node_id: str = None) -> Dict[str, Any]:
        """Process HITL request - main agent interface"""
        
        logger.info(f"process_request called with query: {query[:50]}...")
        
        try:
            # Extract trial data from context
            trials = self._extract_trials_from_context(context)
            
            logger.info(f"Extracted {len(trials)} trials from context")
            
            if not trials:
                return {
                    "status": "error",
                    "message": "No trials found in context for HITL selection",
                    "trials": [],
                    "execution_id": None
                }
            
            # Limit trials if too many
            if len(trials) > max_results:
                trials = trials[:max_results]
            
            # Create selection state
            execution_id = self._generate_execution_id()
            selection_state = await self._create_selection_state(
                execution_id, query, trials, context
            )
            
            # Store pending selection
            self.active_selections[execution_id] = selection_state
            self.pending_selections[execution_id] = asyncio.Future()
            
            # Send HITL request to frontend
            await self._send_hitl_request(execution_id, selection_state, progress_callback, node_id)
            
            logger.info(f"HITL request sent, waiting for human selection...")
            
            # Wait for human selection (with timeout)
            try:
                logger.info(f"Starting wait for human selection for execution {execution_id}")
                logger.info(f"   Wait start timestamp: {datetime.now().isoformat()}")
                
                selected_trials = await asyncio.wait_for(
                    self._wait_for_selection(execution_id),
                    timeout=self.timeout_duration
                )
                
                logger.info(f"Human selection received for execution {execution_id}")
                logger.info(f"   Selected trials: {selected_trials}")
                logger.info(f"   Selection timestamp: {datetime.now().isoformat()}")
                
                return {
                    "status": "completed",
                    "execution_id": execution_id,
                    "selected_trials": selected_trials,
                    "total_trials": len(trials),
                    "selection_reason": "Human-selected trials based on AI suggestions",
                    "suggestions_used": len(selection_state.suggestions)
                }
                
            except asyncio.TimeoutError:
                # Timeout - use AI suggestions as fallback
                logger.warning(f"HITL selection timed out for execution {execution_id}")
                logger.warning(f"   Timeout timestamp: {datetime.now().isoformat()}")
                fallback_trials = self._get_fallback_selection(selection_state)
                
                return {
                    "status": "timeout_fallback",
                    "execution_id": execution_id,
                    "selected_trials": fallback_trials,
                    "total_trials": len(trials),
                    "selection_reason": "AI suggestions used due to timeout",
                    "suggestions_used": len(selection_state.suggestions)
                }
                
        except Exception as e:
            logger.error(f"Error in HITL agent: {e}")
            return {
                "status": "error",
                "message": f"HITL agent error: {str(e)}",
                "trials": [],
                "execution_id": None
            }
    
    def _extract_trials_from_context(self, context: Dict[str, Any]) -> List[UnifiedTrialResult]:
        """Extract trials from previous node results"""
        trials = []
        
        # Look for trial data in execution results
        execution_results = context.get("execution_results", {})
        
        for node_id, results in execution_results.items():
            if isinstance(results, list):
                for result in results:
                    try:
                        if isinstance(result, dict) and "nct_id" in result:
                            # Convert to unified format
                            trial = UnifiedTrialResult.from_dict(result, "context")
                            trials.append(trial)
                        elif hasattr(result, 'nct_id'):
                            # Already a trial object
                            trial = UnifiedTrialResult.from_clinical_trial_result(result, "context")
                            trials.append(trial)
                    except Exception as e:
                        logger.warning(f"Error extracting trial from result: {e}")
                        continue
        
        return trials
    
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        return f"hitl_{uuid.uuid4().hex[:8]}"
    
    async def _create_selection_state(self, execution_id: str, query: str, 
                                    trials: List[UnifiedTrialResult], 
                                    context: Dict[str, Any]) -> TrialSelectionState:
        """Create selection state with AI suggestions"""
        
        # Remove duplicates
        unique_trials = self.trial_processor.deduplicate_trials(trials)
        
        # Generate AI suggestions
        suggestions = await self.trial_processor.generate_suggestions(
            unique_trials, query, context
        )
        
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
        
        return selection_state
    
    async def _send_hitl_request(self, execution_id: str, 
                               selection_state: TrialSelectionState, progress_callback=None, node_id: str = None):
        """Send HITL request to frontend via WebSocket"""
        
        logger.info(f"_send_hitl_request called for execution {execution_id}")
        
        try:
            # Convert trials to JSON-serializable format
            suggestions_data = []
            for s in selection_state.suggestions:
                try:
                    if hasattr(s, 'model_dump'):
                        suggestions_data.append(s.model_dump())
                    else:
                        suggestions_data.append(s.dict() if hasattr(s, 'dict') else str(s))
                except Exception as e:
                    logger.warning(f"Error serializing suggestion: {e}")
                    suggestions_data.append({"error": "Serialization failed"})
            
            all_trials_data = []
            for t in selection_state.all_trials:
                try:
                    if hasattr(t, 'model_dump'):
                        all_trials_data.append(t.model_dump())
                    else:
                        all_trials_data.append(t.dict() if hasattr(t, 'dict') else str(t))
                except Exception as e:
                    logger.warning(f"Error serializing trial: {e}")
                    all_trials_data.append({"error": "Serialization failed"})
            
            # Create HITL message with required progress callback fields
            hitl_message = {
                "type": "hitl_trial_selection_request",
                "node_id": node_id or "hitl_trial_selection",
                "node_type": "hitl_trial_selection",
                "status": "hitl_request",
                "execution_id": execution_id,
                "suggestions": suggestions_data,
                "all_trials": all_trials_data,
                "total_trials": selection_state.total_trials,
                "timeout_seconds": self.timeout_duration,
                "query": selection_state.query,
                "start_time": selection_state.created_at,
                "end_time": None,
                "description": "Human-in-the-loop trial selection request",
                "error": ""
            }
            
            logger.info(f"Sending HITL request for execution {execution_id}")
            
            # Send via progress callback if available
            if progress_callback:
                try:
                    await progress_callback(hitl_message)
                    logger.info(f"✅ HITL request sent successfully via progress callback")
                except Exception as e:
                    logger.error(f"❌ Error sending HITL request via progress callback: {e}")
            else:
                logger.warning(f"⚠️ No progress callback available for HITL request")
            
        except Exception as e:
            logger.error(f"Error in HITL agent: {e}")
            # Continue execution even if WebSocket sending fails
    
    def handle_human_selection(self, execution_id: str, selected_trials: List[str]) -> bool:
        """Handle human selection response from frontend"""
        
        logger.info(f"handle_human_selection called for execution {execution_id}")
        logger.info(f"   Selected trials: {selected_trials}")
        logger.info(f"   Timestamp: {datetime.now().isoformat()}")
        
        if execution_id not in self.pending_selections:
            logger.warning(f"No pending selection found for execution {execution_id}")
            logger.warning(f"   Available pending selections: {list(self.pending_selections.keys())}")
            return False
        
        try:
            # Complete the future with the selected trials
            future = self.pending_selections[execution_id]
            if not future.done():
                future.set_result(selected_trials)
                logger.info(f"Human selection completed for execution {execution_id}: {len(selected_trials)} trials")
                logger.info(f"   Completion timestamp: {datetime.now().isoformat()}")
                return True
            else:
                logger.warning(f"Future already completed for execution {execution_id}")
                return False
        except Exception as e:
            logger.error(f"Error handling human selection: {e}")
            logger.error(f"   Error timestamp: {datetime.now().isoformat()}")
            return False
    
    async def _wait_for_selection(self, execution_id: str) -> List[str]:
        """Wait for human selection with timeout"""
        
        logger.info(f"_wait_for_selection called for execution {execution_id}")
        logger.info(f"   Wait start timestamp: {datetime.now().isoformat()}")
        
        if execution_id not in self.pending_selections:
            raise ValueError(f"No pending selection for execution {execution_id}")
        
        # Wait for the future to be completed
        logger.info(f"Waiting for future completion for execution {execution_id}")
        selected_trials = await self.pending_selections[execution_id]
        
        logger.info(f"Future completed for execution {execution_id}")
        logger.info(f"   Selected trials: {selected_trials}")
        logger.info(f"   Completion timestamp: {datetime.now().isoformat()}")
        
        # Clean up
        del self.pending_selections[execution_id]
        logger.info(f"Cleaned up pending selection for execution {execution_id}")
        
        return selected_trials
    
    def _get_fallback_selection(self, selection_state: TrialSelectionState) -> List[str]:
        """Get fallback selection using AI suggestions"""
        
        # Use top 3 AI suggestions as fallback
        fallback_trials = []
        for suggestion in selection_state.suggestions[:3]:
            fallback_trials.append(suggestion.trial.nct_id)
        
        return fallback_trials
    
    async def handle_selection_response(self, execution_id: str, 
                                      selected_trials: List[str]) -> bool:
        """Handle selection response from frontend"""
        
        if execution_id not in self.pending_selections:
            logger.warning(f"Received selection response for unknown execution {execution_id}")
            return False
        
        if execution_id not in self.active_selections:
            logger.warning(f"Received selection response for unknown state {execution_id}")
            return False
        
        try:
            # Complete the selection
            selection_state = self.active_selections[execution_id]
            selection_state.selected_trials = selected_trials
            selection_state.status = "completed"
            selection_state.completed_at = datetime.now().isoformat()
            
            # Mark trials as selected
            for trial in selection_state.all_trials:
                trial.is_selected = trial.nct_id in selected_trials
                if trial.is_selected:
                    trial.selection_timestamp = datetime.now().isoformat()
            
            # Complete the future
            future = self.pending_selections[execution_id]
            if not future.done():
                future.set_result(selected_trials)
            
            logger.info(f"Selection completed for execution {execution_id}: {len(selected_trials)} trials")
            return True
            
        except Exception as e:
            logger.error(f"Error handling selection response: {e}")
            return False
    
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
            # Complete any pending futures with timeout
            if execution_id in self.pending_selections:
                future = self.pending_selections[execution_id]
                if not future.done():
                    future.set_exception(asyncio.TimeoutError())
                del self.pending_selections[execution_id]
            
            # Remove from active selections
            state = self.active_selections.pop(execution_id)
            state.status = "timeout"
            logger.info(f"Selection state {execution_id} expired and was cleaned up")
    
    async def search_studies(self, query: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Agent interface method - delegates to process_request"""
        
        # This method is called by the dynamic reasoning engine
        # We need to extract context from the current execution state
        context = {
            "execution_results": {},  # Will be populated by DRE
            "query": query
        }
        
        result = await self.process_request(query, context, max_results)
        
        if result["status"] == "completed":
            # Convert selected trials back to ClinicalTrialResult format
            selected_trials = []
            selection_state = self.get_selection_state(result["execution_id"])
            
            if selection_state:
                for trial in selection_state.all_trials:
                    if trial.nct_id in result["selected_trials"]:
                        # Convert UnifiedTrialResult back to ClinicalTrialResult
                        clinical_trial = ClinicalTrialResult(
                            nct_id=trial.nct_id,
                            title=trial.title,
                            condition=trial.condition,
                            intervention=trial.intervention,
                            sponsor=trial.sponsor,
                            status=trial.status,
                            phase=trial.phase,
                            enrollment=trial.enrollment,
                            start_date=trial.start_date,
                            completion_date=trial.completion_date,
                            description=trial.description,
                            location=trial.location,
                            relevance_score=trial.relevance_score,
                            metadata=trial.metadata
                        )
                        selected_trials.append(clinical_trial)
            
            return selected_trials
        else:
            # Return empty list on error or timeout
            return []

# Global HITL agent instance
hitl_agent = HITLAgent()
