import json
from typing import Any, List, Dict, Union

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Chat message model for type hints and validation"""
    role: str
    content: Union[str, List[Dict[str, Any]]]


def extract_last_user_message(messages: List[ChatMessage]) -> str:
    """
    Extract the last user message content for processing.
    
    Args:
        messages: List of chat messages
        
    Returns:
        String content of the last user message, or empty string if not found
    """
    # First pass: look for user role specifically
    for m in reversed(messages):
        if m.role == "user" and m.content:
            if isinstance(m.content, str):
                return m.content.strip()
            elif isinstance(m.content, list):
                return json.dumps(m.content)
    
    # Second pass: look for any non-empty content
    for m in reversed(messages):
        if m.content:
            if isinstance(m.content, str):
                return m.content.strip()
            elif isinstance(m.content, list):
                return json.dumps(m.content)
    
    return ""

