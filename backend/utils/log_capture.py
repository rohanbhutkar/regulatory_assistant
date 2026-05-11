"""
Log Capture - Captures backend logs and sends them to frontend via WebSocket
"""
import sys
import logging
import asyncio
from typing import Optional, Callable
from datetime import datetime
from collections import deque

class LogCapture:
    """Captures stdout/stderr and logging output and forwards to WebSocket"""
    
    def __init__(self, websocket_manager=None):
        self.websocket_manager = websocket_manager
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.original_log_handlers = []
        self.enabled = False
        self.log_buffer = []
        self.max_buffer_size = 1000  # Keep last 1000 log lines
        self.log_queue = deque(maxlen=100)  # Queue for async processing
        self._background_task = None
        
    def set_websocket_manager(self, websocket_manager):
        """Set the WebSocket manager for broadcasting logs"""
        self.websocket_manager = websocket_manager
    
    def enable(self):
        """Enable log capture"""
        if self.enabled:
            return
        
        self.enabled = True
        
        # Capture stdout
        sys.stdout = self
        
        # Capture stderr
        sys.stderr = self
        
        # Capture logging output
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                self.original_log_handlers.append(handler)
        
        # Add custom handler for logs
        log_handler = LoggingHandler(self)
        log_handler.setLevel(logging.INFO)
        root_logger.addHandler(log_handler)
        
        # Start background task to process log queue
        self._start_background_task()
    
    def disable(self):
        """Disable log capture"""
        if not self.enabled:
            return
        
        self.enabled = False
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Remove custom handler
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, LoggingHandler):
                root_logger.removeHandler(handler)
    
    def write(self, text: str):
        """Write to original stream and capture for WebSocket"""
        # Write to original stream
        if self.original_stdout:
            self.original_stdout.write(text)
            self.original_stdout.flush()
        
        # Capture for WebSocket - handle multi-line text
        if text.strip():  # Only send non-empty lines
            # Split by newlines and capture each line
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line:  # Only send non-empty lines
                    # Wrap long lines before capturing (120 char width)
                    wrapped_lines = self._wrap_text(line, width=120).split('\n')
                    for wrapped_line in wrapped_lines:
                        self._capture_log(wrapped_line, 'stdout')
    
    def flush(self):
        """Flush original stream"""
        if self.original_stdout:
            self.original_stdout.flush()
    
    def _start_background_task(self):
        """Start background task to process log queue"""
        async def process_log_queue():
            while self.enabled:
                try:
                    if self.log_queue and self.websocket_manager:
                        log_entry = self.log_queue.popleft()
                        await self.websocket_manager.broadcast_log_event(log_entry)
                    else:
                        await asyncio.sleep(0.1)  # Small delay if queue is empty
                except Exception as e:
                    # Don't fail if there's an error
                    await asyncio.sleep(0.1)
        
        # Try to get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self._background_task = asyncio.create_task(process_log_queue())
            else:
                # If no loop, we'll handle it differently
                pass
        except RuntimeError:
            # No event loop available, logs will be queued
            pass
    
    def _wrap_text(self, text: str, width: int = 120) -> str:
        """Wrap long text to prevent cutoff, preserving words"""
        if len(text) <= width:
            return text
        
        # Split into words
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            # Check if adding this word would exceed width
            if current_length + len(word) + 1 > width and current_line:
                # Start a new line
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                # Add to current line
                current_line.append(word)
                current_length += len(word) + 1 if current_line else len(word)
        
        # Add the last line
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def _capture_log(self, message: str, source: str = 'stdout'):
        """Capture a log message and send via WebSocket"""
        # Wrap long messages to prevent cutoff
        wrapped_message = self._wrap_text(message, width=120)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": wrapped_message,
            "source": source,
            "level": self._detect_log_level(message)
        }
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > self.max_buffer_size:
            self.log_buffer.pop(0)
        
        # Add to queue for async processing
        if self.websocket_manager:
            self.log_queue.append(log_entry)
            
            # Try to send immediately if possible (non-blocking)
            try:
                loop = asyncio.get_running_loop()
                # Schedule async broadcast
                try:
                    asyncio.create_task(self.websocket_manager.broadcast_log_event(log_entry))
                except Exception:
                    # If task creation fails, just queue it
                    pass
            except RuntimeError:
                # No running event loop, queue it for later processing
                # The WebSocket manager will handle it when it processes messages
                pass
    
    def _detect_log_level(self, message: str) -> str:
        """Detect log level from message"""
        message_lower = message.lower()
        if any(indicator in message_lower for indicator in ['error', '❌', 'failed', 'exception']):
            return 'error'
        elif any(indicator in message_lower for indicator in ['warning', '⚠️', 'warn']):
            return 'warning'
        elif any(indicator in message_lower for indicator in ['info', 'ℹ️', '✅', '🔍', '📊']):
            return 'info'
        else:
            return 'debug'
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """Get recent log entries"""
        return self.log_buffer[-limit:]


class LoggingHandler(logging.Handler):
    """Custom logging handler that forwards to LogCapture"""
    
    def __init__(self, log_capture: LogCapture):
        super().__init__()
        self.log_capture = log_capture
    
    def emit(self, record):
        """Emit a log record"""
        try:
            message = self.format(record)
            level = record.levelname.lower()
            self.log_capture._capture_log(message, f'logger_{level}')
        except Exception:
            pass


# Global instance
log_capture = LogCapture()
