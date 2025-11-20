import os

from openai import OpenAI
import anthropic
import google.generativeai as genai

# Configure the API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Create the model
model = genai.GenerativeModel("gemini-2.0-flash")

# Generate response
response = model.generate_content("hello world")

print(response.text)



client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "hello world"}
    ]
)

print(completion.choices[0].message.content)

claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

message = claude_client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "hello world"}
    ]
)

print(message.content[0].text)