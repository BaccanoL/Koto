"""端到端测试：文件上传 -> SSE 流式响应"""
import requests
import time
import json
import sys

url = 'http://127.0.0.1:5000/api/chat/file'
filepath = r'web\uploads\电影时间的计算解析：基于大视觉语言模型的电影连续性研究.docx'

# 禁用代理，直连本地服务器
session = requests.Session()
session.trust_env = False  # 忽略系统代理设置

# 先做健康检查
try:
    r = session.get('http://127.0.0.1:5000/api/health', timeout=5)
    print(f"健康检查: {r.status_code} {r.text[:100]}")
except Exception as e:
    print(f"❌ 服务器未响应: {e}")
    sys.exit(1)

print(f"\n--- 上传文件测试 ---")
print(f"文件: {filepath}")

with open(filepath, 'rb') as f:
    files = {
        'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    }
    data = {
        'session': 'test_stream_doc',
        'message': '把所有不合适的翻译 不符合中文语序逻辑 生硬的地方标注改善',
        'locked_task': '',
        'locked_model': 'auto'
    }
    
    start = time.time()
    try:
        resp = session.post(url, files=files, data=data, stream=True, timeout=300)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        sys.exit(1)
    
    ct = resp.headers.get('Content-Type', '')
    print(f"Content-Type: {ct}")
    print(f"Status: {resp.status_code}")
    print()
    
    if 'text/event-stream' in ct:
        print("✅ 收到 SSE 流式响应！\n")
        count = 0
        last_token = ""
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith('data: '):
                continue
            count += 1
            try:
                evt = json.loads(line[6:])
            except json.JSONDecodeError:
                print(f"  ⚠️ JSON 解析失败: {line[:100]}")
                continue
            
            elapsed = time.time() - start
            t = evt.get('type', '?')
            
            if t == 'classification':
                print(f"  [{elapsed:6.1f}s] 分类: task={evt.get('task')} model={evt.get('model')}")
            elif t == 'progress':
                pct = evt.get('progress', '')
                msg = evt.get('message', '')[:60]
                detail = evt.get('detail', '')[:60]
                print(f"  [{elapsed:6.1f}s] 进度: {pct}% {msg} | {detail}")
            elif t == 'token':
                chunk = evt.get('content', '')
                last_token += chunk
                if len(last_token) > 200 or '\n' in chunk:
                    print(f"  [{elapsed:6.1f}s] 内容: {last_token[:100]}...")
                    last_token = ""
            elif t == 'info':
                print(f"  [{elapsed:6.1f}s] 信息: {evt.get('message', '')[:80]}")
            elif t == 'error':
                print(f"  [{elapsed:6.1f}s] ❌ 错误: {evt.get('message', '')[:200]}")
            elif t == 'done':
                saved = evt.get('saved_files', [])
                summary = evt.get('summary', '')[:200]
                print(f"  [{elapsed:6.1f}s] ✅ 完成!")
                print(f"     保存文件: {saved}")
                print(f"     摘要: {summary}")
                break
            else:
                print(f"  [{elapsed:6.1f}s] 未知类型={t}: {str(evt)[:100]}")
        
        if last_token:
            print(f"  最后内容: {last_token[:200]}")
        
        total = time.time() - start
        print(f"\n--- 总耗时 {total:.1f}s, 共收到 {count} 个 SSE 事件 ---")
    else:
        print("⚠️ 收到 JSON 响应（非流式）")
        try:
            data = resp.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:1000])
        except:
            print(resp.text[:1000])
