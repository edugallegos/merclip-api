from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
# Retrieve API key and initialize client
api_key = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

model = "gemini-2.0-flash-exp-image-generation"
contents = ("Please create a cartoon illustration of a cute penguin ice-skating on a frozen pond, with a bright red scarf flapping in the wind, with snowflakes falling gently from the sky.")

response = client.models.generate_content(
    model=model,
    contents=contents,
    config=types.GenerateContentConfig(response_modalities=['Text', 'Image'])
)

for i, part in enumerate(response.candidates[0].content.parts):
    print(f"Part {i}")
    print("Type:", type(part))
    print("Text:", getattr(part, "text", None))
    if getattr(part, "inline_data", None):
        print("MIME:", part.inline_data.mime_type)
        print("Data length:", len(part.inline_data.data))

for part in response.candidates[0].content.parts:
  if part.text is not None:
    print(part.text)
  elif part.inline_data is not None:
    image = Image.open(BytesIO(part.inline_data.data))
    image.save('gemini-native-image.png')