#!/usr/bin/env python3
"""Probe available image generation models"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dotenv import load_dotenv
load_dotenv('config/gemini_config.env')

import httpx, google.genai as genai

api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('API_KEY')
proxy = 'http://127.0.0.1:7890'

# Try both v1 and v1beta
for api_ver in ['v1', 'v1alpha']:
    print(f"\n=== API version: {api_ver} ===")
    try:
        http_client = httpx.Client(proxy=proxy, timeout=httpx.Timeout(30.0, connect=10.0), verify=False)
        client = genai.Client(api_key=api_key, http_options={'api_version': api_ver, 'httpxClient': http_client})
        count = 0
        for m in client.models.list():
            name = m.name if hasattr(m, 'name') else str(m)
            desc = getattr(m, 'description', '') or ''
            methods = getattr(m, 'supported_generation_methods', []) or []
            if any(kw in name.lower() for kw in ['image', 'imagen', 'banana', 'nano', 'paint', 'draw']):
                print(f'  {name}  |  methods={methods}')
                count += 1
        if count == 0:
            print("  (no image models found, showing all model names)")
            for m in client.models.list():
                name = m.name if hasattr(m, 'name') else str(m)
                print(f'  {name}')
    except Exception as e:
        print(f"  ERROR: {e}")

# Also try direct model probing
print("\n=== Direct model probing ===")
candidates = [
    'nano-banana-pro-preview',
    'nano-banana-preview', 
    'gemini-2.0-flash-preview-image-generation',
    'gemini-2.0-flash-exp',
    'imagen-3.0-generate-002',
    'imagen-3.0-generate-001',
    'imagen-3.0-fast-generate-001',
    'imagen-4.0-generate-preview-06-06',
    'imagegeneration@006',
    'gemini-2.0-flash',
]

http_client = httpx.Client(proxy=proxy, timeout=httpx.Timeout(15.0, connect=10.0), verify=False)
client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta', 'httpxClient': http_client})

for model_name in candidates:
    try:
        m = client.models.get(model=model_name)
        methods = getattr(m, 'supported_generation_methods', []) or []
        print(f"  OK: {model_name}  |  methods={methods}")
    except Exception as e:
        err = str(e)[:80]
        print(f"  FAIL: {model_name}  |  {err}")
