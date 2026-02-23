#!/usr/bin/env python3
import os
import sys
import time
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from web.file_processor import FileProcessor
from web.ppt_pipeline import PPTGenerationPipeline
from web.app import get_client

FILES = [
    r"c:\Users\12524\Desktop\Koto\web\uploads\presentation.docx",
    r"c:\Users\12524\Desktop\Koto\web\uploads\后历史时代 王史纪.pptx",
]


def build_context_text(paths):
    processor = FileProcessor()
    chunks = []
    for path in paths:
        name = os.path.basename(path)
        if not os.path.exists(path):
            chunks.append(f"\n\n=== {name} (Error) ===\n文件不存在\n")
            continue
        try:
            result = processor.process_file(path)
            content = result.get('text_content') or result.get('content', '') or ''
            if len(content) > 50000:
                content = content[:50000] + '...(truncated)'
            chunks.append(f"\n\n=== {name} ===\n{content}\n")
            print(f"[OK] parsed {name}, chars={len(content)}")
        except Exception as e:
            chunks.append(f"\n\n=== {name} (Error) ===\n读取失败: {e}\n")
            print(f"[WARN] parse failed {name}: {e}")
    return ''.join(chunks)


async def main():
    user_input = "基于这两个文件，做一个新的ppt"
    context_text = build_context_text(FILES)
    enhanced_prompt = f"{user_input}\n\n【参考资料】\n基于以下文件生成的 PPT:\n{context_text}"
    if len(enhanced_prompt) > 100000:
        enhanced_prompt = enhanced_prompt[:100000] + "\n...(context truncated)"

    out = os.path.join('workspace', 'documents', f"E2E_RealFiles_{int(time.time())}.pptx")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    client = get_client()
    pipeline = PPTGenerationPipeline(ai_client=client)

    t0 = time.time()
    result = await pipeline.generate(user_request=enhanced_prompt, output_path=out, enable_auto_images=False)
    dt = time.time() - t0

    print("\n=== RESULT ===")
    print(f"success={result.get('success')}")
    print(f"output_path={result.get('output_path')}")
    print(f"error={result.get('error')}")
    print(f"elapsed={dt:.1f}s")

    output_path = result.get('output_path') or out
    if result.get('success') and os.path.exists(output_path):
        print(f"file_exists=True")
        print(f"file_size={os.path.getsize(output_path)}")
    else:
        print("file_exists=False")
        tb = result.get('traceback', '')
        if tb:
            print(tb[:1200])


if __name__ == '__main__':
    asyncio.run(main())
