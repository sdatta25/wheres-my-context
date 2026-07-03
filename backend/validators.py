"""Input validation utilities for Where's My Context."""
import re
from typing import Optional

def validate_project_name(name: str, max_length: int = 100) -> str:
    """Validate and sanitize a project name."""
    if not name or not isinstance(name, str):
        raise ValueError("Project name must be a non-empty string")
    
    name = name.strip()
    if len(name) > max_length:
        raise ValueError(f"Project name exceeds {max_length} characters")
    
    # Allow alphanumeric, spaces, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9\s\-_]+$", name):
        raise ValueError("Project name contains invalid characters")
    
    return name

def validate_memory_text(text: str, min_length: int = 5, max_length: int = 10000) -> str:
    """Validate and sanitize memory text."""
    if not text or not isinstance(text, str):
        raise ValueError("Memory text must be a non-empty string")
    
    text = text.strip()
    if len(text) < min_length:
        raise ValueError(f"Memory text must be at least {min_length} characters")
    
    if len(text) > max_length:
        raise ValueError(f"Memory text exceeds {max_length} characters")
    
    return text

def validate_author_name(name: Optional[str]) -> str:
    """Validate author name."""
    if not name:
        return "anonymous"
    
    name = str(name).strip()
    if len(name) > 100:
        raise ValueError("Author name exceeds 100 characters")
    
    return name

def validate_query(query: str, min_length: int = 3) -> str:
    """Validate search query."""
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")
    
    query = query.strip()
    if len(query) < min_length:
        raise ValueError(f"Query must be at least {min_length} characters")
    
    return query
