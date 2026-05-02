import json
import re

from pydantic import BaseModel
from typing import Any, List, Dict, Union


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

def format_answer_content(raw_answer: Any) -> str:
    """
    Format and reformat answer content to ensure valid JSON structure with proper formatting.
    
    Args:
        raw_answer: Raw answer from the agent (may be string, dict, or None)
        
    Returns:
        Formatted answer as a JSON string
    """
    answer = None
    
    # Parse raw answer into JSON
    if isinstance(raw_answer, str):
        # Extract JSON block from raw answer if it contains extra text
        pattern = re.compile(r'(\w+):\s*(\{[\s\S]*\}|\[[\s\S]*\])')
        match = pattern.search(raw_answer)
        if match:
            json_str = match.group(2)
            try:
                answer = json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Parse simple key-value pairs 
        if answer is None:
            answer = raw_answer.strip()
            # Extract key-value pairs if possible
            kv_pattern = re.compile(r"(\w+):\s*(.+)")
            kv_matches = kv_pattern.findall(answer)
            if kv_matches:
                answer_dict = {k: v for k, v in kv_matches}
                answer = answer_dict
            # Split all double line breaks into a list 
            elif "\n\n" in answer:
                items = [item.strip() for item in answer.split("\n\n") if item.strip()]
                answer = items
        else:
            # Structure valid JSON format
            if isinstance(answer, str):
                try:
                    answer = json.loads(answer)
                except json.JSONDecodeError:
                    pass
    else:
        answer = raw_answer
    
    # Format list as compact JSON (no newlines)
    return json.dumps([answer], separators=(',', ':'), ensure_ascii=False)