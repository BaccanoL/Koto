import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv('config/gemini_config.env')
api = os.getenv('GEMINI_API_KEY')
print('API_KEY_OK' if api else 'NO_API_KEY')

client = genai.Client(api_key=api, http_options={'api_version': 'v1beta'})
models = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-2.0-flash-lite',
    'gemini-3-flash-preview',
    'gemini-3-pro-preview',
    'nano-banana-pro-preview',
]

for model in models:
    try:
        resp = client.models.generate_content(
            model=model,
            contents='reply OK',
            config=types.GenerateContentConfig(max_output_tokens=8, temperature=0.1),
        )
        text = (resp.text or '').strip()
        print(f'{model} => OK {text[:40] if text else "<empty>"}')
    except Exception as e:
        print(f'{model} => FAIL {str(e)[:180]}')
