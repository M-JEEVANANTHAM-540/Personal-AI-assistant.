import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY was not found.")
    exit()

client = genai.Client(
    api_key=api_key,
    http_options={"api_version": "v1"}
)

print("JARVIS: Systems operational.")
print("JARVIS: How can I assist you?")
print("Type 'exit' to shut me down.\n")

previous_interaction_id = None

while True:

    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("JARVIS: Shutting down.")
        break

    if not user_input.strip():
        continue

    if previous_interaction_id is None:

        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input=user_input
        )

    else:

        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input=user_input,
            previous_interaction_id=previous_interaction_id
        )

    print(f"\nJARVIS: {interaction.output_text}\n")

    previous_interaction_id = interaction.id