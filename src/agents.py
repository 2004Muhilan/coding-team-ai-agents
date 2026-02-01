
import os
import time
import json
from typing import List, Dict, Any, Optional
from groq import Groq
from src.prompts import PLANNER_PROMPT, BUILDER_PROMPT, REVIEWER_PROMPT
from src.tools import TOOLS_SCHEMA, AVAILABLE_FUNCTIONS

class Agent:
    def __init__(self, name: str, model: str, system_prompt: str):
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]
        
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def run(self) -> str:
        """
        Executes the agent's logic with tool calling support.
        """
        # Maximum turns to prevent infinite loops
        max_turns = 15
        
        for i in range(max_turns):
            print(f"Turn {i+1}...") # Optional: Debugging aid
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    max_tokens=4096
                )
            except Exception as e:
                # Catch API errors (like the 400 Bad Request) and print the last message state
                print(f"API Error: {e}")
                return f"Error: Agent crashed due to API error: {str(e)}"
            
            response_message = response.choices[0].message
            
            # 1. Convert the SDK object to a dictionary for the message history.
            # This ensures strict compatibility with the API for the next turn.
            assistant_message_dict = {
                "role": "assistant",
                "content": response_message.content if response_message.content else ""
            }
            
            # If there are tool calls, format them explicitly
            if response_message.tool_calls:
                assistant_message_dict["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in response_message.tool_calls
                ]
            
            self.messages.append(assistant_message_dict)
            
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    print(f" > Calling Tool: {function_name}", end=" | ")
                    
                    if function_name in AVAILABLE_FUNCTIONS:
                        function_to_call = AVAILABLE_FUNCTIONS[function_name]
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                            print(f"path: {function_args.get('path')}")
                            tool_response = function_to_call(**function_args)
                        except json.JSONDecodeError:
                            tool_response = f"Error: Invalid JSON arguments for tool '{function_name}'."
                        except Exception as e:
                            tool_response = f"Error executing tool '{function_name}': {str(e)}"
                    else:
                        tool_response = f"Error: Tool '{function_name}' not found."
                    
                    # Append the tool result to history
                    self.messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name, # Some APIs prefer the name included here
                            "content": str(tool_response),
                        }
                    )
            else:
                # If no tool calls, check for termination condition
                content = response_message.content
                if content and "DONE" in content:
                    return content
                
                # Enforce protocol if the model is chatting instead of working
                self.messages.append({
                    "role": "user",
                    "content": (
                        "Reminder: If you have completed your task, reply with exactly: DONE. "
                        "Otherwise, continue using tools to finish the task."
                    )
                })
            
            # Simple backoff to avoid rate limits
            time.sleep(2)

        return "Agent reached maximum turns without saying DONE."

class Planner(Agent):
    def __init__(self, model: str):
        super().__init__("Planner", model, PLANNER_PROMPT)

class Builder(Agent):
    def __init__(self, model: str):
        super().__init__("Builder", model, BUILDER_PROMPT)

class Reviewer(Agent):
    def __init__(self, model: str):
        super().__init__("Reviewer", model, REVIEWER_PROMPT)
