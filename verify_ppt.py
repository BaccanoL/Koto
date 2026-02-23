import os
import sys
import asyncio
import time
from dotenv import load_dotenv

# Add current directory to path (project root)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables
load_dotenv(os.path.join(current_dir, 'config', 'gemini_config.env'))

# Ensure web module is importable
# Import Flask app factory components (needed for client)
try:
    from web.app import get_client
except ImportError:
    # If that fails, might be path issue
    print("Failed to import web.app")
    sys.exit(1)

from web.ppt_pipeline import PPTGenerationPipeline

def progress_callback(msg, p=None):
    if p is not None:
        print(f"[PROGRESS {p}%] {msg}")
    else:
        print(f"[PROGRESS] {msg}")

def thought_callback(text):
    print(f"[THOUGHT] {text}")

async def run_verification():
    print("Initializing verification...")
    
    # Check if API key is loaded
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment variables.")
        return

    print("Getting AI client...")
    try:
        client = get_client()
    except Exception as e:
        print(f"ERROR: Failed to initialize AI client: {e}")
        return

    print("Initializing PPT Pipeline...")
    pipeline = PPTGenerationPipeline(ai_client=client, workspace_dir=current_dir)

    timestamp = int(time.time())
    output_filename = f"verification_ppt_{timestamp}.pptx"
    output_path = os.path.join(current_dir, "workspace", output_filename)
    
    # Ensure workspace directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"Starting PPT generation: {output_path}")
    
    # Test prompt specifically asking for images and substantial content
    prompt = "Create a detailed presentation about 'The Future of Quantum Computing'. Include sections on Hardware, Algorithms, and Applications. Make sure to include visual metaphors and comparisons."

    try:
        result = await pipeline.generate(
            user_request=prompt,
            output_path=output_path,
            enable_auto_images=True,  # Explicitly enable images
            progress_callback=progress_callback,
            thought_callback=thought_callback
        )
        
        print("\nGeneration Complete!")
        print(f"Result: {result}")
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"File created successfully: {output_path} (Size: {size/1024:.2f} KB)")
            if size < 10000: # 10KB is very small for a PPTX with images
                print("WARNING: File size suggests content might be sparse or images missing.")
            else:
                print("SUCCESS: PPT generated with substantial content.")
        else:
            print("ERROR: Output file not found via os.path.exists.")

    except Exception as e:
        print(f"ERROR during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_verification())
