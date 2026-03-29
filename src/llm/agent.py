"""LLM Agent for IOT deployment management."""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from typing import Callable

load_dotenv()


class LLMAgent:
    """LLM-powered agent that reasons about user intent and selects appropriate IOT deployment tools."""

    SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    with open(SYSTEM_PROMPT_PATH, "r") as f:
        SYSTEM_PROMPT = f.read()

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("API_KEY", "dummy"),
            base_url=os.getenv("API_BASE_URL", "http://localhost:11434/v1"),
        )
        self.model = os.getenv("MODEL", "llama3:latest")
        self.tools: dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        """Register an MCP tool for execution."""
        self.tools[name] = func

    def register_tools(self, tools: dict[str, Callable]):
        """Register multiple tools at once."""
        self.tools.update(tools)

    async def process(self, user_input: str) -> str:
        """Process user input: reason about intent, select and execute appropriate tool."""
        prompt = f"{self.SYSTEM_PROMPT}\n\nUser request: {user_input}"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0,
        )

        response_text = (response.choices[0].message.content or "").strip()
        if not response_text:
            return "No response from LLM."

        action = self._parse_action(response_text)
        if not action:
            return f"Could not parse response: {response_text}"

        tool_name = action.get("tool")

        # non-tool response
        if tool_name == "none" or not tool_name:
            return action.get("message", response_text)
        
        # execute tool
        return await self._execute_action(action)
        
    def _parse_action(self, response: str) -> dict | None:
        """Extract JSON action from LLM response with error correction."""
        # Try direct JSON parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Extract JSON block from response and attempt parsing with error correction
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                return None
            
            json_str = response[start:end]
            
            # First attempt: direct parse
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            import re
            json_str = re.sub(r':\s*(-?\d+)\s+to\s+(\d+)', r': "\1 to \2"', json_str)
            
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try removing problematic keys
                lines = json_str.split('\n')
                fixed_lines = []
                for line in lines:
                    # Skip malformed lines
                    if ':' in line and ('{' not in line and '[' not in line):
                        # Try to quote unquoted values
                        if ': ' in line and not ('": ' in line or "': " in line):
                            # Attempt basic fixing
                            pass
                    fixed_lines.append(line)
                
                try:
                    return json.loads('\n'.join(fixed_lines))
                except json.JSONDecodeError:
                    # Last resort: return response as message
                    return {"tool": "none", "message": response}
        
        except Exception as e:
            return {"tool": "none", "message": str(response)}

    async def _execute_action(self, action: dict) -> str:
        """Execute the requested tool action."""
        tool_name = action.get("tool")
        params = action.get("params", {})

        if tool_name not in self.tools:
            return f"Unknown tool: {tool_name}. Available: {list(self.tools.keys())}"

        try:
            result = await self.tools[tool_name](**params)
            return f"{tool_name}: {result}"
        except Exception as e:
            return f"Error in {tool_name}: {e}"