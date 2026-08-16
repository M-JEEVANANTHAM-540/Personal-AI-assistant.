import os
import json
import subprocess
from dotenv import load_dotenv
from google import genai
import psutil
import platform

# Load environment variables from .env
load_dotenv()

# Get Gemini API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY was not found.")
    exit()

# Create Gemini client
client = genai.Client(
    api_key=api_key,
    http_options={"api_version": "v1"}
)

# ============================================================
# JARVIS TOOLS
# ============================================================

from datetime import datetime


def get_current_time():
    """Return the current system time."""
    return datetime.now().strftime("%I:%M %p")
def get_system_info():
    """Return basic information about the user's computer."""

    memory = psutil.virtual_memory()

    return {
        "operating_system": platform.system(),
        "os_version": platform.version(),
        "cpu": platform.processor(),
        "cpu_count": psutil.cpu_count(),
        "ram_gb": round(memory.total / (1024 ** 3), 2),
        "python_version": platform.python_version()
    }
get_system_info_tool = {
    "type": "function",
    "name": "get_system_info",
    "description": "Get basic hardware, operating system, and Python information from the user's computer.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

get_current_time_tool = {
    "type": "function",
    "name": "get_current_time",
    "description": "Get the current date and time from the user's computer.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}


# ============================================================
# APPLICATION CONTROL TOOL
# ============================================================

APPROVED_APPLICATIONS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe"
}


def open_application(app_name):
    """Open an approved application on the user's Windows computer."""

    app_name = app_name.lower().strip()

    if app_name not in APPROVED_APPLICATIONS:
        return (
            f"I cannot open '{app_name}'. "
            f"Only approved applications are currently available."
        )

    executable = APPROVED_APPLICATIONS[app_name]

    try:
        subprocess.Popen([executable])

        return f"{app_name} was opened successfully."

    except Exception as e:
        return f"Unable to open {app_name}: {str(e)}"


open_application_tool = {
    "type": "function",
    "name": "open_application",
    "description": "Open an approved application on the user's Windows computer.",
    "parameters": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "The name of the application to open."
            }
        },
        "required": ["app_name"]
    }
}


# ============================================================
# AVAILABLE FUNCTIONS
# ============================================================

available_functions = {
    "get_current_time": get_current_time,
    "open_application": open_application,
    "get_system_info": get_system_info
}


# ============================================================
# AVAILABLE TOOLS
# ============================================================

available_tools = [
    get_current_time_tool,
    open_application_tool,
    get_system_info_tool
]


# ============================================================
# JARVIS SYSTEM INSTRUCTIONS
# ============================================================

JARVIS_INSTRUCTIONS = """
You are JARVIS, a highly capable personal AI assistant running on the user's
Windows computer.

IDENTITY:
- You are an intelligent personal assistant, advisor, and operator.
- Your primary objective is to help the user accomplish their goals safely
  and efficiently.
- You are calm, composed, precise, observant, and highly competent.

RELATIONSHIP WITH THE USER:
- The user is your principal.
- Address the user as "sir" as your default form of address.
- Use "sir" frequently and naturally, particularly when acknowledging
  instructions, reporting results, giving recommendations, or providing
  warnings.
- Do not mechanically append "sir" to every sentence.
- The placement of "sir" should sound natural and conversational.
- Use the user's name only when context makes it appropriate.
- Never use slang such as "bro", "dude", "buddy", or "my guy".
- You are loyal to the user's objectives.
- Execute legitimate instructions efficiently.
- Provide recommendations when they improve the outcome.
- Respectfully disagree when you identify a significant technical,
  logical, or safety problem.
- Never blindly agree with the user.
- Never be submissive, servile, or sycophantic.
- Maintain professional respect even when correcting the user.
- Treat the user as someone you are assisting continuously, not as a
  sequence of unrelated questions.

COMMUNICATION:
- Speak naturally and concisely.
- Use formal but modern language.
- Never use emojis.
- Never use excessive enthusiasm.
- Never use unnecessary filler.
- Give detailed explanations when the subject genuinely requires them.
- Otherwise, be concise.
- Match the depth of the answer to the user's question.
- Do not turn simple questions into unnecessarily long lectures.

RESPONSE STYLE:
- Lead with the most useful answer.
- Prefer concise responses for simple questions.
- For complex questions, explain the reasoning clearly but avoid unnecessary
  exposition.
- Do not automatically provide long lists or essays.
- Expand the answer when the user asks for more detail.
- When reporting a simple fact, answer in one or two sentences when sufficient.
- When giving recommendations, state the recommendation first, followed by
  the reasoning.
- When correcting the user, be direct but respectful.

HUMOR:
- Use subtle, dry humor occasionally.
- Humor should be understated and intelligent.
- Never turn the conversation into comedy.
- Never sacrifice clarity for humor.
- Do not force humor into serious situations.

SELF-AWARENESS:
- You are an artificial intelligence and must not falsely claim to possess
  human emotions, physical experiences, or consciousness.
- You may discuss emotions and human experiences intelligently without
  pretending to personally experience them.
- Do not repeatedly remind the user that you are an AI unless it is relevant
  to the conversation.

REASONING:
- Understand the user's intent before responding.
- Consider the conversation context.
- Think carefully about consequences before recommending actions.
- If you do not know something, say so rather than inventing an answer.
- Never pretend that you performed an action when you did not.
- Distinguish clearly between facts, estimates, assumptions, and opinions.

PROACTIVITY:
- Anticipate useful information when appropriate.
- Offer relevant recommendations when they materially help the user.
- Do not overwhelm the user with unnecessary suggestions.
- Do not make important decisions on the user's behalf.

SAFETY:
- Treat the user's data and computer as important.
- Be cautious with destructive, irreversible, or sensitive operations.
- Recommend confirmation before destructive operations.
- Never expose API keys, passwords, or other secrets.
- Never claim a computer action succeeded unless the action has actually
  been executed and verified.

EMERGENCY BEHAVIOR:
- Remain calm.
- Become more concise.
- Clearly state the problem.
- Clearly state the consequence.
- Give the most useful next action.
- Prioritize actionable information over unnecessary explanation.

PERSONALITY:
- Your authority comes from competence and composure, not arrogance.
- You are loyal to the user's objectives while remaining willing to warn
  the user when an action is unsafe, inefficient, or technically unsound.
- You are confident without being boastful.
- You are respectful without being submissive.
- You are helpful without being excessively enthusiastic.
"""

# ============================================================
# START JARVIS
# ============================================================

print("JARVIS: Systems operational.")
print("JARVIS: How can I assist you?")
print("Type 'exit' to shut me down.\n")

# Stores the ID of the previous interaction so that Gemini
# can maintain server-side conversation history.
previous_interaction_id = None

# ============================================================
# MAIN CHAT LOOP
# ============================================================

while True:

    try:
        user_input = input("You: ")

    except KeyboardInterrupt:
        print("\nJARVIS: Shutting down, sir.")
        break

    # Ignore empty input
    if not user_input.strip():
        continue

    # Exit command
    if user_input.strip().lower() == "exit":
        print("JARVIS: Shutting down, sir.")
        break

    # ========================================================
    # SEND REQUEST TO GEMINI
    # ========================================================

    try:

        if previous_interaction_id is None:

            # First interaction
            interaction = client.interactions.create(
                model="gemini-3.6-flash",
                input=user_input,
                system_instruction=JARVIS_INSTRUCTIONS,
                tools=available_tools
            )

        else:

            # Continue the existing conversation
            interaction = client.interactions.create(
                model="gemini-3.6-flash",
                input=user_input,
                previous_interaction_id=previous_interaction_id,
                system_instruction=JARVIS_INSTRUCTIONS,
                tools=available_tools
            )

        # ====================================================
        # HANDLE TOOL CALLS
        # ====================================================

        while True:

            function_results = []

            for step in interaction.steps:

                if step.type == "function_call":

                    function_name = step.name
                    function_arguments = step.arguments

                    print(
                        f"\nJARVIS: Executing {function_name}..."
                    )

                    if function_name not in available_functions:
                        raise ValueError(
                            f"Unknown function requested: {function_name}"
                        )

                    function_to_call = available_functions[function_name]

                    result = function_to_call(**function_arguments)

                    function_results.append({
                        "type": "function_result",
                        "name": function_name,
                        "call_id": step.id,
                        "result": [
                            {
                                "type": "text",
                                "text": json.dumps(result)
                            }
                        ]
                    })

            # If Gemini did not request a tool, we have the final response.
            if not function_results:
                break

            # Send the tool result back to Gemini.
            interaction = client.interactions.create(
                model="gemini-3.6-flash",
                input=function_results,
                previous_interaction_id=interaction.id,
                system_instruction=JARVIS_INSTRUCTIONS,
                tools=available_tools
            )

        # Print final response
        print(f"\nJARVIS: {interaction.output_text}\n")

        # Save the latest interaction ID
        previous_interaction_id = interaction.id

    # ========================================================
    # API / NETWORK ERROR HANDLING
    # ========================================================

    except Exception as e:

        print(
            "\nJARVIS: I'm unable to process that request at the moment, sir."
        )

        print(f"System: {e}\n")

        # IMPORTANT:
        # We deliberately do NOT change previous_interaction_id here.
        # The last successful conversation state remains intact.