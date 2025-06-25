#So lets do it 
#Here i have created a simple agent to generate ideas on the given topic

from dotenv import load_dotenv
import os
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in your .env file")
client = genai.Client(api_key=api_key) 
model = "models/gemini-2.0-flash"  

user_inp = input("Enter the topic or a subject you want a video of ")
prompt = f"Brainstorm a give me ideas on {user_inp} , and I am passing these ideas to a script writer so make it easy for the script writers to writing their scripts"

contents = [
            types.Content(  
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]

gen_config = types.GenerateContentConfig(response_mime_type="text/plain")

full_answer = ""
for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=gen_config,
        ):
    full_answer += chunk.text or ""


print(full_answer)

