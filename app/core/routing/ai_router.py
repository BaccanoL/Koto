import threading
import hashlib
# google.genai.types 延迟到 classify() 内部加载，避免启动时加载 (~4.7s)

class AIRouter:
    """
    基于轻量级 AI 模型的智能任务路由器
    使用 gemini-2.0-flash-lite 进行任务分类
    """
    
    # 路由器专用系统指令
    ROUTER_INSTRUCTION = """你是任务分类器。根据用户输入判断任务类型。只输出一个类型名称。

类型列表:
- PAINTER: 用户要你生成/绘制图片
- FILE_GEN: 用户要你生成Word/PDF/Excel/PPT文件
- DOC_ANNOTATE: 用户要你标注/批注/润色/校对已有文档
- RESEARCH: 用户需要深度系统性研究分析（长篇报告）
- CODER: 用户要你写代码/编程/调试
- SYSTEM: 用户命令你打开/关闭某个具体应用程序
- AGENT: 用户要你执行工具操作（发微信/设提醒/浏览器控制）
- WEB_SEARCH: 用户询问需要实时数据的问题（天气/股价/新闻/比赛）
- CHAT: 闲聊、知识问答、概念解释、教程咨询

关键区分:
- 问知识/教程/方法 → CHAT（即使提到"启动""打开"等词）
- 命令执行操作 → 对应类型
- "了解/研究一下" → CHAT（日常"看看"之意）
- "深入研究/系统分析/技术原理" → RESEARCH

只输出类型名称，如: CHAT"""

    # 缓存最近的分类结果（避免重复调用）
    _cache = {}
    _cache_max_size = 100
    
    @classmethod
    def classify(cls, client, user_input: str, timeout: float = 3.0) -> tuple:
        """
        使用 AI 模型分类任务
        
        Args:
            client: Google GenAI Client instance
            user_input: User prompt
            timeout: Timeout in seconds
            
        返回: (task_type, confidence, source)
        - task_type: 任务类型
        - confidence: 置信度描述
        - source: "AI" 或 "Cache"
        """
        
        # 检查缓存
        cache_key = hashlib.md5(user_input.encode()).hexdigest()[:16]
        if cache_key in cls._cache:
            cached = cls._cache[cache_key]
            print(f"[AIRouter] Cache hit: {cached}")
            return cached[0], cached[1], "Cache"
        
        try:
            result_holder = {'task': None, 'error': None}
            
            def call_model():
                try:
                    from google.genai import types
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-lite",  # 最快的模型
                        contents=user_input,
                        config=types.GenerateContentConfig(
                            system_instruction=cls.ROUTER_INSTRUCTION,
                            max_output_tokens=20,  # 只需要一个词
                            temperature=0.1,  # 低温度，更确定性
                        )
                    )
                    if response.candidates and response.candidates[0].content.parts:
                        text = response.candidates[0].content.parts[0].text.strip().upper()
                        # 清理输出
                        valid_tasks = ["PAINTER", "FILE_GEN", "DOC_ANNOTATE", "RESEARCH", "CODER", "SYSTEM", "AGENT", "WEB_SEARCH", "CHAT"]
                        for task in valid_tasks:
                            if task in text:
                                result_holder['task'] = task
                                return
                        result_holder['task'] = "CHAT"  # 默认
                except Exception as e:
                    result_holder['error'] = str(e)
            
            # 带超时的调用
            thread = threading.Thread(target=call_model, daemon=True)
            thread.start()
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                print(f"[AIRouter] Timeout after {timeout}s")
                return None, "Timeout", "AI"
            
            if result_holder['error']:
                print(f"[AIRouter] Error: {result_holder['error']}")
                return None, "Error", "AI"
            
            task = result_holder['task']
            if task:
                # 缓存结果
                if len(cls._cache) >= cls._cache_max_size:
                    # 清除一半缓存
                    keys = list(cls._cache.keys())[:cls._cache_max_size // 2]
                    for k in keys:
                        del cls._cache[k]
                cls._cache[cache_key] = (task, "🤖 AI")
                
                print(f"[AIRouter] Classified as: {task}")
                return task, "🤖 AI", "AI"
            
            return None, "NoResult", "AI"
            
        except Exception as e:
            print(f"[AIRouter] Exception: {e}")
            return None, "Exception", "AI"
