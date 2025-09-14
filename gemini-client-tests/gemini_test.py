import os
import sys
import google.generativeai as genai

modules_path = os.path.join(os.path.dirname(__file__), 'own-server', 'src')
# print(modules_path)
sys.path.insert(0, modules_path)

genai.configure(api_key=os.environ["GEMINI_API_KEY"]) # API key stored as environmental variable

# Choose your model
model = genai.GenerativeModel("gemini-1.5-flash")  # or gemini-1.5-pro

chat_prompt = "Say hi and tell me a nice quote"
print(f"Prompt: {chat_prompt}")

response = model.generate_content(chat_prompt)
print(f"Response: {response.text}")
