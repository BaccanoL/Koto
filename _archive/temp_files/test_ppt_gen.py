#!/usr/bin/env python3
"""Test PPT generation pipeline end-to-end"""
import os, sys, asyncio, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv('config/gemini_config.env')

api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('API_KEY')
print(f"[1] API KEY found: {bool(api_key)}")

# Test 1: PPTBlueprint.to_dict
print("\n--- Test 1: PPTBlueprint.to_dict ---")
from web.ppt_master import PPTBlueprint, SlideBlueprint, SlideType, ContentDensity
bp = PPTBlueprint(title='test', subtitle='sub')
bp.slides.append(SlideBlueprint(slide_index=0, slide_type=SlideType.TITLE, title='Title'))
try:
    d = bp.to_dict()
    print(f"OK: to_dict keys: {list(d.keys())}")
except Exception as e:
    print(f"FAIL: {e}")

# Test 2: Model name
print("\n--- Test 2: model name ---")
from web.ppt_master import PPTContentPlanner
cp = PPTContentPlanner(ai_client=None)
print(f"model_name: {cp.model_name}")
print("OK" if cp.model_name == "gemini-2.5-flash" else "WRONG MODEL")

# Test 3: Default plan
print("\n--- Test 3: default plan ---")
plan = asyncio.run(cp.plan_content_structure("about AI"))
print(f"OK: {len(plan.get('outline',[]))} sections")

# Test 4: Synthesizer
print("\n--- Test 4: PPTSynthesizer ---")
from web.ppt_synthesizer import PPTSynthesizer
synth = PPTSynthesizer()
bp2 = PPTBlueprint(title='AI', subtitle='Intro')
bp2.slides.append(SlideBlueprint(slide_index=0, slide_type=SlideType.TITLE, title='AI', content=['Intro'], layout_config={}))
bp2.slides.append(SlideBlueprint(slide_index=1, slide_type=SlideType.CONTENT, title='What', content=['ML','DL'], layout_config={}))
bp2.slides.append(SlideBlueprint(slide_index=2, slide_type=SlideType.SUMMARY, title='Thx', content=['Q?'], layout_config={}))
out = os.path.join('workspace', 'documents', 'test_synth.pptx')
os.makedirs(os.path.dirname(out), exist_ok=True)
r = asyncio.run(synth.synthesize_from_blueprint(bp2, out))
print(f"success={r.get('success')}, error={r.get('error')}")
if r.get('success') and os.path.exists(out):
    print(f"FILE: {os.path.getsize(out)} bytes")

# Test 5: Full pipeline NO AI
print("\n--- Test 5: Pipeline without AI ---")
from web.ppt_pipeline import PPTGenerationPipeline
pipe = PPTGenerationPipeline(ai_client=None)
out2 = os.path.join('workspace', 'documents', 'test_noai.pptx')
r2 = asyncio.run(pipe.generate(user_request='about AI PPT', output_path=out2))
print(f"success={r2.get('success')}, output_path={r2.get('output_path')}, error={r2.get('error')}")
if r2.get('success') and os.path.exists(out2):
    print(f"FILE: {os.path.getsize(out2)} bytes OK")
else:
    if r2.get('traceback'):
        print(r2['traceback'][:400])

print("\n=== DONE ===")
