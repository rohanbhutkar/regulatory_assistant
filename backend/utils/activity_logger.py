"""
Activity Logger - Emits structured activity events to WebSocket for frontend visibility
"""
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum

from utils.websocket_manager import note_broadcast_task

class OperationType(str, Enum):
    """Types of operations that can be tracked"""
    AI_GENERATION = "ai_generation"
    DATA_SEARCH = "data_search"
    SIMULATION = "simulation"
    EVIDENCE_DISCOVERY = "evidence_discovery"
    BUDGET_CALC = "budget_calc"
    SITE_FILTERING = "site_filtering"
    POPULATION_ANALYSIS = "population_analysis"
    PRICING_CALC = "pricing_calc"
    HTA_ASSESSMENT = "hta_assessment"

class OperationStatus(str, Enum):
    """Status of an operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"

class ActivityEventType(str, Enum):
    """Types of activity events"""
    OPERATION_START = "operation_start"
    OPERATION_PROGRESS = "operation_progress"
    OPERATION_COMPLETE = "operation_complete"
    OPERATION_ERROR = "operation_error"
    OPERATION_CANCELLED = "operation_cancelled"
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"

class ActivityLogger:
    """Structured activity logger that emits events to WebSocket"""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
        self.active_operations: Dict[str, Dict[str, Any]] = {}
    
    def set_websocket_manager(self, websocket_manager):
        """Set the WebSocket manager for broadcasting events"""
        self.websocket_manager = websocket_manager
    
    def start_operation(
        self,
        operation_type: OperationType,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None
    ) -> str:
        """
        Start tracking a new operation
        
        Returns operation_id for tracking
        """
        if operation_id is None:
            operation_id = f"{operation_type.value}_{uuid.uuid4().hex[:8]}"
        
        operation = {
            "id": operation_id,
            "type": operation_type.value,
            "context": context or {},
            "status": OperationStatus.PENDING.value,
            "progress": 0.0,
            "current_step": "",
            "steps": [],
            "start_time": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.active_operations[operation_id] = operation
        
        # Emit start event
        self._emit_event(
            ActivityEventType.OPERATION_START,
            operation_id,
            operation_type.value,
            context,
            step="Initializing",
            progress=0.0,
            message=f"Starting {operation_type.value.replace('_', ' ').title()}",
            metadata=metadata
        )
        
        return operation_id
    
    def update_progress(
        self,
        operation_id: str,
        progress: float,
        step: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update operation progress"""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        operation["status"] = OperationStatus.IN_PROGRESS.value
        operation["progress"] = max(0.0, min(100.0, progress))
        
        if step:
            operation["current_step"] = step
            # Add step to steps list if not already there
            step_exists = any(s.get("name") == step for s in operation["steps"])
            if not step_exists:
                operation["steps"].append({
                    "name": step,
                    "status": "in_progress",
                    "start_time": datetime.now().isoformat()
                })
        
        if metadata:
            operation["metadata"].update(metadata)
        
        # Emit progress event
        self._emit_event(
            ActivityEventType.OPERATION_PROGRESS,
            operation_id,
            operation["type"],
            operation.get("context"),
            step=step or operation["current_step"],
            progress=progress,
            message=message or f"Processing: {step or 'In progress'}",
            metadata=metadata
        )
    
    def start_step(
        self,
        operation_id: str,
        step_name: str,
        message: Optional[str] = None
    ):
        """Mark a step as started"""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        operation["current_step"] = step_name
        
        # Add or update step
        step_exists = False
        for s in operation["steps"]:
            if s.get("name") == step_name:
                s["status"] = "in_progress"
                s["start_time"] = datetime.now().isoformat()
                step_exists = True
                break
        
        if not step_exists:
            operation["steps"].append({
                "name": step_name,
                "status": "in_progress",
                "start_time": datetime.now().isoformat()
            })
        
        self._emit_event(
            ActivityEventType.STEP_START,
            operation_id,
            operation["type"],
            operation.get("context"),
            step=step_name,
            progress=operation["progress"],
            message=message or f"Starting: {step_name}",
            metadata={}
        )
    
    def complete_step(
        self,
        operation_id: str,
        step_name: str,
        message: Optional[str] = None
    ):
        """Mark a step as completed"""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        
        # Update step status
        for s in operation["steps"]:
            if s.get("name") == step_name:
                s["status"] = "completed"
                s["end_time"] = datetime.now().isoformat()
                if "start_time" in s:
                    start = datetime.fromisoformat(s["start_time"])
                    end = datetime.now()
                    s["duration"] = (end - start).total_seconds()
                break
        
        self._emit_event(
            ActivityEventType.STEP_COMPLETE,
            operation_id,
            operation["type"],
            operation.get("context"),
            step=step_name,
            progress=operation["progress"],
            message=message or f"Completed: {step_name}",
            metadata={}
        )
    
    def complete_operation(
        self,
        operation_id: str,
        result: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """Mark operation as completed"""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        operation["status"] = OperationStatus.COMPLETED.value
        operation["progress"] = 100.0
        operation["end_time"] = datetime.now().isoformat()
        
        if result:
            operation["metadata"]["result"] = result
        
        # Calculate total duration
        start = datetime.fromisoformat(operation["start_time"])
        end = datetime.now()
        operation["duration"] = (end - start).total_seconds()
        
        # Mark all steps as completed
        for s in operation["steps"]:
            if s.get("status") == "in_progress":
                s["status"] = "completed"
                s["end_time"] = datetime.now().isoformat()
        
        self._emit_event(
            ActivityEventType.OPERATION_COMPLETE,
            operation_id,
            operation["type"],
            operation.get("context"),
            step=operation["current_step"],
            progress=100.0,
            message=message or f"Completed {operation['type'].replace('_', ' ').title()}",
            metadata={"result": result} if result else {}
        )
        
        # Clean up after a delay (keep for 5 minutes for frontend to sync)
        # In production, might want to persist to database
    
    def error_operation(
        self,
        operation_id: str,
        error: str,
        error_details: Optional[Dict[str, Any]] = None
    ):
        """Mark operation as error"""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        operation["status"] = OperationStatus.ERROR.value
        operation["end_time"] = datetime.now().isoformat()
        operation["error"] = error
        operation["metadata"]["error_details"] = error_details or {}
        
        self._emit_event(
            ActivityEventType.OPERATION_ERROR,
            operation_id,
            operation["type"],
            operation.get("context"),
            step=operation["current_step"],
            progress=operation["progress"],
            message=f"Error: {error}",
            metadata={"error": error, "error_details": error_details}
        )
    
    def cancel_operation(
        self,
        operation_id: str,
        reason: Optional[str] = None
    ):
        """Cancel an operation"""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        operation["status"] = OperationStatus.CANCELLED.value
        operation["end_time"] = datetime.now().isoformat()
        operation["metadata"]["cancellation_reason"] = reason
        
        self._emit_event(
            ActivityEventType.OPERATION_CANCELLED,
            operation_id,
            operation["type"],
            operation.get("context"),
            step=operation["current_step"],
            progress=operation["progress"],
            message=reason or "Operation cancelled",
            metadata={"reason": reason}
        )
    
    def _emit_event(
        self,
        event_type: ActivityEventType,
        operation_id: str,
        operation_type: str,
        context: Optional[Dict[str, Any]],
        step: str,
        progress: float,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Emit event to WebSocket if manager is available"""
        event = {
            "type": "activity_event",
            "event_type": event_type.value,
            "operation_id": operation_id,
            "operation_type": operation_type,
            "context": context or {},
            "step": step,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Broadcast to all connected clients via WebSocket manager
        if self.websocket_manager:
            try:
                # Get operation details if available
                if operation_id in self.active_operations:
                    operation = self.active_operations[operation_id]
                    event["operation"] = {
                        "id": operation["id"],
                        "type": operation["type"],
                        "status": operation["status"],
                        "progress": operation["progress"],
                        "current_step": operation["current_step"],
                        "steps": operation["steps"],
                        "start_time": operation["start_time"],
                        "end_time": operation.get("end_time"),
                        "duration": operation.get("duration")
                    }
                
                # Schedule async broadcast without blocking
                # broadcast_activity_event is async, so we need to schedule it as a task
                try:
                    # Try to get the running event loop
                    loop = asyncio.get_running_loop()
                    # Schedule the coroutine as a task (fire and forget)
                    # This will execute the coroutine without blocking
                    task = loop.create_task(self.websocket_manager.broadcast_activity_event(event))
                    note_broadcast_task(task)
                except RuntimeError:
                    # No running event loop - this can happen in sync contexts
                    # The event will still be logged, just not broadcast via WebSocket
                    # This is expected in some contexts where there's no async event loop
                    pass
            except Exception as e:
                # Don't fail if WebSocket is not available
                print(f"Warning: Could not broadcast activity event: {e}")
    
    def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get operation details"""
        return self.active_operations.get(operation_id)
    
    def get_active_operations(self, context: Optional[Dict[str, Any]] = None) -> list:
        """Get all active operations, optionally filtered by context"""
        operations = list(self.active_operations.values())
        
        if context:
            filtered = []
            for op in operations:
                op_context = op.get("context", {})
                # Match if all context keys match
                if all(op_context.get(k) == v for k, v in context.items()):
                    filtered.append(op)
            return filtered
        
        return operations

# Global instance
activity_logger = ActivityLogger()
