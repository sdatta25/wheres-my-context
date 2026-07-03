"""Custom exceptions for Where's My Context."""

class MemoryEngineError(Exception):
    """Base exception for memory engine errors."""
    pass

class InvalidProjectError(MemoryEngineError):
    """Raised when project name is invalid."""
    pass

class MemoryNotFoundError(MemoryEngineError):
    """Raised when a memory cannot be found."""
    pass

class ConceptExtractionError(MemoryEngineError):
    """Raised when concept extraction fails."""
    pass

class CogneeConnectionError(MemoryEngineError):
    """Raised when Cognee Cloud connection fails."""
    pass

class RecallError(MemoryEngineError):
    """Raised when recall operation fails."""
    pass
