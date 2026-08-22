import os
import json
import subprocess
from datetime import datetime

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from dotenv import load_dotenv
from ollama import chat
import psutil
import platform
import pyttsx3


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# OLLAMA CONFIGURATION
# ============================================================

OLLAMA_MODEL = "qwen3:8b"


# ============================================================
# JARVIS VOICE
# ============================================================

voice_engine = pyttsx3.init()

voice_engine.setProperty("rate", 175)
voice_engine.setProperty("volume", 1.0)


# ============================================================
# WHISPER SPEECH-TO-TEXT
# ============================================================

print("JARVIS: Loading speech recognition system...")

whisper_model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

print("JARVIS: Speech recognition ready.")


def speak(text):
    """Speak JARVIS's response through the computer's speakers."""
    if not text or not text.strip():
        return

    voice_engine.say(text)
    voice_engine.runAndWait()


# ============================================================
# VOICE INPUT
# ============================================================

SAMPLE_RATE = 16000
CHANNELS = 1

SILENCE_THRESHOLD = 0.012
SILENCE_DURATION = 0.8
MAX_RECORDING_DURATION = 20.0
MIN_RECORDING_DURATION = 0.25
CHUNK_DURATION = 0.1


def _audio_level(audio):
    """Return the RMS volume level of a microphone chunk."""
    return float(np.sqrt(np.mean(np.square(audio))))


def record_audio():
    """Wait for speech and record until the user stops speaking."""

    print("\nJARVIS: Listening...", flush=True)

    chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
    silence_chunks_required = max(
        1,
        int(SILENCE_DURATION / CHUNK_DURATION)
    )
    max_chunks = int(MAX_RECORDING_DURATION / CHUNK_DURATION)
    min_chunks = max(
        1,
        int(MIN_RECORDING_DURATION / CHUNK_DURATION)
    )

    chunks = []
    speech_started = False
    silent_chunks = 0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        blocksize=chunk_size
    ) as stream:

        for _ in range(max_chunks):

            audio_chunk, overflowed = stream.read(chunk_size)
            audio_chunk = audio_chunk[:, 0].copy()
            level = _audio_level(audio_chunk)

            if level >= SILENCE_THRESHOLD:
                speech_started = True
                silent_chunks = 0
                chunks.append(audio_chunk)

            elif speech_started:
                chunks.append(audio_chunk)
                silent_chunks += 1

                if silent_chunks >= silence_chunks_required:
                    break

    if not chunks:
        return np.array([], dtype=np.float32)

    audio = np.concatenate(chunks)

    if len(audio) < min_chunks * chunk_size:
        return np.array([], dtype=np.float32)

    return audio


def transcribe_audio(audio):
    """Convert recorded microphone audio to text using Whisper."""

    if audio.size == 0:
        return ""

    segments, info = whisper_model.transcribe(
        audio,
        beam_size=5,
        language="en",
        vad_filter=True
    )

    return " ".join(
        segment.text.strip()
        for segment in segments
    ).strip()


def listen():
    """Wait for speech, detect silence, and transcribe it."""

    audio = record_audio()

    if audio.size == 0:
        return ""

    text = transcribe_audio(audio)

    if text:
        print(f"You: {text}")
    else:
        print("JARVIS: I could not understand that.")

    return text


# ============================================================
# JARVIS TOOLS
# ============================================================

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


# ============================================================
# TOOL SCHEMAS
# ============================================================

get_system_info_tool = {
    "type": "function",
    "name": "get_system_info",
    "description": (
        "Get basic hardware, operating system, "
        "and Python information from the user's computer."
    ),
    "parameters": {
        "type": "object",
        "properties": {}
    }
}


get_current_time_tool = {
    "type": "function",
    "name": "get_current_time",
    "description": (
        "Get the current date and time from "
        "the user's computer."
    ),
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
    "description": (
        "Open an approved application on the user's "
        "Windows computer."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": (
                    "The name of the application to open."
                )
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

- For complex questions, explain the reasoning clearly but avoid
  unnecessary exposition.

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

- Do not repeatedly remind the user that you are an AI unless it is relevant.


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
# OLLAMA INTERACTION
# ============================================================

def stream_interaction(messages):
    """
    Stream a local Ollama interaction and return:
    - generated text
    - requested tool calls
    """

    response = chat(
        model=OLLAMA_MODEL,
        messages=messages,
        tools=available_tools,
        stream=True,
        think=False,
        options={
            "temperature": 0.2
        }
    )

    response_text = ""
    tool_calls = []

    for chunk in response:

        message = getattr(chunk, "message", None)

        if not message:
            continue

        content = getattr(message, "content", "") or ""

        if content:
            response_text += content
            print(content, end="", flush=True)

        current_tool_calls = getattr(
            message,
            "tool_calls",
            None
        )

        if current_tool_calls:
            tool_calls.extend(current_tool_calls)

    return response_text, tool_calls


def normalize_tool_call(tool_call):
    """Convert an Ollama tool call into a predictable structure."""

    function = getattr(tool_call, "function", None)

    if function is None:
        return None

    name = getattr(function, "name", None)
    arguments = getattr(function, "arguments", {})

    if not name:
        return None

    if arguments is None:
        arguments = {}

    return {
        "name": name,
        "arguments": arguments
    }


def execute_ollama_tool_calls(tool_calls):
    """
    Execute Ollama-requested Python functions and return
    Ollama-compatible tool messages.
    """

    tool_messages = []

    for raw_tool_call in tool_calls:

        tool_call = normalize_tool_call(raw_tool_call)

        if not tool_call:
            continue

        function_name = tool_call["name"]
        function_arguments = tool_call["arguments"]

        print(
            f"JARVIS: Executing {function_name}..."
        )

        if function_name not in available_functions:

            result = (
                f"Unknown function requested: "
                f"{function_name}"
            )

        else:

            function_to_call = available_functions[
                function_name
            ]

            try:

                if isinstance(function_arguments, str):
                    function_arguments = json.loads(
                        function_arguments
                    )

                result = function_to_call(
                    **function_arguments
                )

            except Exception as e:

                result = (
                    f"Unable to execute "
                    f"{function_name}: {str(e)}"
                )

        tool_messages.append({
            "role": "tool",
            "tool_name": function_name,
            "content": json.dumps(result)
        })

    return tool_messages


# ============================================================
# START JARVIS
# ============================================================

print("JARVIS: Systems operational.")
print("JARVIS: Local Qwen3 8B model connected.")
print("JARVIS: How can I assist you?")
print("Voice mode is active. Say \"keyboard\" to switch modes.")
print("Say \"exit\" in keyboard mode to shut me down.\n")


# Stores the local conversation history for Ollama.
conversation = [
    {
        "role": "system",
        "content": JARVIS_INSTRUCTIONS
    }
]


# ============================================================
# MAIN CHAT LOOP
# ============================================================

while True:

    try:

        if "voice_mode" not in locals():
            voice_mode = True

        if voice_mode:
            user_input = listen()
        else:
            user_input = input("You: ")


    except KeyboardInterrupt:

        print("\nJARVIS: Shutting down, sir.")
        break

    if not user_input.strip():
        continue

    if user_input.strip().lower() == "keyboard":
        voice_mode = False
        print("JARVIS: Keyboard mode enabled.")
        continue

    if user_input.strip().lower() == "voice":
        voice_mode = True
        print("JARVIS: Voice mode enabled.")
        continue

    if user_input.strip().lower() == "exit":

        print("JARVIS: Shutting down, sir.")
        break


    # ========================================================
    # SEND REQUEST TO LOCAL OLLAMA
    # ========================================================

    try:

        conversation.append({
            "role": "user",
            "content": user_input
        })

        while True:

            print(
                "\nJARVIS: ",
                end="",
                flush=True
            )

            response_text, tool_calls = stream_interaction(
                conversation
            )

            print("\n")

            # Build the assistant message. Ollama requires the
            # tool calls to remain attached to this assistant turn.
            assistant_message = {
                "role": "assistant",
                "content": response_text
            }

            normalized_tool_calls = []

            for raw_tool_call in tool_calls:

                normalized = normalize_tool_call(
                    raw_tool_call
                )

                if normalized:
                    normalized_tool_calls.append(
                        normalized
                    )

            if normalized_tool_calls:

                assistant_message["tool_calls"] = [
                    {
                        "function": {
                            "name": tool_call["name"],
                            "arguments": tool_call["arguments"]
                        }
                    }
                    for tool_call in normalized_tool_calls
                ]

            conversation.append(assistant_message)

            # ==================================================
            # HANDLE TOOL CALLS
            # ==================================================

            if normalized_tool_calls:

                tool_messages = execute_ollama_tool_calls(
                    tool_calls
                )

                conversation.extend(tool_messages)

                continue

            break


        # ====================================================
        # SPEAK FINAL RESPONSE
        # ====================================================

        if response_text.strip():
            speak(response_text)


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        print(
            "\nJARVIS: I'm unable to process that request "
            "at the moment, sir."
        )

        print(
            f"System: {e}\n"
        )
