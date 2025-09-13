import os
import google.generativeai as genai

# Configure with your API key (from AI Studio)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Choose your model
model = genai.GenerativeModel("gemini-1.5-flash")  # or gemini-1.5-pro

chat_prompt = "Say hi"

# Call the model
response = model.generate_content(chat_prompt)

print(response.text)
