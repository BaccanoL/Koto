#!/usr/bin/env python3
"""Try actual image generation with various models"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dotenv import load_dotenv
load_dotenv('config/gemini_config.env')
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

import httpx, google.genai as genai
from google.genai import types

api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('API_KEY')
proxy = 'http://127.0.0.1:7890'
http_client = httpx.Client(proxy=proxy, timeout=httpx.Timeout(60.0, connect=15.0), verify=False)
client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta', 'httpxClient': http_client})

prompt = "A simple blue circle on white background"

# Method 1: Try generate_content with response_modalities=["IMAGE","TEXT"] (native image gen)
native_image_models = [
    'gemini-2.0-flash-exp',
    'gemini-2.0-flash-preview-image-generation', 
    'gemini-2.0-flash',
    'gemini-2.5-flash',
    'gemini-2.5-flash-preview-04-17',
    'nano-banana-pro-preview',
]

print("=== Method 1: generate_content with IMAGE modality ===")
for model in native_image_models:
    try:
        response = client.models.generate_content(
            model=model,
            contents=f"Generate an image: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )
        # Check if any part has image data
        has_image = False
        if response and response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            has_image = True
                            mime = part.inline_data.mime_type
                            size = len(part.inline_data.data) if part.inline_data.data else 0
                            print(f"  OK IMAGE: {model}  |  {mime}, {size} bytes")
                        elif hasattr(part, 'text') and part.text:
                            pass  # text response
        if not has_image:
            text = response.text[:80] if response and response.text else "no response"
            print(f"  TEXT ONLY: {model}  |  {text}")
    except Exception as e:
        err = str(e)[:120]
        print(f"  FAIL: {model}  |  {err}")

# Method 2: Try images.generate (Imagen API)
print("\n=== Method 2: images.generate (Imagen) ===")
imagen_models = [
    'imagen-3.0-generate-002',
    'imagen-3.0-generate-001',
    'imagen-3.0-fast-generate-001',
    'imagen-4.0-generate-preview-06-06',
]
for model in imagen_models:
    try:
        # Try via REST-like approach
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1)
        )
        if response and response.generated_images:
            img = response.generated_images[0]
            size = len(img.image.image_bytes) if img.image and img.image.image_bytes else 0
            print(f"  OK: {model}  |  {size} bytes")
        else:
            print(f"  EMPTY: {model}")
    except Exception as e:
        err = str(e)[:120]
        print(f"  FAIL: {model}  |  {err}")

print("\n=== DONE ===")
