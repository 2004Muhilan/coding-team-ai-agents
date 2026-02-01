
import os
import sys
import argparse
from dotenv import load_dotenv
from termcolor import colored

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents import Planner, Builder, Verifier, Agent
from src.tools import read_file, TOOLS_SCHEMA, AVAILABLE_FUNCTIONS
import json

# Load environment variables
load_dotenv()

def debug_run(self) -> str:
    """
    Debug version of Agent.run with logging.
    """
    max_turns = 15
    print(colored(f"\n[DEBUG] Starting run for agent: {self.name}", "cyan"))
    
    for turn in range(max_turns):
        print(colored(f"\n[DEBUG] Turn {turn + 1}/{max_turns}", "cyan"))
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            max_tokens=4096
        )
        
        response_message = response.choices[0].message
        self.messages.append(response_message)
        
        content = response_message.content
        if content:
             print(colored(f"[DEBUG] Model Content: {content}", "white"))
        
        tool_calls = response_message.tool_calls
        
        if tool_calls:
            print(colored(f"[DEBUG] Tool Calls: {len(tool_calls)}", "yellow"))
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                args_str = tool_call.function.arguments
                print(colored(f"[DEBUG] Calling: {function_name} with args: {args_str}", "yellow"))
                
                if function_name in AVAILABLE_FUNCTIONS:
                    function_to_call = AVAILABLE_FUNCTIONS[function_name]
                    try:
                        function_args = json.loads(args_str)
                        tool_response = function_to_call(**function_args)
                        print(colored(f"[DEBUG] Tool Output: {str(tool_response)[:200]}...", "green"))
                    except json.JSONDecodeError:
                        tool_response = f"Error: Invalid JSON arguments for tool '{function_name}'."
                        print(colored(f"[DEBUG] {tool_response}", "red"))
                    except Exception as e:
                        tool_response = f"Error executing tool '{function_name}': {str(e)}"
                        print(colored(f"[DEBUG] {tool_response}", "red"))
                else:
                    tool_response = f"Error: Tool '{function_name}' not found."
                    print(colored(f"[DEBUG] {tool_response}", "red"))
                
                self.messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": str(tool_response),
                    }
                )
        else:
            print(colored("[DEBUG] No tool calls.", "cyan"))
            
            if content and "DONE" in content:
                print(colored("[DEBUG] DONE signal received.", "green"))
                return content
            
            self.messages.append({
                "role": "user",
                "content": (
                    "Reminder: If you have completed your task, reply with exactly: DONE. "
                    "Otherwise, continue using tools to finish the task."
                )
            })

    print(colored("[DEBUG] Reached max turns.", "red"))
    return "Agent reached maximum turns without saying DONE."

# Monkeypatch the Agent.run method
Agent.run = debug_run

def print_agent_output(agent_name: str, content: str):
    print(colored(f"\n[{agent_name}]", "blue", attrs=["bold"]))
    print(content)

def check_env_vars():
    if not os.getenv("GROQ_API_KEY"):
        print(colored("Error: GROQ_API_KEY not found in .env file.", "red"))
        sys.exit(1)
    if not os.getenv("GROQ_MODEL_NAME"):
        print(colored("Warning: GROQ_MODEL_NAME not found in .env, defaulting to 'llama3-70b-8192'", "yellow"))
        os.environ["GROQ_MODEL_NAME"] = "llama3-70b-8192"

def run_planner(model_name):
    print(colored("Initializing Planner...", "green"))
    planner = Planner(model=model_name)
    
    print(colored("\n--- Planner Phase ---", "magenta"))
    user_request = input(colored("What would you like to build? ", "yellow"))
    planner.add_message("user", user_request)
    
    while True:
        print(colored("Planner is working...", "cyan"))
        response = planner.run()
        print_agent_output("Planner", response)
        
        # Display the generated plan files
        print(colored("\nCurrent Plan Files:", "cyan"))
        for filename in ["requirements.md", "architecture.md", "task_plan.md"]:
            content = read_file(filename)
            if not content.startswith("Error"):
                print(colored(f"\n--- {filename} ---", "white", attrs=["bold"]))
                print(content)
            else:
                print(colored(f"Warning: {filename} was not created.", "red"))
        
        # Human-in-the-loop
        print(colored("\nDo you approve this plan?", "yellow"))
        user_feedback = input("Type 'yes' to proceed, or provide feedback to refine the plan: ")
        
        if user_feedback.lower() in ["yes", "y", "approve"]:
            break
        else:
            planner.add_message("user", f"User Feedback: {user_feedback}\nPlease update the plan files based on this feedback.")

def run_builder(model_name):
    print(colored("Initializing Builder...", "green"))
    builder = Builder(model=model_name)
    
    print(colored("\n--- Builder Phase ---", "magenta"))
    # Context Injection for Builder
    print(colored("Injecting plan context into Builder...", "cyan"))
    
    requirements = read_file("requirements.md")
    architecture = read_file("architecture.md")
    task_plan = read_file("task_plan.md")
    
    # Check if files exist to avoid errors if running builder in isolation without planner first
    if requirements.startswith("Error") or architecture.startswith("Error") or task_plan.startswith("Error"):
        print(colored("Error: One or more plan files are missing. Builder might fail.", "red"))
        sys.exit(1)
    
    builder_context = f"""The plan has been approved. Here are the documents:

--- requirements.md ---
{requirements}

--- architecture.md ---
{architecture}

--- task_plan.md ---
{task_plan}

Please start building the system based on these files.
"""
    builder.add_message("user", builder_context)
    
    print(colored("Builder is working...", "cyan"))
    response = builder.run()
    print_agent_output("Builder", response)

def run_verifier(model_name):
    print(colored("Initializing Verifier...", "green"))
    verifier = Verifier(model=model_name)
    
    print(colored("\n--- Verifier Phase ---", "magenta"))
    verifier.add_message("user", "The system has been built. Please verify the code and run tests.")
    
    print(colored("Verifier is working...", "cyan"))
    response = verifier.run()
    print_agent_output("Verifier", response)
    
    # Final Output
    review_content = read_file("test_review.md")
    if not review_content.startswith("Error"):
        print(colored("\n--- Review Report ---", "white", attrs=["bold"]))
        print(review_content)
    else:
        print(colored("Warning: test_review.md was not created.", "yellow"))

def main():
    parser = argparse.ArgumentParser(description="Run specific agents from the coding team.")
    parser.add_argument("--agent", type=str, required=True, choices=["planner", "builder", "verifier"], help="The agent to run.")
    args = parser.parse_args()
    
    check_env_vars()
    model_name = os.environ["GROQ_MODEL_NAME"]
    
    if args.agent == "planner":
        run_planner(model_name)
    elif args.agent == "builder":
        run_builder(model_name)
    elif args.agent == "verifier":
        run_verifier(model_name)

if __name__ == "__main__":
    main()
