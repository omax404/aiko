"""
AIKO ERROR HIERARCHY
Standardized exception classes for the application.
"""

from datetime import datetime

class AikoError(Exception):
    """Base exception for all Aiko application errors."""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.utcnow()

class ResourceNotFoundError(AikoError):
    """Raised when a file or model is missing."""
    pass

class VisionError(AikoError):
    """Errors related to Computer Vision / Moondream."""
    pass

class VoiceError(AikoError):
    """Errors related to TTS / Pocket-TTS."""
    pass

class VTSError(AikoError):
    """Errors related to VTube Studio connection."""
    pass

class MemoryError(AikoError):
    """Errors related to Memory/RAG system."""
    pass

class GenerationError(AikoError):
    """Errors during Image Generation."""
    pass
