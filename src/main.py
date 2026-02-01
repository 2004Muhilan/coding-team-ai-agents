
import os
import sys
from dotenv import load_dotenv
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from termcolor import colored
from src.agents import Planner, Builder, Reviewer
from src.tools import read_file, list_files

# Load environment variables
load_dotenv()

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

def main():
    check_env_vars()
    
    model_name = os.environ["GROQ_MODEL_NAME"]
    
    print(colored("Initializing Agents...", "green"))
    planner = Planner(model=model_name)
    builder = Builder(model=model_name)
    reviewer = Reviewer(model=model_name)
    
    print(colored("Welcome to the Multi-Agent Coding Team!", "cyan", attrs=["bold"]))
    user_request = input(colored("What would you like to build? ", "yellow"))
    
    # --- Planner Phase ---
    print(colored("\n--- Planner Phase ---", "magenta"))
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

    # --- Builder & Reviewer Loop ---
    print(colored("\n--- Builder & Reviewer Phase ---", "magenta"))
    # Context Injection for Builder
    print(colored("Injecting plan context into Builder...", "cyan"))
    
    requirements = read_file("requirements.md")
    architecture = read_file("architecture.md")
    task_plan = read_file("task_plan.md")
    
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

    loop_count = 0
    
    while True:
        loop_count += 1
        print(colored(f"\n--- Iteration {loop_count}: Building ---", "magenta"))
        
        # 1. Builder Works
        print(colored("Builder is working...", "cyan"))
    
        response = builder.run()
        print_agent_output("Builder", response)
    
        # 2. Reviewer Works
        print(colored("\n--- Reviewer Phase ---", "magenta"))
    
        reviewer_context = f"""The system has been built. Please review the code based on the following documents:

--- requirements.md ---
{requirements}

--- architecture.md ---
{architecture}
"""

        reviewer.add_message("user", reviewer_context)
    
        print(colored("Reviewer is working...", "cyan"))
        response = reviewer.run()
        print_agent_output("Reviewer", response)

        # 3. Human-in-the-loop (Build Approval)
        print(colored("\n--- Review Report ---", "white", attrs=["bold"]))
        review_content = read_file("test_review.md")
        if not review_content.startswith("Error"):
            print(review_content)
        else:
            print(colored("Warning: test_review.md was not created.", "yellow"))
            
        print(colored("\nDo you approve this build?", "yellow"))
        user_feedback = input("Type 'yes' to finish, or provide feedback to the Builder: ")
        
        if user_feedback.lower() in ["yes", "y", "approve"]:
            break
        else:
            # Feed the review AND user comments back to the Builder
            print(colored("Sending feedback to Builder...", "cyan"))
            builder_feedback = f"""The user has rejected the build.
            
User Feedback: {user_feedback}

Reviewer Findings (from test_review.md):
{review_content}

Please fix the code based on the user feedback and the reviewer's report.
"""
            builder.add_message("user", builder_feedback)

    # Final Output
    print(colored("\n--- Workflow Complete ---", "green", attrs=["bold"]))

if __name__ == "__main__":
    main()
