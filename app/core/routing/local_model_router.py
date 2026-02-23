import time
import socket
import json
import requests

class LocalModelRouter:
    """
    使用本地 Ollama 模型进行任务分类（可选功能）
    
    - 如果安装了 Ollama + Qwen，使用本地模型（更快、更准）
    - 如果没有安装，自动降级到 SmartDispatcher（纯规则+语料匹配）
    - 对用户透明，不影响正常使用
    """
    
    _initialized = False
    _model_name = None
    _available = None  # 缓存可用性状态
    _check_time = 0    # 上次检查时间
    
    # 推荐的快速模型（按优先级排序）
    OLLAMA_MODELS = [
        "qwen3:8b",          # ★ 最佳中英文能力，RTX 4090 流畅运行
        "qwen3:4b",          # 快速备选
        "qwen3:1.7b",        # 轻量备选
        "qwen2.5:7b",        # 旧版但质量好
        "qwen2.5:3b",        # 旧版快速
        "qwen2.5:1.5b",      # 旧版轻量
        "llama3.2:3b",       # 英文为主
    ]
    
    # 分类 Prompt（固定 JSON 格式，确保输出一致）
    # Qwen3 支持 /no_think 模式，跳过思考直接输出，加速分类
    CLASSIFY_PROMPT = '''/no_think
你是任务分类器。只输出 JSON，不要任何解释。

任务类型:
- PAINTER: 用户要求生成/绘制/创作一张图片、照片、壁纸、头像
- FILE_GEN: 用户要求生成 Word/PDF/Excel/PPT 等文件文档
- DOC_ANNOTATE: 用户要求对已有文档进行标注/批注/润色/校对
- RESEARCH: 用户要求深度分析某个主题（需要长篇、系统性回答）
- CODER: 用户要求写代码/编程/调试/实现功能
- SYSTEM: 用户下命令让你执行系统操作（如"打开微信""关机"）
- AGENT: 用户要求执行工具操作（发微信消息、设提醒、浏览器自动化）
- WEB_SEARCH: 用户询问需要实时信息的问题（天气、股价、新闻、比赛结果）
- CHAT: 日常对话、知识问答、闲聊、建议、概念解释

核心判断规则:
1. 用户在**问问题/求知识** → CHAT（即使提到"启动""打开"等词）
2. 用户在**下命令/要求执行** → 对应操作类型
3. "怎么/如何/什么办法/为什么/是什么" = 提问 → 通常是 CHAT
4. 短句+命令语气+具体应用名 = 系统操作 → SYSTEM
5. 提到"写代码/脚本/函数/python" = 编程 → CODER
6. 提到天气/股价/新闻+需要实时数据 → WEB_SEARCH
7. 只提到"研究"但没有深度要求 → CHAT（"研究"日常用法=了解）

正例:
输入: 打开微信
输出: {{"task":"SYSTEM","confidence":0.95}}
输入: 画一只猫
输出: {{"task":"PAINTER","confidence":0.92}}
输入: 写一个快速排序函数
输出: {{"task":"CODER","confidence":0.93}}
输入: 查下明天北京天气
输出: {{"task":"WEB_SEARCH","confidence":0.90}}
输入: 帮我做一个PPT
输出: {{"task":"FILE_GEN","confidence":0.88}}
输入: 标注这篇文档的不当之处
输出: {{"task":"DOC_ANNOTATE","confidence":0.88}}
输入: 给张三发微信说明天开会
输出: {{"task":"AGENT","confidence":0.90}}

反例（容易误判，注意区分）:
输入: 在Windows环境里快速启动bash虚拟环境，一般用什么办法
输出: {{"task":"CHAT","confidence":0.92}}
（分析：虽含"启动"但这是知识提问，不是让你执行启动操作）
输入: python怎么安装第三方库
输出: {{"task":"CHAT","confidence":0.88}}
（分析：问"怎么"=求知识，不是让你写代码）
输入: 什么是docker
输出: {{"task":"CHAT","confidence":0.90}}
输入: 了解一下机器学习
输出: {{"task":"CHAT","confidence":0.85}}
输入: 研究一下这个问题
输出: {{"task":"CHAT","confidence":0.80}}
（分析："研究一下"=日常"了解一下"，不是深度研究）
输入: 帮我深入研究MicroLED的技术原理和发展历程
输出: {{"task":"RESEARCH","confidence":0.90}}
（分析："深入研究"+具体主题+"技术原理"=需要系统性长文）
输入: 写一段自我介绍
输出: {{"task":"CHAT","confidence":0.85}}
（分析："写一段"=短文本输出，不是生成文件）
输入: 帮我写份项目总结Word文档
输出: {{"task":"FILE_GEN","confidence":0.90}}
输入: 搜索怎么用git
输出: {{"task":"CHAT","confidence":0.82}}
（分析：用户要的是知识/教程，不是去网上搜实时信息）
输入: 今天A股涨了吗
输出: {{"task":"WEB_SEARCH","confidence":0.92}}
输入: 帮我把这个文件优化一下
输出: {{"task":"DOC_ANNOTATE","confidence":0.85}}

只输出 JSON：
{{"task":"...","confidence":0.0-1.0}}
'''

    @classmethod
    def is_ollama_available(cls) -> bool:
        """检查 Ollama 是否可用（带缓存，避免频繁检测）"""
        
        # 缓存 30 秒
        if cls._available is not None and (time.time() - cls._check_time) < 30:
            return cls._available
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex(('127.0.0.1', 11434))
            sock.close()
            cls._available = (result == 0)
            cls._check_time = time.time()
            return cls._available
        except:
            cls._available = False
            cls._check_time = time.time()
            return False
    
    @classmethod
    def init_model(cls, model_name: str = None) -> bool:
        """初始化本地模型（静默失败，不影响使用）"""
        if cls._initialized and cls._model_name:
            return True
        
        if not cls.is_ollama_available():
            # 静默返回，不打印错误（避免刷屏）
            return False
        
        # 获取已安装的模型
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code != 200:
                return False
            installed = [m['name'].split(':')[0] + ':' + m['name'].split(':')[1] if ':' in m['name'] else m['name'] 
                        for m in resp.json().get('models', [])]
        except:
            return False
        
        if not installed:
            return False
        
        # 选择可用的最快模型
        target_model = model_name
        if not target_model:
            for m in cls.OLLAMA_MODELS:
                base_name = m.split(':')[0]
                if any(base_name in im for im in installed):
                    for im in installed:
                        if base_name in im:
                            target_model = im
                            break
                    break
        
        if not target_model:
            return False
        
        cls._model_name = target_model
        cls._initialized = True
        print(f"[LocalModelRouter] ✅ 使用本地模型: {target_model}")
        return True
    
    @classmethod
    def classify(cls, user_input: str, timeout: float = 4.0) -> tuple:
        """
        使用本地 Ollama 模型分类任务
        
        返回: (task_type, confidence_str, source) 或 (None, reason, source)
        """
        start = time.time()
        
        # 确保模型可用
        if not cls._initialized:
            if not cls.init_model():
                return None, "❌ ModelNotReady", "Local"
        
        prompt = cls.CLASSIFY_PROMPT
        
        try:
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": cls._model_name,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input[:500]},
                    ],
                    "stream": False,
                    "format": "json",
                    "think": False,  # Qwen3: 禁用思考模式，加速分类
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 80,
                    }
                },
                timeout=timeout
            )
            
            latency = (time.time() - start) * 1000
            
            if resp.status_code != 200:
                return None, f"❌ API Error {resp.status_code}", "Local"
            
            data_json = resp.json()
            raw = (data_json.get("message", {}) or {}).get("content", "")
            if not raw:
                raw = data_json.get("response", "")
            raw = (raw or "").strip()
            valid_tasks = ["PAINTER", "FILE_GEN", "DOC_ANNOTATE", "RESEARCH", "CODER", "SYSTEM", "AGENT", "WEB_SEARCH", "CHAT"]

            # 解析 JSON 输出
            task_type = None
            confidence = 0.0
            try:
                import json as _json
                data = _json.loads(raw)
                task_type = str(data.get("task", "")).strip().upper()
                confidence = float(data.get("confidence", 0.0))
            except Exception:
                # 回退：尝试从纯文本中提取
                raw_upper = raw.upper()
                for t in valid_tasks:
                    if t in raw_upper:
                        task_type = t
                        confidence = 0.5
                        break

            if task_type in valid_tasks and "|" not in task_type and 0.0 <= confidence <= 1.0 and confidence >= 0.45:
                conf_str = f"🤖 Local {confidence:.2f} ({latency:.0f}ms)"
                print(f"[LocalModelRouter] {task_type} {conf_str}")
                return task_type, conf_str, "Local"
            else:
                print(f"[LocalModelRouter] 无法解析结果: {raw[:80]}")
                return None, f"⚠️ ParseError", "Local"
                
        except requests.exceptions.Timeout:
            return None, f"⏱️ Timeout ({timeout}s)", "Local"
        except Exception as e:
            print(f"[LocalModelRouter] 错误: {e}")
            return None, f"❌ Error", "Local"

    # ── 本地模型响应生成（简单问题快速通道） ──

    # 用于响应生成的模型（按偏好排序，比分类模型可以更大）
    OLLAMA_RESPONSE_MODELS = [
        "qwen3:8b",          # ★ 最佳，中英文流畅
        "qwen3:4b",          # 快速备选
        "qwen2.5:7b",        # 旧版质量好
        "qwen2.5:3b",        # 旧版快速
        "llama3.2:3b",
    ]

    _response_model = None   # 用于生成的模型（可能比分类模型大）
    _response_model_inited = False

    @classmethod
    def _init_response_model(cls) -> bool:
        """初始化用于响应生成的本地模型"""
        if cls._response_model_inited and cls._response_model:
            return True
        if not cls.is_ollama_available():
            return False

        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code != 200:
                return False
            installed = [m['name'] for m in resp.json().get('models', [])]
        except Exception:
            return False

        if not installed:
            return False

        # 优先选择更大的生成模型
        for want in cls.OLLAMA_RESPONSE_MODELS:
            base = want.split(':')[0]
            for im in installed:
                if base in im:
                    cls._response_model = im
                    cls._response_model_inited = True
                    print(f"[LocalModelRouter] ✅ 响应生成模型: {im}")
                    return True

        # 回退到分类模型
        if cls._model_name:
            cls._response_model = cls._model_name
            cls._response_model_inited = True
            return True
        return False

    @classmethod
    def is_simple_query(cls, user_input: str, task_type: str, history: list = None) -> bool:
        """
        判断是否为简单问题，可以用本地模型快速回答。
        
        标准：
        - 任务类型是 CHAT
        - 输入较短（≤120 字符）
        - 不需要联网信息 / 深度分析
        - 不涉及文件或图片
        - 历史对话不超过 4 轮（上下文不太复杂）
        """
        if task_type != "CHAT":
            return False

        if not cls.is_ollama_available():
            return False

        text = user_input.strip()

        # 长输入 → 不适合本地小模型
        if len(text) > 120:
            return False

        # 多轮对话上下文太多 → 云模型更好
        if history and len(history) > 8:  # 4 轮 = 8 条 (user+model)
            return False

        # 需要实时数据的关键词 → 必须联网
        realtime_kw = [
            "今天", "现在", "最新", "实时", "天气", "股价", "汇率",
            "新闻", "热点", "价格", "多少钱", "涨", "跌", "比赛",
            "成绩", "排名", "选举", "疫情", "航班", "火车票", "高铁",
        ]
        if any(kw in text for kw in realtime_kw):
            return False

        # 需要深度/专业分析的关键词 → 云模型质量更好
        deep_kw = [
            "深入", "详细", "深度", "系统性", "全面分析",
            "写一篇", "写一份", "报告", "论文", "文档",
        ]
        if any(kw in text for kw in deep_kw):
            return False

        # 涉及代码的 → 云模型更可靠
        code_kw = ["代码", "函数", "脚本", "python", "java", "javascript", "代码", "debug", "bug"]
        if any(kw in text.lower() for kw in code_kw):
            return False

        return True

    @classmethod
    def generate_stream(cls, user_input: str, history: list = None, 
                        system_instruction: str = None, timeout: float = 30.0):
        """
        使用本地 Ollama 模型流式生成响应。
        
        Returns: generator of text chunks, or None if unavailable
        """
        if not cls._init_response_model():
            return None

        # 构建 messages
        messages = []
        sys_prompt = system_instruction or (
            "你是 Koto，一个友善、专业的 AI 助手。"
            "用中文回答用户问题，如果用户用英文则用英文回答。"
            "回答要简洁明了、准确可靠。"
            "如果不确定答案，请诚实说明。"
        )
        messages.append({"role": "system", "content": sys_prompt})

        # 加入历史对话（最多最近 4 轮）
        if history:
            recent = history[-8:]  # 最多 4 轮
            for turn in recent:
                role = "assistant" if turn.get("role") == "model" else turn.get("role", "user")
                parts_text = " ".join(turn.get("parts", []))
                if parts_text.strip():
                    messages.append({"role": role, "content": parts_text[:500]})

        messages.append({"role": "user", "content": user_input})

        def _stream():
            try:
                resp = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": cls._response_model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 2048,
                        }
                    },
                    stream=True,
                    timeout=timeout
                )
                if resp.status_code != 200:
                    return

                import re as _re
                _in_think = False
                _think_buf = ""
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            # 过滤 Qwen3 的 <think>...</think> 思考标签
                            _think_buf += content
                            while True:
                                if _in_think:
                                    end_idx = _think_buf.find("</think>")
                                    if end_idx >= 0:
                                        _think_buf = _think_buf[end_idx + 8:]
                                        _in_think = False
                                    else:
                                        _think_buf = ""  # 仍在思考中，丢弃
                                        break
                                else:
                                    start_idx = _think_buf.find("<think>")
                                    if start_idx >= 0:
                                        before = _think_buf[:start_idx]
                                        if before:
                                            yield before
                                        _think_buf = _think_buf[start_idx + 7:]
                                        _in_think = True
                                    else:
                                        # 没有 think 标签，直接输出
                                        # 保留最后几个字符以防标签被截断
                                        if len(_think_buf) > 10:
                                            yield _think_buf[:-10]
                                            _think_buf = _think_buf[-10:]
                                        break
                        if data.get("done"):
                            # 输出剩余缓冲
                            if _think_buf and not _in_think:
                                yield _think_buf
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"[LocalModelRouter] 流式生成错误: {e}")

        return _stream()
