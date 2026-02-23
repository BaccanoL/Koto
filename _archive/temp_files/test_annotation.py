"""测试文档标注完整流程"""
import os, sys, time

# 设置项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置代理
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

from google import genai

# 初始化客户端
client = genai.Client(api_key='AIzaSyCmnMnCSIT4Fm9nAuFDBFaH-RqGbfp1U1Y')

# 测试文件路径
test_file = r"C:\Users\12524\Desktop\Koto\workspace\documents\数字之眼的危机^L7算法的形式主义危机.docx"

print("=" * 60)
print("测试文档标注完整流程")
print("=" * 60)

from web.document_feedback import DocumentFeedbackSystem

feedback = DocumentFeedbackSystem(gemini_client=client)

user_input = "用学术的角度，综合看一下这篇文章，给出评论、标注、和修改意见以及后续方向"

print(f"\n📄 文件: {os.path.basename(test_file)}")
print(f"📝 需求: {user_input}")
print(f"⏰ 开始时间: {time.strftime('%H:%M:%S')}")
print()

start = time.time()
event_count = 0

for progress_event in feedback.full_annotation_loop_streaming(test_file, user_input):
    event_count += 1
    stage = progress_event.get('stage', '?')
    progress = progress_event.get('progress', 0)
    message = progress_event.get('message', '')
    detail = progress_event.get('detail', '')
    
    elapsed = time.time() - start
    print(f"[{elapsed:6.1f}s] [{stage:20s}] {progress:3d}% | {message} | {detail}")
    
    if stage == 'complete':
        result = progress_event.get('result', {})
        print(f"\n{'=' * 60}")
        print(f"✅ 完成！")
        print(f"   applied: {result.get('applied', 0)}")
        print(f"   failed:  {result.get('failed', 0)}")
        print(f"   revised: {result.get('revised_file', 'N/A')}")
        print(f"   总耗时: {elapsed:.1f}s")
        print(f"   事件数: {event_count}")
        break
    
    if stage == 'error':
        print(f"\n❌ 错误！ {message}")
        break

print(f"\n总耗时: {time.time() - start:.1f}s, 共收到 {event_count} 个事件")
