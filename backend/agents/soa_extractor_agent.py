"""
Schedule of Activities (SoA) Extraction Agent
Uses protocol-table-extractor-llm to extract SoA tables from clinical trial protocols
"""
import asyncio
import os
import tempfile
import psutil
import gc
import signal
import time
import re
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from models.schemas import SoATableResult, ProtocolMetadata
from utils.logger import log_query, log_performance, log_error
from utils.cache import cache_manager

# Extraction modes
ExtractionMode = Literal["soa_only", "general_only", "all_tables", "toc_only", "auto"]

class AdaptiveMemoryManager:
    """Adaptive memory manager that adjusts thresholds based on available system RAM"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._emergency_cleanup_in_progress = False
        self._setup_adaptive_thresholds()
        self.process = psutil.Process()
    
    def _setup_adaptive_thresholds(self):
        """Set memory thresholds based on available system RAM"""
        try:
            total_ram_gb = psutil.virtual_memory().total / (1024**3)
            
            if total_ram_gb >= 32:  # 32GB+ systems
                self.max_memory_percent = 85.0
                self.max_memory_gb = 20.0
                self.warning_memory_percent = 75.0
                self.warning_memory_gb = 15.0
            elif total_ram_gb >= 16:  # 16-32GB systems
                self.max_memory_percent = 80.0
                self.max_memory_gb = 12.0
                self.warning_memory_percent = 70.0
                self.warning_memory_gb = 10.0
            elif total_ram_gb >= 8:  # 8-16GB systems
                self.max_memory_percent = 75.0
                self.max_memory_gb = 6.0
                self.warning_memory_percent = 65.0
                self.warning_memory_gb = 5.0
            else:  # <8GB systems
                self.max_memory_percent = 70.0
                self.max_memory_gb = 4.0
                self.warning_memory_percent = 60.0
                self.warning_memory_gb = 3.0
            
            print(f"💾 Adaptive Memory Manager initialized:")
            print(f"  - System RAM: {total_ram_gb:.1f} GB")
            print(f"  - Max memory: {self.max_memory_percent:.1f}% ({self.max_memory_gb:.1f} GB)")
            print(f"  - Warning threshold: {self.warning_memory_percent:.1f}% ({self.warning_memory_gb:.1f} GB)")
            
        except Exception as e:
            print(f"⚠️  Could not determine system RAM, using conservative defaults: {e}")
            # Conservative defaults
            self.max_memory_percent = 70.0
            self.max_memory_gb = 4.0
            self.warning_memory_percent = 60.0
            self.warning_memory_gb = 3.0
    
    def check_memory_usage(self) -> Dict[str, float]:
        """Check current memory usage with thread safety"""
        try:
            with self._lock:
                memory_info = self.process.memory_info()
                memory_percent = self.process.memory_percent()
                memory_gb = memory_info.rss / (1024**3)
                
                return {
                    'percent': memory_percent,
                    'gb': memory_gb,
                    'mb': memory_gb * 1024,
                    'limit_percent': self.max_memory_percent,
                    'limit_gb': self.max_memory_gb,
                    'warning_percent': self.warning_memory_percent,
                    'warning_gb': self.warning_memory_gb
                }
        except Exception as e:
            print(f"⚠️ Memory check failed: {e}")
            return {'percent': 0, 'gb': 0, 'mb': 0, 'limit_percent': 100, 'limit_gb': 100, 'warning_percent': 80, 'warning_gb': 80}
    
    def is_memory_safe(self) -> bool:
        """Check if memory usage is within safe limits"""
        try:
            usage = self.check_memory_usage()
            return (usage['percent'] < self.max_memory_percent and 
                   usage['gb'] < self.max_memory_gb)
        except Exception:
            return True  # Assume safe if check fails
    
    def is_memory_warning(self) -> bool:
        """Check if memory usage is approaching limits"""
        try:
            usage = self.check_memory_usage()
            return (usage['percent'] >= self.warning_memory_percent or 
                   usage['gb'] >= self.warning_memory_gb)
        except Exception:
            return False
    
    def force_garbage_collection(self):
        """Force garbage collection to free memory"""
        try:
            with self._lock:
                collected = gc.collect()
                print(f"🧹 Garbage collection freed {collected} objects")
        except Exception as e:
            print(f"⚠️ Garbage collection failed: {e}")
    
    def log_memory_status(self, context: str = ""):
        """Log current memory status"""
        try:
            usage = self.check_memory_usage()
            status_icon = "🟢" if usage['percent'] < self.warning_memory_percent else "🟡" if usage['percent'] < self.max_memory_percent else "🔴"
            print(f"{status_icon} Memory Status {context}: {usage['percent']:.1f}% ({usage['gb']:.2f}GB)")
            
            if self.is_memory_warning():
                print(f"⚠️  Memory usage approaching limits - consider cleanup")
            if not self.is_memory_safe():
                print(f"🚨 Memory usage exceeds safe limits!")
                
        except Exception as e:
            print(f"⚠️ Memory status logging failed: {e}")
    
    def emergency_cleanup(self, context: str = ""):
        """Perform emergency cleanup with recursion protection"""
        if self._emergency_cleanup_in_progress:
            print(f"⚠️  Emergency cleanup already in progress, skipping recursive call")
            return
        
        try:
            with self._lock:
                if self._emergency_cleanup_in_progress:
                    return
                self._emergency_cleanup_in_progress = True
            
            print(f"🧹 Performing emergency cleanup {context}...")
            
            # Force garbage collection multiple times
            for i in range(3):
                try:
                    collected = gc.collect()
                    print(f"  Round {i+1}: Freed {collected} objects")
                    time.sleep(0.1)  # Brief pause between rounds
                except Exception as e:
                    print(f"  Round {i+1} failed: {e}")
            
            # Log final memory status
            self.log_memory_status("After Emergency Cleanup")
            print(f"✅ Emergency cleanup completed")
            
        except Exception as e:
            print(f"⚠️  Emergency cleanup failed: {e}")
        finally:
            with self._lock:
                self._emergency_cleanup_in_progress = False

class EnhancedTimeoutManager:
    """Enhanced timeout manager with better crash prevention"""
    
    def __init__(self, default_timeout: float = 600.0):
        self.default_timeout = default_timeout
        self._active_tasks = set()
        self._lock = threading.Lock()
    
    async def with_timeout(self, coro, timeout: float = None, context: str = ""):
        """Execute coroutine with timeout protection and task tracking"""
        if timeout is None:
            timeout = self.default_timeout
        
        task_id = id(coro)
        
        try:
            with self._lock:
                self._active_tasks.add(task_id)
            
            print(f"⏱️  Starting {context} with {timeout}s timeout (Task ID: {task_id})")
            
            # Create a wrapper that handles cleanup
            async def wrapped_coro():
                try:
                    return await coro
                except Exception as e:
                    print(f"❌ {context} failed: {e}")
                    raise
                finally:
                    with self._lock:
                        self._active_tasks.discard(task_id)
            
            result = await asyncio.wait_for(wrapped_coro(), timeout=timeout)
            print(f"✅ {context} completed within timeout")
            return result
            
        except asyncio.TimeoutError:
            print(f"⏰ {context} timed out after {timeout}s")
            with self._lock:
                self._active_tasks.discard(task_id)
            raise TimeoutError(f"{context} timed out after {timeout}s")
        except Exception as e:
            print(f"❌ {context} failed: {e}")
            with self._lock:
                self._active_tasks.discard(task_id)
            raise
    
    def cancel_all_tasks(self):
        """Cancel all active timeout-managed tasks"""
        with self._lock:
            active_count = len(self._active_tasks)
            self._active_tasks.clear()
        print(f"🛑 Cancelled {active_count} active timeout-managed tasks")

class ExtractionModeDetector:
    """Intelligently detects the appropriate extraction mode based on user query"""
    
    def __init__(self):
        # Keywords for different extraction modes
        self.mode_keywords = {
            "soa_only": [
                "schedule of activities", "soa", "schedule", "activities", "visit schedule",
                "assessment timeline", "procedures", "timeline", "visits", "assessments"
            ],
            "general_only": [
                "general tables", "all tables", "tables", "table extraction", "extract tables",
                "protocol tables", "study tables", "data tables", "information tables"
            ],
            "toc_only": [
                "table of contents", "toc", "contents", "index", "structure", "outline",
                "document structure", "protocol structure", "study structure"
            ],
            "all_tables": [
                "everything", "all", "complete", "full extraction", "extract all",
                "comprehensive", "both", "soa and general", "soa + general"
            ]
        }
    
    def detect_extraction_mode(self, query: str) -> ExtractionMode:
        """Detect the appropriate extraction mode from user query"""
        query_lower = query.lower()
        
        # Count keyword matches for each mode
        mode_scores = {}
        for mode, keywords in self.mode_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            mode_scores[mode] = score
        
        # Find the mode with highest score
        best_mode = max(mode_scores.items(), key=lambda x: x[1])
        
        if best_mode[1] > 0:
            print(f"🎯 Detected extraction mode: {best_mode[0]} (score: {best_mode[1]})")
            return best_mode[0]
        else:
            # Default to auto if no clear preference
            print("🎯 No clear extraction mode detected, using auto mode")
            return "auto"
    
    def get_extraction_description(self, mode: ExtractionMode) -> str:
        """Get human-readable description of extraction mode"""
        descriptions = {
            "soa_only": "Schedule of Activities tables only",
            "general_only": "General protocol tables only (exclusions, endpoints, etc.)",
            "toc_only": "Table of Contents and document structure only",
            "all_tables": "All tables (SOA + General)",
            "auto": "Automatic mode selection based on content analysis"
        }
        return descriptions.get(mode, "Unknown mode")

class SoAExtractorAgent:
    """Agent for extracting Schedule of Activities tables from protocol PDFs"""
    
    def __init__(self):
        self.extractor = None
        self.lazy_extractor = None
        self.memory_manager = AdaptiveMemoryManager()
        self.timeout_manager = EnhancedTimeoutManager()
        self.mode_detector = ExtractionModeDetector()
        self._emergency_exit_requested = False
        self._initialize_extractors()
        self._temp_dir = Path(tempfile.gettempdir()) / "soa_extraction"
        self._temp_dir.mkdir(exist_ok=True)
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Set up signal handlers to prevent segmentation faults"""
        try:
            # Handle SIGSEGV (segmentation fault)
            signal.signal(signal.SIGSEGV, self._handle_segmentation_fault)
            
            # Handle SIGABRT (abort)
            signal.signal(signal.SIGABRT, self._handle_abort)
            
            # Handle SIGTERM (termination)
            signal.signal(signal.SIGTERM, self._handle_termination)
            
            # Handle SIGINT (interrupt) for graceful shutdown
            signal.signal(signal.SIGINT, self._handle_interrupt)
            
            print("🛡️  Enhanced signal handlers configured for crash prevention")
        except Exception as e:
            print(f"⚠️  Signal handler setup failed: {e}")
    
    def _handle_segmentation_fault(self, signum, frame):
        """Handle segmentation fault gracefully with recursion protection"""
        if self._emergency_exit_requested:
            print(f"🚨 Emergency exit already requested, forcing immediate exit")
            os._exit(1)
        
        self._emergency_exit_requested = True
        print(f"🚨 Segmentation fault detected (signal {signum})")
        
        try:
            # Cancel all timeout-managed tasks
            self.timeout_manager.cancel_all_tasks()
            
            # Perform emergency cleanup
            self.memory_manager.emergency_cleanup("Segmentation Fault")
            
            # Force exit after cleanup
            print(f"🚨 Forcing exit after segmentation fault cleanup")
            os._exit(1)
        except Exception as e:
            print(f"🚨 Emergency cleanup failed during segmentation fault: {e}")
            os._exit(1)
    
    def _handle_abort(self, signum, frame):
        """Handle abort signal gracefully"""
        if self._emergency_exit_requested:
            os._exit(1)
        
        self._emergency_exit_requested = True
        print(f"🚨 Abort signal detected (signal {signum})")
        
        try:
            self.timeout_manager.cancel_all_tasks()
            self.memory_manager.emergency_cleanup("Abort Signal")
            print(f"🚨 Forcing exit after abort signal cleanup")
            os._exit(1)
        except Exception as e:
            print(f"🚨 Emergency cleanup failed during abort: {e}")
            os._exit(1)
    
    def _handle_termination(self, signum, frame):
        """Handle termination signal gracefully"""
        if self._emergency_exit_requested:
            os._exit(0)
        
        self._emergency_exit_requested = True
        print(f"🔄 Termination signal detected (signal {signum})")
        
        try:
            self.timeout_manager.cancel_all_tasks()
            self.memory_manager.emergency_cleanup("Termination Signal")
            print(f"🔄 Graceful shutdown completed")
            os._exit(0)
        except Exception as e:
            print(f"🚨 Emergency cleanup failed during termination: {e}")
            os._exit(0)
    
    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signal for graceful shutdown"""
        if self._emergency_exit_requested:
            print(f"🔄 Interrupt signal received during emergency exit")
            return
        
        print(f"🔄 Interrupt signal received, initiating graceful shutdown")
        self._emergency_exit_requested = True
        
        try:
            self.timeout_manager.cancel_all_tasks()
            self.memory_manager.emergency_cleanup("Interrupt Signal")
            print(f"🔄 Graceful shutdown completed")
            os._exit(0)
        except Exception as e:
            print(f"🚨 Emergency cleanup failed during interrupt: {e}")
            os._exit(0)
    
    def _initialize_extractors(self):
        """Initialize the extractors with enhanced memory protection"""
        try:
            # Check memory before initialization
            self.memory_manager.log_memory_status("Before Extractor Init")
            
            if self.memory_manager.is_memory_warning():
                print("⚠️  Memory usage high before initialization, forcing cleanup")
                self.memory_manager.force_garbage_collection()
            
            # Try to import from the protocol-table-extractor-llm package (optional dependency)
            import sys
            lib_path = Path(__file__).parent.parent / "protocol-table-extractor-llm" / "lib"
            
            # Check if the external library exists
            if not lib_path.exists():
                raise ImportError("protocol-table-extractor-llm library not found (optional dependency)")
            
            sys.path.append(str(lib_path))
            
            # Initialize integrated graph extractor (for SOA-specific extraction)
            from integrated_graph_extractor import IntegratedGraphExtractor
            self.extractor = IntegratedGraphExtractor()
            
            # Initialize lazy LangGraph extractor (for comprehensive table extraction)
            from lazy_langgraph_extractor import LazyLangGraphExtractor
            self.lazy_extractor = LazyLangGraphExtractor()
            
            # Check memory after initialization
            self.memory_manager.log_memory_status("After Extractor Init")
            
            print("✅ SoA Extractor initialized successfully with multiple extraction methods")
            print("  - Integrated Graph Extractor: SOA-focused extraction")
            print("  - Lazy LangGraph Extractor: Comprehensive table extraction")
            print("  - Enhanced memory protection and timeout management")
            print("  - Adaptive memory thresholds based on system RAM")
            
        except ImportError as e:
            # This is OK - the external library is optional
            # SoA extraction can still work with fallback methods
            print(f"ℹ️  Note: Optional SoA extraction library not available ({str(e).split(':')[0]})")
            print("   Advanced table extraction features will use fallback methods")
            self.extractor = None
            self.lazy_extractor = None
        except Exception as e:
            print(f"❌ Extractor initialization failed: {e}")
            self.extractor = None
            self.lazy_extractor = None
    
    def _deduplicate_soa_data(self, soa_tables: List[SoATableResult]) -> List[SoATableResult]:
        """Deduplicate SoA tables to prevent duplicates in frontend"""
        seen = set()
        unique_tables = []
        
        for table in soa_tables:
            if not table or not hasattr(table, 'nct_id'):
                continue
                
            # Create unique key for each table
            table_key = f"{table.nct_id}-{table.page_number}-{table.table_title}"
            
            if table_key not in seen:
                seen.add(table_key)
                unique_tables.append(table)
        
        return unique_tables

    def _validate_soa_data(self, soa_data: Dict) -> bool:
        """Validate SoA data structure before sending to frontend"""
        required_fields = ['trial_summaries', 'soa_table_details', 'hasSoAContent']
        
        if not all(field in soa_data for field in required_fields):
            print(f"❌ Missing required fields in SoA data: {list(soa_data.keys())}")
            return False
        
        if not isinstance(soa_data['trial_summaries'], list):
            print(f"❌ trial_summaries is not a list: {type(soa_data['trial_summaries'])}")
            return False
        
        if not isinstance(soa_data['soa_table_details'], list):
            print(f"❌ soa_table_details is not a list: {type(soa_data['soa_table_details'])}")
            return False
        
        if not isinstance(soa_data['hasSoAContent'], bool):
            print(f"❌ hasSoAContent is not a boolean: {type(soa_data['hasSoAContent'])}")
            return False
        
        return True
    
    async def extract_soa_from_pdf(self, pdf_path: str, nct_id: str, 
                                  extraction_mode: ExtractionMode = "auto",
                                  user_query: str = "", progress_callback=None) -> List[SoATableResult]:
        """Extract SoA tables from a protocol PDF with intelligent mode selection and progress logging"""
        if not self.extractor and not self.lazy_extractor:
            raise RuntimeError("No extractors available")
        
        # Check for emergency exit request
        if self._emergency_exit_requested:
            raise RuntimeError("Emergency exit requested, cannot proceed with extraction")
        
        # Send progress update for extraction start
        if progress_callback:
            await progress_callback({
                "node_id": "extract_soa",
                "node_type": "extract",
                "status": "progress",
                "context": f"Starting {extraction_mode} extraction for {nct_id}",
                "details": "Initializing extraction process and loading extractors",
                "current_trial": nct_id,
                "extraction_step": "extraction_initialization",
                "extraction_method": extraction_mode,
                "pdf_size_mb": round(os.path.getsize(pdf_path) / (1024 * 1024), 2)
            })
        
        # Auto-detect extraction mode if not specified
        if extraction_mode == "auto" and user_query:
            extraction_mode = self.mode_detector.detect_extraction_mode(user_query)
        
        print(f"🎯 Extraction Mode: {extraction_mode}")
        print(f"📝 Description: {self.mode_detector.get_extraction_description(extraction_mode)}")
        
        # Send progress update for mode detection
        if progress_callback:
            await progress_callback({
                "node_id": "extract_soa",
                "node_type": "extract",
                "status": "progress",
                "context": f"Mode detection for {nct_id}",
                "details": f"Selected extraction mode: {extraction_mode} - {self.mode_detector.get_extraction_description(extraction_mode)}",
                "current_trial": nct_id,
                "extraction_step": "mode_detection",
                "extraction_method": extraction_mode
            })
        
        # Pre-extraction memory check
        self.memory_manager.log_memory_status(f"Before {extraction_mode} extraction for {nct_id}")
        
        # Send progress update for memory check
        if progress_callback:
            memory_info = self.memory_manager.check_memory_usage()
            await progress_callback({
                "node_id": "extract_soa",
                "node_type": "extract",
                "status": "progress",
                "context": f"Memory check for {nct_id}",
                "details": f"Memory usage: {memory_info['percent']:.1f}% ({memory_info['gb']:.2f}GB) - {'Safe' if memory_info['percent'] < 80 else 'Warning'}",
                "current_trial": nct_id,
                "extraction_step": "memory_check",
                "memory_usage": memory_info,
                "memory_status": "safe" if memory_info['percent'] < 80 else "warning"
            })
        
        if self.memory_manager.is_memory_warning():
            print("⚠️  Memory usage high before extraction, forcing cleanup")
            
            # Send progress update for memory cleanup
            if progress_callback:
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Memory cleanup for {nct_id}",
                    "details": "Performing garbage collection due to high memory usage - this may take a moment",
                    "current_trial": nct_id,
                    "extraction_step": "memory_cleanup"
                })
            
            self.memory_manager.force_garbage_collection()
            
            # Check again after cleanup
            if not self.memory_manager.is_memory_safe():
                error_msg = f"Memory usage too high ({self.memory_manager.check_memory_usage()['percent']:.1f}%) to safely extract SoA"
                
                # Send progress update for memory error
                if progress_callback:
                    await progress_callback({
                        "node_id": "extract_soa",
                        "node_type": "extract",
                        "status": "failed",
                        "context": f"Memory error for {nct_id}",
                        "details": error_msg,
                        "current_trial": nct_id,
                        "extraction_step": "memory_error",
                        "extraction_error": error_msg
                    })
                
                raise RuntimeError(error_msg)
        
        try:
            log_query(f"{extraction_mode} extraction for {nct_id} from {pdf_path}")
            start_time = asyncio.get_event_loop().time()
            
            # Send progress update for extraction start
            if progress_callback:
                memory_info = self.memory_manager.check_memory_usage()
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Starting table extraction for {nct_id}",
                    "details": f"Using {extraction_mode} extraction method - preparing extractor and analyzing PDF structure",
                    "current_trial": nct_id,
                    "extraction_step": "table_extraction_start",
                    "extraction_method": extraction_mode,
                    "memory_usage": memory_info
                })
            
            # Extract tables based on mode
            if extraction_mode == "soa_only":
                result = await self._extract_soa_only(pdf_path, nct_id, progress_callback)
            elif extraction_mode == "general_only":
                result = await self._extract_general_only(pdf_path, nct_id, progress_callback)
            elif extraction_mode == "toc_only":
                result = await self._extract_toc_only(pdf_path, nct_id, progress_callback)
            elif extraction_mode == "all_tables":
                result = await self._extract_all_tables(pdf_path, nct_id, progress_callback)
            else:
                # Auto mode - use intelligent selection
                result = await self._extract_auto_mode(pdf_path, nct_id, user_query, progress_callback)
            
            # Send progress update for extraction completion
            if progress_callback:
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Extraction completed for {nct_id}",
                    "details": f"Successfully extracted tables using {extraction_mode} method - processing results",
                    "current_trial": nct_id,
                    "extraction_step": "table_extraction_completed",
                    "extraction_method": extraction_mode,
                    "tables_extracted": len(result.get('extracted_tables', []))
                })
            
            # Post-extraction memory check
            self.memory_manager.log_memory_status(f"After {extraction_mode} extraction for {nct_id}")
            
            # Send progress update for post-extraction memory check
            if progress_callback:
                memory_info = self.memory_manager.check_memory_usage()
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Post-extraction memory check for {nct_id}",
                    "details": f"Memory usage after extraction: {memory_info['percent']:.1f}% ({memory_info['gb']:.2f}GB) - {'Stable' if memory_info['percent'] < 90 else 'High'}",
                    "current_trial": nct_id,
                    "extraction_step": "post_extraction_memory_check",
                    "memory_usage": memory_info,
                    "memory_status": "stable" if memory_info['percent'] < 90 else "high"
                })
            
            # Convert to our schema
            soa_tables = []
            for table in result.get('extracted_tables', []):
                # Check if this is an SoA table (for all modes, we want to identify table types)
                if self._is_soa_table(table):
                    # Handle different table data structures
                    table_data = self._normalize_table_data(table)
                    
                    soa_table = SoATableResult(
                        nct_id=nct_id,
                        table_title=table.get('title', 'Unknown'),
                        page_number=table.get('page', 0),
                        table_data=table_data,
                        extraction_method=table.get('extraction_method', extraction_mode),
                        confidence_score=table.get('confidence', 0.5),
                        metadata={
                            'extraction_time': result.get('extraction_time', 0),
                            'overall_confidence': result.get('confidence', 0.5),
                            'table_type': table.get('table_type', 'unknown'),
                            'extraction_mode': extraction_mode
                        }
                    )
                    soa_tables.append(soa_table)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            log_performance(f"{extraction_mode} extraction for {nct_id}", processing_time)
            
            # Deduplicate SoA tables to prevent frontend duplicates
            unique_soa_tables = self._deduplicate_soa_data(soa_tables)
            print(f"🔍 Deduplicated {len(soa_tables)} → {len(unique_soa_tables)} unique tables")
            
            # Send progress update for processing completion
            if progress_callback:
                # Create SoA data structure
                soa_data = {
                    "trial_summaries": [{
                        'nct_id': nct_id,
                        'title': f'Trial {nct_id}',
                        'condition': 'Unknown',
                        'phase': 'Unknown',
                        'status': 'Unknown',
                        'sponsor': 'Unknown',
                        'enrollment': 'Unknown',
                        'soa_table_count': len(unique_soa_tables)
                    }],
                    "soa_table_details": [
                        {
                            'nct_id': table.nct_id,
                            'table_title': table.table_title,
                            'page_number': table.page_number,
                            'table_data': table.table_data,
                            'confidence_score': table.confidence_score,
                            'extraction_method': table.extraction_method,
                            'metadata': {
                                'extraction_time': result.get('extraction_time', 0),
                                'overall_confidence': result.get('confidence', 0.5),
                                'table_type': getattr(table, 'metadata', {}).get('table_type', 'soa_table'),
                                'extraction_mode': extraction_mode
                            }
                        } for table in unique_soa_tables
                    ],
                    "hasSoAContent": True,
                    "soa_indicators": f"Extracted {len(unique_soa_tables)} SoA tables from {nct_id}"
                }
                
                # Debug: Log the actual table data structure being sent
                if unique_soa_tables:
                    sample_table = unique_soa_tables[0]
                    print(f"🔍 🔍 DEBUG: Sample table data structure:")
                    print(f"  📋 Table title: {sample_table.table_title}")
                    print(f"  📋 Table data type: {type(sample_table.table_data)}")
                    print(f"  📋 Table data length: {len(sample_table.table_data) if sample_table.table_data else 0}")
                    if sample_table.table_data and len(sample_table.table_data) > 0:
                        print(f"  📋 First row type: {type(sample_table.table_data[0])}")
                        print(f"  📋 First row: {sample_table.table_data[0]}")
                        if isinstance(sample_table.table_data[0], dict):
                            print(f"  📋 First row keys: {list(sample_table.table_data[0].keys())}")
                
                # Validate SoA data before sending
                if self._validate_soa_data(soa_data):
                    await progress_callback({
                        "node_id": "extract_soa",
                        "node_type": "extract",
                        "status": "progress",
                        "context": f"Processing completed for {nct_id}",
                        "details": f"Processed {len(unique_soa_tables)} SoA tables in {processing_time:.2f}s",
                        "current_trial": nct_id,
                        "extraction_step": "processing_completed",
                        "tables_extracted": len(unique_soa_tables),
                        "processing_time": processing_time,
                        "soa_data": soa_data
                    })
                else:
                    print(f"❌ SoA data validation failed for {nct_id}")
                    # Send progress update without SoA data
                    await progress_callback({
                        "node_id": "extract_soa",
                        "node_type": "extract",
                        "status": "progress",
                        "context": f"Processing completed for {nct_id}",
                        "details": f"Processed {len(unique_soa_tables)} SoA tables in {processing_time:.2f}s",
                        "current_trial": nct_id,
                        "extraction_step": "processing_completed",
                        "tables_extracted": len(unique_soa_tables),
                        "processing_time": processing_time
                    })
            
            # Final memory cleanup
            self.memory_manager.force_garbage_collection()
            
            print(f"✅ Extracted {len(unique_soa_tables)} tables from {nct_id} using {extraction_mode} mode")
            return unique_soa_tables
            
        except TimeoutError as e:
            log_error(e, f"{extraction_mode} extraction timeout for {nct_id}")
            print(f"⏰ {extraction_mode} extraction timed out for {nct_id}")
            
            # Send progress update for timeout
            if progress_callback:
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Extraction timeout for {nct_id}",
                    "details": f"Extraction timed out after {extraction_mode} mode",
                    "current_trial": nct_id,
                    "extraction_step": "timeout",
                    "extraction_error": str(e)
                })
            
            return []
        except Exception as e:
            log_error(e, f"{extraction_mode} extraction for {nct_id}")
            print(f"❌ {extraction_mode} extraction failed for {nct_id}: {e}")
            
            # Send progress update for extraction failure
            if progress_callback:
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Extraction failed for {nct_id}",
                    "details": f"Error during {extraction_mode} extraction: {str(e)}",
                    "current_trial": nct_id,
                    "extraction_step": "extraction_failed",
                    "extraction_error": str(e)
                })
            
            return []
        finally:
            # Always perform cleanup
            self._cleanup_after_extraction()
    
    async def _extract_soa_only(self, pdf_path: str, nct_id: str, progress_callback=None) -> Dict[str, Any]:
        """Extract only Schedule of Activities tables"""
        print(f"🎯 SOA-only extraction for {nct_id}")
        
        # Debug: Check if progress callback is available
        if progress_callback:
            print(f"📋 🔍 SoA Extractor has progress_callback: {type(progress_callback)}")
        else:
            print(f"⚠️ SoA Extractor has NO progress_callback")
        
        # Send progress update for SOA extraction start
        if progress_callback:
            memory_info = self.memory_manager.check_memory_usage()
            await progress_callback({
                "node_id": "extract_soa",
                "node_type": "extract",
                "status": "progress",
                "context": f"Starting SOA-only extraction for {nct_id}",
                "details": "Using Integrated Graph Extractor for SOA tables - this method provides the highest accuracy for visit schedules",
                "current_trial": nct_id,
                "extraction_step": "soa_extraction_start",
                "extraction_method": "soa_only",
                "memory_usage": memory_info,
                "extractor_type": "Integrated Graph Extractor"
            })
        
        if not self.extractor:
            raise RuntimeError("Integrated Graph Extractor not available for SOA extraction")
        
        try:
            # Send progress update for extraction preparation
            if progress_callback:
                print(f"📋 🔍 SoA Extractor has progress_callback: {type(progress_callback)}")
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Preparing SOA extraction for {nct_id}",
                    "details": "Initializing Integrated Graph Extractor and setting up extraction pipeline",
                    "current_trial": nct_id,
                    "extraction_step": "extractor_preparation",
                    "extraction_method": "soa_only"
                })
            else:
                print(f"⚠️ SoA Extractor has NO progress_callback")
            
            # Create enhanced progress callback for the integrated extractor
            async def integrated_extractor_progress_callback(progress_data):
                """Enhanced progress callback for integrated extractor with detailed step mapping"""
                print(f"📋 🔍 SoA Extractor integrated_extractor_progress_callback CALLED with data: {progress_data}")
                if progress_callback:
                    print(f"📋 🔍 SoA Extractor has progress_callback: {type(progress_callback)}")
                else:
                    print(f"⚠️ SoA Extractor has NO progress_callback")
                
                print(f"📋 🔍 SoA Extractor received progress: {progress_data.get('step', 'unknown')} - {progress_data.get('details', 'No details')}")
                print(f"📋 📊 Full progress data: {progress_data}")
                
                # Map integrated extractor steps to meaningful progress updates
                step_mapping = {
                    'toc_extraction': 'TOC Extraction',
                    'soa_page_identification': 'SOA Page Identification', 
                    'page_analysis': 'Page Content Analysis',
                    'table_detection': 'Table Structure Detection',
                    'table_extraction': 'Table Data Extraction',
                    'table_processing': 'Table Data Processing',
                    'table_validation': 'Table Validation',
                    'result_assembly': 'Result Assembly',
                    'method_grouping': 'Method Grouping',
                    'extraction_completion': 'Extraction Completion',
                    'page_number_assignment': 'Page Number Assignment',
                    'toc_metadata_tagging': 'TOC Metadata Tagging',
                    'golden_set_comparison': 'Golden Set Comparison',
                    'pre_filtering': 'Pre-filtering Pages',
                    'method_processing': 'Method Processing'
                }
                
                # Extract step information
                current_step = progress_data.get('step', 'unknown')
                step_description = step_mapping.get(current_step, current_step.replace('_', ' ').title())
                
                # Add context and details
                enhanced_data = {
                    "node_id": "extract_soa",
                    "node_type": "extract", 
                    "status": "progress",
                    "context": f"SOA extraction in progress for {nct_id}",
                    "details": progress_data.get('details', f"Current step: {step_description}"),
                    "current_trial": nct_id,
                    "extraction_step": current_step,
                    "extraction_method": "soa_only",
                    "step_description": step_description,
                    "extractor_type": "Integrated Graph Extractor",
                    # Forward all detailed progress information
                    "step": current_step,
                    "progress": progress_data.get('progress'),
                    "total_pages": progress_data.get('total_pages'),
                    "total_tables": progress_data.get('total_tables'),
                    "method_groups": progress_data.get('method_groups'),
                    "page_analyses": progress_data.get('page_analyses'),
                    "current_method": progress_data.get('current_method'),
                    "current_batch": progress_data.get('current_batch'),
                    "batch_size": progress_data.get('batch_size'),
                    "pages_processed": progress_data.get('pages_processed'),
                    "tables_found": progress_data.get('tables_found')
                }
                
                # Add any additional data from the integrated extractor
                if 'page_number' in progress_data:
                    enhanced_data['current_page'] = progress_data['page_number']
                if 'tables_found' in progress_data:
                    enhanced_data['tables_found_so_far'] = progress_data['tables_found']
                if 'confidence' in progress_data:
                    enhanced_data['current_confidence'] = progress_data['confidence']
                
                print(f"📋 🔄 SoA Extractor forwarding progress: {enhanced_data}")
                if progress_callback:
                    await progress_callback(enhanced_data)
                else:
                    print(f"⚠️ Cannot forward progress - no progress_callback available")
            
            print(f"📋 🔍 Integrated extractor progress callback function defined: {integrated_extractor_progress_callback}")
            print(f"📋 🔍 Function type: {type(integrated_extractor_progress_callback)}")
            print(f"📋 🔍 Function name: {integrated_extractor_progress_callback.__name__}")
            
            # Ensure the progress callback is properly bound
            bound_callback = integrated_extractor_progress_callback
            print(f"📋 🔍 Bound callback: {bound_callback}")
            print(f"📋 🔍 Bound callback type: {type(bound_callback)}")
            print(f"📋 🔍 Bound callback is None: {bound_callback is None}")
            
            # Send progress update for extraction execution
            if progress_callback:
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"Executing SOA extraction for {nct_id}",
                    "details": "Running Integrated Graph Extractor with intelligent table detection and processing",
                    "current_trial": nct_id,
                    "extraction_step": "extraction_execution",
                    "extraction_method": "soa_only",
                    "timeout_seconds": 1800
                })
            
            result = await self.timeout_manager.with_timeout(
                self.extractor.extract_soa_with_graph(pdf_path, progress_callback=bound_callback),
                                    timeout=1800.0,  # 30 minutes for SOA extraction (consistent with main query timeout)
                context=f"SOA-only extraction for {nct_id}"
            )
            
            # Debug: Check if integrated extractor was called
            print(f"📋 🔍 Integrated Graph Extractor call completed")
            print(f"📋 🔍 Integrated Graph Extractor result type: {type(result)}")
            print(f"📋 🔍 Integrated Graph Extractor result: {result}")
            print(f"📋 🔍 Integrated Graph Extractor was called with progress_callback: {bound_callback}")
            print(f"📋 🔍 Progress callback type: {type(bound_callback)}")
            print(f"📋 🔍 Progress callback is None: {bound_callback is None}")
            
            # Send progress update for SOA extraction completion
            if progress_callback:
                memory_info = self.memory_manager.check_memory_usage()
                tables_count = len(result.extracted_tables) if hasattr(result, 'extracted_tables') else 0
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "progress",
                    "context": f"SOA extraction completed for {nct_id}",
                    "details": f"Successfully extracted {tables_count} SOA tables using Integrated Graph Extractor",
                    "current_trial": nct_id,
                    "extraction_step": "soa_extraction_completed",
                    "extraction_method": "soa_only",
                    "tables_extracted": tables_count,
                    "memory_usage": memory_info,
                    "extractor_type": "Integrated Graph Extractor"
                })
            
            # Convert to consistent format
            return {
                'extracted_tables': result.extracted_tables,
                'extraction_time': result.extraction_time,
                'confidence': result.confidence,
                'soa_tables': result.extracted_tables,
                'general_tables': []
            }
            
        except Exception as e:
            # Send progress update for SOA extraction error
            if progress_callback:
                await progress_callback({
                    "node_id": "extract_soa",
                    "node_type": "extract",
                    "status": "failed",
                    "context": f"SOA extraction error for {nct_id}",
                    "details": f"Error during SOA extraction: {str(e)}",
                    "current_trial": nct_id,
                    "extraction_step": "soa_extraction_error",
                    "extraction_method": "soa_only",
                    "extraction_error": str(e)
                })
            raise
    
    async def _extract_general_only(self, pdf_path: str, nct_id: str, progress_callback=None) -> Dict[str, Any]:
        """Extract only general tables (exclusions, endpoints, etc.)"""
        print(f"🎯 General tables only extraction for {nct_id}")
        
        if not self.lazy_extractor:
            raise RuntimeError("Lazy LangGraph Extractor not available for general table extraction")
        
        result = await self.timeout_manager.with_timeout(
            self.lazy_extractor.extract_tables(pdf_path),
                                timeout=1800.0,  # 30 minutes for general table extraction (consistent with main query timeout)
            context=f"General tables extraction for {nct_id}"
        )
        
        # Return only general tables
        return {
            'extracted_tables': result.get('general_tables', []),
            'extraction_time': 0,  # Lazy extractor doesn't provide this
            'confidence': 0.5,
            'soa_tables': [],
            'general_tables': result.get('general_tables', [])
        }
    
    async def _extract_toc_only(self, pdf_path: str, nct_id: str, progress_callback=None) -> Dict[str, Any]:
        """Extract only Table of Contents and document structure"""
        print(f"🎯 TOC-only extraction for {nct_id}")
        
        if not self.extractor:
            raise RuntimeError("Integrated Graph Extractor not available for TOC extraction")
        
        # Use the TOC extraction capabilities
        result = await self.timeout_manager.with_timeout(
            self.extractor.extract_soa_with_graph(pdf_path),
                                timeout=600.0,  # 10 minutes for TOC extraction
            context=f"TOC extraction for {nct_id}"
        )
        
        # Extract TOC information
        toc_data = result.toc_data if hasattr(result, 'toc_data') else {}
        
        return {
            'extracted_tables': [],  # TOC doesn't produce tables
            'extraction_time': result.extraction_time,
            'confidence': result.confidence,
            'soa_tables': [],
            'general_tables': [],
            'toc_data': toc_data
        }
    
    async def _extract_all_tables(self, pdf_path: str, nct_id: str, progress_callback=None) -> Dict[str, Any]:
        """Extract all tables (SOA + General)"""
        print(f"🎯 All tables extraction for {nct_id}")
        
        if not self.lazy_extractor:
            raise RuntimeError("Lazy LangGraph Extractor not available for comprehensive extraction")
        
        result = await self.timeout_manager.with_timeout(
            self.lazy_extractor.extract_tables(pdf_path),
                                timeout=1800.0,  # 30 minutes for comprehensive extraction (consistent with main query timeout)
            context=f"All tables extraction for {nct_id}"
        )
        
        # Combine all tables
        all_tables = []
        if result.get('soa_tables'):
            all_tables.extend(result['soa_tables'])
        if result.get('general_tables'):
            all_tables.extend(result['general_tables'])
        
        return {
            'extracted_tables': all_tables,
            'extraction_time': 0,
            'confidence': 0.5,
            'soa_tables': result.get('soa_tables', []),
            'general_tables': result.get('general_tables', [])
        }
    
    async def _extract_auto_mode(self, pdf_path: str, nct_id: str, user_query: str, progress_callback=None) -> Dict[str, Any]:
        """Intelligent auto-mode extraction based on content analysis"""
        print(f"🎯 Auto-mode extraction for {nct_id}")
        
        # Analyze the document to determine what's available
        if self.extractor:
            # Quick SOA-focused extraction first - WITH progress callback
            try:
                print(f"🎯 Auto-mode: Performing initial SOA analysis with progress callback")
                soa_result = await self.timeout_manager.with_timeout(
                    self.extractor.extract_soa_with_graph(pdf_path, progress_callback=progress_callback),
                    timeout=600.0,  # 10 minutes for quick analysis
                    context=f"Auto-mode SOA analysis for {nct_id}"
                )
                
                if soa_result.extracted_tables:
                    print(f"🎯 Auto-mode: Found {len(soa_result.extracted_tables)} SOA tables, returning result directly")
                    # Return the result directly instead of calling _extract_soa_only again
                    return {
                        'extracted_tables': soa_result.extracted_tables,
                        'extraction_time': soa_result.extraction_time,
                        'confidence': soa_result.confidence
                    }
                
            except Exception as e:
                print(f"⚠️  Auto-mode SOA analysis failed: {e}")
        
        # If no SOA tables found, try comprehensive extraction
        if self.lazy_extractor:
            print(f"🎯 Auto-mode: No SOA tables found, trying comprehensive extraction")
            return await self._extract_all_tables(pdf_path, nct_id, progress_callback)
        
        # Fallback to basic extraction
        print(f"🎯 Auto-mode: Using fallback extraction")
        return await self._extract_soa_only(pdf_path, nct_id, progress_callback)
    
    async def _safe_extract_soa(self, pdf_path: str):
        """Safely extract SoA with memory monitoring"""
        try:
            # Monitor memory during extraction
            async def memory_monitor():
                while True:
                    await asyncio.sleep(30)  # Check every 30 seconds
                    if self.memory_manager.is_memory_warning():
                        print("⚠️  Memory usage high during extraction, forcing cleanup")
                        self.memory_manager.force_garbage_collection()
                    
                    # Check for emergency exit request
                    if self._emergency_exit_requested:
                        print("🚨 Emergency exit requested, stopping memory monitor")
                        break
            
            # Start memory monitoring
            monitor_task = asyncio.create_task(memory_monitor())
            
            try:
                # Extract tables using the integrated extractor
                result = await self.extractor.extract_soa_with_graph(pdf_path)
                return result
            finally:
                # Cancel memory monitoring
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            print(f"❌ Safe extraction failed: {e}")
            raise
    
    def _cleanup_after_extraction(self):
        """Cleanup after extraction to prevent memory leaks"""
        try:
            print("🧹 Performing post-extraction cleanup...")
            
            # Force garbage collection
            self.memory_manager.force_garbage_collection()
            
            # Clear any temporary data
            if hasattr(self, '_temp_dir') and self._temp_dir.exists():
                # Clean up old temporary files
                for temp_file in self._temp_dir.glob("*.pdf"):
                    try:
                        if temp_file.stat().st_mtime < time.time() - 3600:  # 1 hour old
                            temp_file.unlink()
                    except Exception:
                        pass
            
            print("✅ Post-extraction cleanup completed")
        except Exception as e:
            print(f"⚠️  Post-extraction cleanup failed: {e}")
    
    def _is_soa_table(self, table: Dict[str, Any]) -> bool:
        """Determine if a table is a Schedule of Activities table"""
        title = table.get('title', 'Unknown').lower()
        keywords = ['schedule', 'activities', 'soa', 'visit', 'assessment', 'procedure']
        return any(keyword in title for keyword in keywords)
    
    def _normalize_table_data(self, table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize table data to the expected format"""
        try:
            # Get the raw table data
            raw_data = table.get('data', [])
            
            print(f"📋 🔄 _normalize_table_data called with table type: {type(table)}")
            print(f"📋 🔄 Raw data type: {type(raw_data)}")
            print(f"📋 🔄 Raw data length: {len(raw_data) if raw_data else 0}")
            
            # If it's already a list of dicts, return as is
            if raw_data and isinstance(raw_data[0], dict):
                print(f"📋 ✅ Data already in dict format, returning as-is")
                print(f"📋 🔄 First row keys: {list(raw_data[0].keys())}")
                return raw_data
            
            # If it's a list of lists (rows), convert to list of dicts
            if raw_data and isinstance(raw_data[0], list):
                print(f"📋 🔄 Converting list of lists to list of dicts")
                # Assume first row is headers
                if len(raw_data) < 2:
                    return []
                
                headers = raw_data[0]
                rows = raw_data[1:]
                
                print(f"📋 🔄 Original headers: {headers}")
                print(f"📋 🔄 Headers type: {type(headers)}")
                print(f"📋 🔄 Number of rows: {len(rows)}")
                
                result = []
                for row in rows:
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            row_dict[str(header)] = row[i]
                        else:
                            row_dict[str(header)] = ""
                    result.append(row_dict)
                
                print(f"📋 🔄 Converted result first row keys: {list(result[0].keys()) if result else 'No result'}")
                return result
            
            # If it's a string, try to parse it
            if isinstance(raw_data, str):
                print(f"📋 🔄 Parsing string data")
                # Simple CSV-like parsing
                lines = raw_data.strip().split('\n')
                if len(lines) < 2:
                    return []
                
                headers = lines[0].split('|')
                result = []
                for line in lines[1:]:
                    values = line.split('|')
                    row_dict = {}
                    for i, header in enumerate(headers):
                        if i < len(values):
                            row_dict[header.strip()] = values[i].strip()
                        else:
                            row_dict[header.strip()] = ""
                    result.append(row_dict)
                
                return result
            
            return []
            
        except Exception as e:
            print(f"⚠️  Table data normalization failed: {e}")
            return []

# Global instance
soa_extractor_agent = SoAExtractorAgent() 