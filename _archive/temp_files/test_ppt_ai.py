#!/usr/bin/env python3
"""Test PPT generation with AI content planning"""
import os, sys, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dotenv import load_dotenv
load_dotenv('config/gemini_config.env')
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

import httpx
import google.genai as genai
from web.ppt_pipeline import PPTGenerationPipeline
from web.ppt_master import PPTContentPlanner

api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('API_KEY')
proxy = 'http://127.0.0.1:7890'
http_client = httpx.Client(proxy=proxy, timeout=httpx.Timeout(120.0, connect=30.0), verify=False)
client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta', 'httpxClient': http_client})

async def test():
    # Test 1: AI-powered content planning
    print("--- Test: AI Content Planning ---")
    planner = PPTContentPlanner(ai_client=client)
    plan = await planner.plan_content_structure('AI in healthcare')
    outline = plan.get('outline', [])
    print(f"AI Plan sections: {len(outline)}")
    for s in outline:
        t = s.get('title', '?')
        print(f"  - {t}")
    
    # Test 2: Full pipeline with AI
    print("\n--- Test: Full Pipeline with AI ---")
    pipe = PPTGenerationPipeline(ai_client=client)
    out = os.path.join('workspace', 'documents', 'test_ai_ppt.pptx')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = await pipe.generate(user_request='Make a presentation about AI in healthcare', output_path=out)
    
    success = r.get('success')
    output = r.get('output_path')
    error = r.get('error')
    print(f"Pipeline success={success}")
    print(f"Output: {output}")
    if error:
        print(f"Error: {error}")
    if output and os.path.exists(output):
        size = os.path.getsize(output)
        print(f"File: {size} bytes - OK!")
    elif os.path.exists(out):
        size = os.path.getsize(out)
        print(f"File at out: {size} bytes - OK!")
    else:
        print("NO FILE CREATED")
        tb = r.get('traceback', '')
        if tb:
            print(tb[:500])

asyncio.run(test())
