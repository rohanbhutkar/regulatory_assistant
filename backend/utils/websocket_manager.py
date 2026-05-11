from fastapi import WebSocket
from typing import Dict, List, Optional, Any
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_progress: Dict[str, Dict] = {}
        self.activity_subscriptions: Dict[str, List[Any]] = {}  # client_id -> list of operation_ids or contexts
        self.pending_activity_events: Dict[str, List[Dict]] = {}  # client_id -> list of queued events
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected")
        # Send any pending activity events
        await self.send_pending_events(client_id)
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.agent_progress:
            del self.agent_progress[client_id]
        print(f"Client {client_id} disconnected")
    
    async def handle_message(self, client_id: str, message: str):
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'query':
                await self._handle_query(client_id, data)
            elif message_type == 'simulation':
                await self._handle_simulation(client_id, data)
            elif message_type == 'ping':
                await self._send_message(client_id, {'type': 'pong'})
        except Exception as e:
            await self._send_error(client_id, str(e))
    
    async def _handle_query(self, client_id: str, data: Dict):
        """Handle research agent queries with real data processing"""
        query_data = data.get('data', {})
        query = query_data.get('query', '')
        conversation_history = query_data.get('conversation_history', [])
        
        # Send progress update
        await self._send_progress(client_id, {
            'step': 'Processing query',
            'progress': 10,
            'message': f'Analyzing query: {query[:50]}...'
        })
        
        try:
            # Process query with real data
            response_content = await self._process_real_query(query)
            
            # Send final response
            await self._send_message(client_id, {
                'type': 'query_completed',
                'data': {
                    'query': query,
                    'synthesis': {
                        'answer': response_content,
                        'citations': [],
                        'confidence': 0.85,
                        'data_quality': 'good'
                    },
                    'processing_time': 1.0
                }
            })
        except Exception as e:
            await self._send_error(client_id, f'Query processing failed: {str(e)}')
    
    async def _process_real_query(self, query: str) -> str:
        """Process query with real data from TrialTrove, SiteTrove, etc."""
        try:
            query_lower = query.lower()
            
            # Handle diabetes-related queries
            if "diabetes" in query_lower or "diabetic" in query_lower:
                return await self._process_diabetes_query(query)
            
            # Handle trial selection queries
            if "select" in query_lower and "trial" in query_lower:
                return await self._process_trial_selection_query(query)
            
            # Handle general trial queries
            if "trial" in query_lower:
                return await self._process_trial_query(query)
            
            # Handle site queries
            if "site" in query_lower:
                return await self._process_site_query(query)
            
            # Default response
            return f"I've processed your query: '{query}'. I can help you search clinical trials, analyze research sites, or explore population data. What would you like to know more about?"
            
        except Exception as e:
            print(f"Error processing real query: {e}")
            return f"I encountered an error processing your query: {str(e)}"
    
    async def _process_diabetes_query(self, query: str) -> str:
        """Process diabetes-related queries with real TrialTrove data"""
        try:
            # Get the global data loader from main.py
            from main import data_loader
            
            # Search for diabetes trials in TrialTrove data
            diabetes_trials = []
            trialtrove_data = data_loader.get_data('trialtrove')
            if not trialtrove_data.empty:
                for _, trial in trialtrove_data.iterrows():
                    trial_text = str(trial).lower()
                    if "diabetes" in trial_text or "diabetic" in trial_text:
                        diabetes_trials.append(trial.to_dict())
            
            if diabetes_trials:
                # Get some key statistics
                phases = {}
                statuses = {}
                sponsors = {}
                
                for trial in diabetes_trials[:100]:  # Limit to first 100 for performance
                    phase = trial.get('phase', 'Unknown')
                    status = trial.get('status', 'Unknown')
                    sponsor = trial.get('sponsor', 'Unknown')
                    
                    phases[phase] = phases.get(phase, 0) + 1
                    statuses[status] = statuses.get(status, 0) + 1
                    sponsors[sponsor] = sponsors.get(sponsor, 0) + 1
                
                # Get top sponsors
                top_sponsors = sorted(sponsors.items(), key=lambda x: x[1], reverse=True)[:5]
                
                response = f"""I found **{len(diabetes_trials)} diabetes-related clinical trials** in our database! Here's what I discovered:

## 📊 **Diabetes Trial Overview**
- **Total Trials Found**: {len(diabetes_trials)}
- **Database Coverage**: {len(trialtrove_data)} total trials

## 🔬 **Phase Distribution**
{chr(10).join([f"- **{phase}**: {count} trials" for phase, count in phases.items()])}

## 📈 **Status Breakdown**
{chr(10).join([f"- **{status}**: {count} trials" for status, count in statuses.items()])}

## 🏢 **Top Sponsors**
{chr(10).join([f"- **{sponsor}**: {count} trials" for sponsor, count in top_sponsors])}

## 🎯 **Sample Diabetes Trials**
"""
                
                # Add sample trials
                for i, trial in enumerate(diabetes_trials[:5]):
                    title = trial.get('trial_name', 'Unnamed Trial')
                    nct_id = trial.get('nct_id', 'N/A')
                    phase = trial.get('phase', 'Unknown')
                    status = trial.get('status', 'Unknown')
                    indication = trial.get('indication', 'Unknown')
                    
                    response += f"""
**{i+1}. {title}**
- **NCT ID**: {nct_id}
- **Phase**: {phase}
- **Status**: {status}
- **Indication**: {indication}
"""
                
                response += f"""

Would you like me to:
- **Filter by specific phase** (Phase I, II, III, IV)?
- **Focus on active trials** only?
- **Analyze specific diabetes types** (Type 1, Type 2, gestational)?
- **Look at enrollment criteria** for these trials?

Just let me know what aspect of diabetes trials you'd like to explore further!"""
                
                return response
            else:
                return f"I searched our database of {len(trialtrove_data)} trials but didn't find specific diabetes-related trials. This might be due to data formatting or search terms. Try asking about specific diabetes types or phases."
                
        except Exception as e:
            print(f"Error processing diabetes query: {e}")
            return f"I encountered an error while searching for diabetes trials: {str(e)}"
    
    async def _process_trial_selection_query(self, query: str) -> str:
        """Process trial selection queries"""
        try:
            # Extract key terms from query
            query_lower = query.lower()
            
            # Get the global data loader from main.py
            from main import data_loader
            
            # Search for relevant trials
            relevant_trials = []
            trialtrove_data = data_loader.get_data('trialtrove')
            if not trialtrove_data.empty:
                for _, trial in trialtrove_data.iterrows():
                    trial_text = str(trial).lower()
                    if any(term in trial_text for term in query_lower.split()):
                        relevant_trials.append(trial.to_dict())
            
            if relevant_trials:
                return f"I found **{len(relevant_trials)} relevant trials** for your query. You can now select specific trials from the Reference Trials tab to use as references for your study design."
            else:
                return f"I searched our database but didn't find trials matching your criteria. Try using more specific terms or browse the Reference Trials tab to explore available trials."
                
        except Exception as e:
            print(f"Error processing trial selection query: {e}")
            return f"I encountered an error while processing your trial selection query: {str(e)}"
    
    async def _process_trial_query(self, query: str) -> str:
        """Process general trial queries"""
        try:
            from main import data_loader
            trialtrove_data = data_loader.get_data('trialtrove')
            total_trials = len(trialtrove_data)
            return f"I can help you explore our database of **{total_trials:,} clinical trials**. Use the Reference Trials tab to search and filter trials by phase, status, therapeutic area, or other criteria."
        except Exception as e:
            print(f"Error processing trial query: {e}")
            return f"I encountered an error while processing your trial query: {str(e)}"
    
    async def _process_site_query(self, query: str) -> str:
        """Process site-related queries"""
        try:
            from main import data_loader
            sitetrove_data = data_loader.get_data('sitetrove')
            total_sites = len(sitetrove_data)
            return f"I can help you explore our database of **{total_sites:,} research sites**. Use the Site Selection tab to find optimal sites for your study based on performance, location, and enrollment potential."
        except Exception as e:
            print(f"Error processing site query: {e}")
            return f"I encountered an error while processing your site query: {str(e)}"
    
    async def _handle_simulation(self, client_id: str, data: Dict):
        """Handle simulation requests"""
        simulation_type = data.get('simulation_type')
        params = data.get('params', {})
        
        await self._send_progress(client_id, {
            'step': 'Initializing simulation',
            'progress': 5,
            'message': f'Starting {simulation_type} simulation'
        })
        
        try:
            # Simulate simulation processing
            for i in range(10):
                await asyncio.sleep(0.5)
                progress = 5 + (i * 9)
                await self._send_progress(client_id, {
                    'step': f'Simulation step {i+1}',
                    'progress': progress,
                    'message': f'Processing {simulation_type} simulation...'
                })
            
            # Mock results
            results = {
                'simulation_type': simulation_type,
                'results': {
                    'total_cost': 1500000,
                    'enrollment_time': 18,
                    'success_probability': 0.78
                },
                'parameters': params
            }
            
            await self._send_message(client_id, {
                'type': 'simulation_complete',
                'results': results,
                'simulation_type': simulation_type
            })
        except Exception as e:
            await self._send_error(client_id, f'Simulation failed: {str(e)}')
    
    async def _send_message(self, client_id: str, message: Dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
    
    async def _send_progress(self, client_id: str, progress: Dict):
        await self._send_message(client_id, {
            'type': 'progress_update',
            'progress': progress
        })
    
    async def _send_error(self, client_id: str, error: str):
        await self._send_message(client_id, {
            'type': 'error',
            'error': error
        })
    
    async def broadcast_activity_event(self, event: Dict[str, Any]):
        """Broadcast activity event to all connected clients or specific subscribers"""
        event_json = json.dumps(event)
        
        # Broadcast to all connected clients
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                # Check if client is subscribed to this operation/context
                subscriptions = self.activity_subscriptions.get(client_id, [])
                should_send = True
                
                # If client has subscriptions, check if event matches
                if subscriptions:
                    operation_id = event.get("operation_id")
                    context = event.get("context", {})
                    should_send = False
                    
                    # Check if subscribed to this operation_id or context
                    for sub in subscriptions:
                        if isinstance(sub, str):
                            # Subscription to specific operation_id
                            if sub == operation_id:
                                should_send = True
                                break
                        elif isinstance(sub, dict):
                            # Subscription to context (e.g., {"asset_id": "asset-1"})
                            if all(context.get(k) == v for k, v in sub.items()):
                                should_send = True
                                break
                    # If no subscriptions, send to all (default behavior)
                    if not subscriptions:
                        should_send = True
                
                if should_send:
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_text(event_json)
                    else:
                        # Queue event for when client reconnects
                        if client_id not in self.pending_activity_events:
                            self.pending_activity_events[client_id] = []
                        self.pending_activity_events[client_id].append(event)
            except Exception as e:
                logger.debug("Error broadcasting activity event to %s: %s", client_id, e)
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def subscribe_to_activity(self, client_id: str, subscription: str | Dict[str, Any]):
        """Subscribe client to specific operation or context"""
        if client_id not in self.activity_subscriptions:
            self.activity_subscriptions[client_id] = []
        self.activity_subscriptions[client_id].append(subscription)
    
    def unsubscribe_from_activity(self, client_id: str, subscription: str | Dict[str, Any] = None):
        """Unsubscribe client from activity events"""
        if subscription is None:
            # Unsubscribe from all
            self.activity_subscriptions.pop(client_id, None)
        else:
            # Unsubscribe from specific subscription
            if client_id in self.activity_subscriptions:
                self.activity_subscriptions[client_id] = [
                    s for s in self.activity_subscriptions[client_id] if s != subscription
                ]
    
    async def send_pending_events(self, client_id: str):
        """Send pending activity events to reconnected client"""
        if client_id in self.pending_activity_events:
            events = self.pending_activity_events[client_id]
            for event in events:
                try:
                    await self._send_message(client_id, event)
                except Exception as e:
                    print(f"Error sending pending event to {client_id}: {e}")
            # Clear pending events
            del self.pending_activity_events[client_id]
    
    async def broadcast_log_event(self, log_entry: Dict[str, Any]):
        """Broadcast log entry to all connected clients"""
        event = {
            "type": "log_event",
            "log": log_entry
        }
        event_json = json.dumps(event)
        
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                if websocket.client_state.name == "CONNECTED":
                    await websocket.send_text(event_json)
            except Exception as e:
                logger.debug("Error broadcasting log event to %s: %s", client_id, e)
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

