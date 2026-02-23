#!/usr/bin/env python3
"""Probe round 2: try gemini-3 models and v1 for imagen"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dotenv import load_dotenv
load_dotenv('config/gemini_config.env')

import httpx, google.genai as genai
from google.genai import types

api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('API_KEY')
proxy = 'http://127.0.0.1:7890'
prompt = "A simple blue circle on white background"

# Round 1: gemini-3 models with native image gen (v1beta)
print("=== gemini-3 models (v1beta) with IMAGE modality ===")
http_client = httpx.Client(proxy=proxy, timeout=httpx.Timeout(60.0, connect=15.0), verify=False)
client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta', 'httpxClient': http_client})

g3_models = [
    'gemini-3-flash-preview',
    'gemini-3-pro-preview',
]
for model in g3_models:
    try:
        response = client.models.generate_content(
            model=model,
            contents=f"Generate an image: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )
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
                            pass
        if not has_image:
            text = response.text[:100] if response and response.text else "no response"
            print(f"  TEXT ONLY: {model}  |  {text}")
    except Exception as e:
        err = str(e)[:150]
        print(f"  FAIL: {model}  |  {err}")

# Round 2: Imagen on v1
print("\n=== Imagen models (v1 API) ===")
http_client2 = httpx.Client(proxy=proxy, timeout=httpx.Timeout(60.0, connect=15.0), verify=False)
client2 = genai.Client(api_key=api_key, http_options={'api_version': 'v1', 'httpxClient': http_client2})

imagen_models = [
    'imagen-3.0-generate-002',
    'imagen-3.0-generate-001',
    'imagen-3.0-fast-generate-001',
    'imagen-4.0-generate-preview-06-06',
]
for model in imagen_models:
    try:
        response = client2.models.generate_images(
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
        err = str(e)[:150]
        print(f"  FAIL: {model}  |  {err}")

# Round 3: Try gemini-2.0-flash-001 with image on v1beta
print("\n=== Other models with IMAGE modality (v1beta) ===")
other_models = [
    'gemini-2.0-flash-001',
    'gemini-2.5-pro',
    'gemini-2.5-pro-preview-05-06',
]
for model in other_models:
    try:
        response = client.models.generate_content(
            model=model,
            contents=f"Generate an image: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )
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
        if not has_image:
            text = response.text[:100] if response and response.text else "no response"
            print(f"  TEXT ONLY: {model}  |  {text}")
    except Exception as e:
        err = str(e)[:150]
        print(f"  FAIL: {model}  |  {err}")

print("\n=== DONE ===")
