from typing import Dict, Any, Tuple, List, Optional
import time
import re

# 延迟导入 - 这些模块仅在运行时方法调用时加载，避免启动时加载 google.genai (~4.7s) 和 requests (~0.5s)
# from app.core.routing.local_model_router import LocalModelRouter
# from app.core.routing.ai_router import AIRouter
# from app.core.routing.task_decomposer import TaskDecomposer
# from app.core.routing.local_planner import LocalPlanner

def _get_local_model_router():
    from app.core.routing.local_model_router import LocalModelRouter
    return LocalModelRouter

def _get_ai_router():
    from app.core.routing.ai_router import AIRouter
    return AIRouter

def _get_task_decomposer():
    from app.core.routing.task_decomposer import TaskDecomposer
    return TaskDecomposer

def _get_local_planner():
    from app.core.routing.local_planner import LocalPlanner
    return LocalPlanner

class SmartDispatcher:
    """
    混合智能路由算法
    1. 首先尝试 AI 路由器（快速、智能）
    2. 如果 AI 超时或失败，回退到本地算法
    """
    
    # 是否启用 AI 路由
    USE_AI_ROUTER = True
    
    # 依赖注入容器
    _dependencies = {
        "LocalExecutor": None,
        "ContextAnalyzer": None,
        "WebSearcher": None,
        "MODEL_MAP": {},
        "client": None
    }
    
    @classmethod
    def configure(cls, local_executor, context_analyzer, web_searcher, model_map, client):
        """配置外部依赖"""
        cls._dependencies["LocalExecutor"] = local_executor
        cls._dependencies["ContextAnalyzer"] = context_analyzer
        cls._dependencies["WebSearcher"] = web_searcher
        cls._dependencies["MODEL_MAP"] = model_map
        cls._dependencies["client"] = client

    # 任务语料库 - 每个任务的典型表达方式 (Simplified for brevity, but should be full list)
    TASK_CORPUS = {
        "PAINTER": [
            "画一张图", "帮我画", "生成图片", "画个图", "来张图", "要张图片",
            "做一张图", "做张图", "做个图", "做图", "出一张图", "出张图",
            "画壁纸", "画头像", "画插画", "画海报", "画logo", "画风景",
            "绘制", "作画", "创作图像", "设计图片", "图片生成",
            "画一个", "画只", "画朵", "画座", "画个人物",
            "生成一张", "生成一幅", "创作一张", "制作一张图",
            "可爱图", "帅气图", "美图", "萌图", "图片",
            "赛博朋克风格", "二次元风格", "写实风格", "水彩画", "油画风格",
            "动漫风格", "卡通风格", "像素风格", "手绘风格",
            "画个角色", "人物图", "角色图", "立绘", "头像图",
            "生成照片", "一张照片", "照片", "来张照片", "要张照片",
            "明日香", "绑菜", "初音", "雷姆", "蕾姆", "蕾米", "琪亚娜",
            "生成一张xxx的照片", "xxx的图片", "xxx的照片",
            "修改图片", "编辑照片", "修改照片", "换背景", "换底色",
            "把背景", "把底色", "背景改成", "底色改成", "换成蓝色",
            "换成白色", "换成红色", "证件照", "抠图", "去背景",
            "修图", "P图", "美化", "滤镜", "调色",
            "draw me", "generate image", "create picture", "make artwork",
            "paint a", "illustration of", "wallpaper of", "portrait of",
            "make an image", "create an image", "generate a picture",
            "edit image", "change background", "modify photo",
            "generate a photo", "photo of", "picture of",
        ],
        "CODER": [
            "写代码", "编写程序", "写个脚本", "代码实现", "编程实现",
            "帮我写个函数", "代码怎么写", "这段代码", "修复bug", "调试",
            "python实现", "javascript代码", "用java写", "算法实现",
            "数据结构", "排序算法", "网页开发", "后端开发", "API接口",
            "数据库查询", "sql语句", "正则表达式", "爬虫",
            "write code", "implement function", "debug this", "fix bug",
            "python script", "javascript code", "coding", "programming",
        ],
        "FILE_GEN": [
            "生成pdf", "创建word", "生成word", "导出word", "做个word文档", 
            "写份word报告", "导出excel", "生成excel表格",
            "制作简历", "写份合同", "生成表格", "做ppt", "制作ppt", "生成幻灯片",
            "文档模板", "报告模板", "生成文件", "输出文档", "保存为文档",
            ".docx", ".pdf", ".xlsx", ".pptx",
            "文档标注", "批注修改", "全文润色", "docx润色", "word文档改写",
            "改写成更通顺", "语序不通顺", "翻译腔修改", "用中文语序改", 
            "校对文稿", "审校文档", "纠错", "文档批注", "文档修改",
            "create pdf", "generate word", "make document", "export excel",
            "create resume", "generate file", "save as document",
        ],
        "RESEARCH": [
            "深入分析", "详细研究", "全面调研", "系统分析", "深度解读",
            "论文分析", "学术研究", "技术原理", "底层机制", "架构设计",
            "对比分析", "优缺点分析", "历史演变", "发展趋势",
            "为什么", "原理是什么", "如何工作", "深入理解",
            "deep analysis", "research on", "in-depth study", "comprehensive review",
            "technical principle", "architecture design", "compare and contrast",
        ],
        "WEB_SEARCH": [
            "天气", "气温", "下雨吗", "下雪吗", "温度多少", "天气怎么样",
            "今天天气", "明天天气", "这周天气", "天气预报", "会下雨",
            "北京天气", "上海天气", "深圳天气", "杭州天气",
            "最新消息", "今天新闻", "现在", "实时", "最近发生",
            "最新", "今日", "当前", "此刻",
            "股价多少", "现在汇率", "比特币价格", "黄金价格",
            "比分", "比赛结果", "谁赢了",
            "weather", "temperature", "forecast", "latest news", "current price",
        ],
        "FILE_OP": [
            "读取文件", "打开文件", "查看文件", "读文件", "看看文件内容",
            "文件列表", "列出文件", "目录下有什么", "文件夹里有",
            "workspace里", "工作区文件",
            "自动归纳文件夹", "自动整理文件夹", "归纳这个路径", "整理这个目录", "微信文件归纳",
            "批量", "批量转换", "批量重命名", "批量归档", "批量压缩", "抽取文本", "提取文本", "格式转换",
            "read file", "open file", "list files", "show directory",
        ],
        "FILE_EDIT": [
            "修改文件", "编辑文件", "改文件", "改一下", "修改一下",
            "替换", "把xxx改成", "将xxx改为", "把xxx换成", "改成xxx",
            "删除第", "删除行", "去掉第", "插入", "添加一行", "加一行",
            "在第几行", "第几行改成", "第几行插入", "第几行之后",
            "文件里的", "代码中的", "脚本里的", "配置文件",
            "修复文件", "更新文件", "追加内容", "末尾添加",
            "edit file", "modify file", "change file", "replace in file",
            "delete line", "insert line", "append to file", "update file",
        ],
        "FILE_SEARCH": [
            "找文件", "查找文件", "搜索文件", "找一下", "查一下", "搜一下",
            "哪个文件", "哪些文件", "文件在哪", "有什么文件",
            "包含xxx的文件", "内容是xxx", "文件内容", "搜索内容",
            "找到", "查到", "之前", "以前", "处理过", "生成过",
            "那个文件", "那份文件", "哪份文件", "哪个文档",
            "关于xxx的文件", "xxx相关的文件",
            "find file", "search file", "locate file", "which file",
            "file contains", "file with", "search for", "look for file",
        ],
        "CHAT": [
            "你好", "在吗", "聊聊", "说说", "讲个笑话", "有空吗",
            "怎么样", "是什么", "什么是", "介绍一下", "介绍下",
            "推荐一下", "建议", "帮忙", "能不能", "可以吗",
            "谢谢", "感谢", "再见", "晚安",
            "了解", "想了解", "我想知道", "告诉我", "讲讲", "说一下", "说说看",
            "解释一下", "是啥", "有什么", "怎么回事", "为啥",
            "能介绍", "帮我介绍", "给我讲讲", "谈谈",
            "写一段", "写点", "写个介绍", "简单介绍", "简短介绍",
            "产品介绍", "公司介绍", "项目介绍", "功能介绍",
            "写一篇", "写几句", "写点内容", "文字说明", "文案",
            "口号", "标语", "广告词", "宣传语",
            "hello", "hi there", "how are you", "what is", "tell me about",
            "can you", "please help", "thanks", "recommend", "suggest",
            "explain", "describe", "I want to know", "I'd like to learn",
            "write a brief", "write some text", "short description", "introduction of",
        ],
        "SYSTEM": [
            "系统时间", "当前时间", "几点了", "今天几号", "日期", "星期几",
            "关机", "重启", "休眠", "睡眠", "截图", "搜索",
            "打开", "启动", "运行", "关闭", "退出", "杀死",
            "系统状态", "电脑状态", "系统信息", "电脑信息", "配置", "内存", "cpu", "硬盘",
            "what time is it", "current time", "date today", "shutdown", "restart",
        ],
    }

    # 预计算特征 (字符级 n-gram)
    _features = None
    _task_vectors = None
    
    @classmethod
    def _init_features(cls):
        """初始化特征向量 (懒加载)"""
        if cls._features is not None:
            return
        
        all_ngrams = set()
        for corpus in cls.TASK_CORPUS.values():
            for text in corpus:
                ngrams = cls._extract_ngrams(text)
                all_ngrams.update(ngrams)
        
        cls._features = list(all_ngrams)
        
        cls._task_vectors = {}
        for task, corpus in cls.TASK_CORPUS.items():
            vectors = [cls._text_to_vector(text) for text in corpus]
            avg_vector = [sum(v[i] for v in vectors) / len(vectors) for i in range(len(cls._features))]
            cls._task_vectors[task] = avg_vector

    @classmethod
    def _compute_similarity_scores(cls, user_input: str) -> dict:
        """计算各任务的相似度分数"""
        if cls._features is None or cls._task_vectors is None:
            cls._init_features()
        user_vector = cls._text_to_vector(user_input)
        return {
            task: cls._cosine_similarity(user_vector, task_vector)
            for task, task_vector in cls._task_vectors.items()
        }

    @classmethod
    def _build_routing_list(cls, scores: dict, boosts: dict = None, reasons: dict = None, top_k: int = 6) -> list:
        """构建路由分配列表（用于可视化展示）"""
        boosts = boosts or {}
        reasons = reasons or {}
        routing = []
        for task, score in scores.items():
            final_score = max(score, boosts.get(task, 0))
            reason_list = reasons.get(task, [])
            if not reason_list:
                reason_list = ["similarity"]
            routing.append({
                "task": task,
                "score": float(final_score),
                "reason": " + ".join(reason_list)
            })
        routing.sort(key=lambda x: x["score"], reverse=True)
        return routing[:top_k]
    
    @staticmethod
    def _extract_ngrams(text, n=2):
        """提取字符级 n-gram"""
        text = text.lower().strip()
        ngrams = set()
        for char in text:
            if char.strip():
                ngrams.add(char)
        for i in range(len(text) - 1):
            if text[i:i+2].strip():
                ngrams.add(text[i:i+2])
        return ngrams
    
    @classmethod
    def _quick_task_hint(cls, user_input: str) -> str:
        text_lower = user_input.lower()
        if any(k in text_lower for k in ["画", "图", "照片", "生成图", "绘制"]):
            return "PAINTER"
        if any(k in text_lower for k in ["代码", "编程", "python", "javascript", "函数"]):
            return "CODER"
        if any(k in text_lower for k in ["查", "搜索", "价格", "天气", "新闻"]):
            return "WEB_SEARCH"
        if any(k in text_lower for k in ["word", "pdf", "docx", "表格", "文档", "报告", "生成", "做成", "标注", "批注", "润色", "改写", "校对", "审校", "修订", "纠错"]):
            return "FILE_GEN"
        if any(k in text_lower for k in ["研究", "分析", "深入", "介绍"]):
            return "RESEARCH"
        return "CHAT"
    
    @classmethod
    def _text_to_vector(cls, text):
        if cls._features is None:
            cls._init_features()
        ngrams = cls._extract_ngrams(text)
        vector = [1 if f in ngrams else 0 for f in cls._features]
        return vector
    
    @staticmethod
    def _cosine_similarity(v1, v2):
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0
        return dot_product / (norm1 * norm2)
    
    @classmethod
    def _get_dep(cls, name):
        """Helper to get dependency safely"""
        return cls._dependencies.get(name)

    @staticmethod
    def _should_use_annotation_system(user_input, has_file=False):
        """Simplistic check if annotation system should be used"""
        # This logic was previously inline or imported, implementing basic check here
        keywords = ["标注", "批注", "润色", "改写", "校对", "审校", "修订", "纠错", "改善", "优化", "修改"]
        quality_words = ["不合适", "生硬", "翻译腔", "语序", "用词", "逻辑", "问题"]
        target_words = ["翻译", "文章", "文档", "内容", "文本", "段落", "句子", "字词"]
        
        if not has_file:
            return False
            
        has_kw = any(k in user_input for k in keywords)
        has_qw = any(q in user_input for q in quality_words)
        has_target = any(t in user_input for t in target_words)
        
        return has_kw or (has_qw and has_target)

    @classmethod
    def analyze(cls, user_input: str, history=None, file_context=None):
        """
        智能分析用户输入，返回最匹配的任务类型
        优先级：规则检测 > 本地快速模型 > RAG > 远程AI > 本地语料
        
        返回: (task_type, confidence_info, context_info)
        """
        start_time = time.time()
        
        # Get dependencies
        LocalExecutor = cls._get_dep("LocalExecutor")
        ContextAnalyzer = cls._get_dep("ContextAnalyzer")
        WebSearcher = cls._get_dep("WebSearcher")
        client = cls._get_dep("client")
        
        # 初始化特征 (首次调用)
        cls._init_features()
        
        user_lower = user_input.lower().strip()
        context_info = None
        similarity_scores = cls._compute_similarity_scores(user_input)
        base_routing_list = cls._build_routing_list(similarity_scores)
        
        # === 0. Force Plan Mode (New Feature) ===
        if user_input.strip().startswith("/plan ") or "请制定计划" in user_input or "拆解任务" in user_input:
            context_info = {"complexity": "complex", "is_multi_step_task": True}
            context_info["multi_step_info"] = {
                "pattern": "forced_plan",
                "description": "User forced planning mode"
            }
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores, 
                boosts={"MULTI_STEP": 1.0},
                reasons={"MULTI_STEP": ["user_forced"]}
            )
            return "MULTI_STEP", "🛠️ Forced-Plan", context_info
        
        # === 优先：文件附件处理 logic ===
        if file_context and file_context.get("has_file"):
            file_ext = file_context.get("file_type", "")
            edit_keywords = ["修改", "更改", "标注", "批注", "润色", "改写", "校对", "审校", "修订", "纠错", "改善", "优化", "调整"]
            has_edit_intent = any(kw in user_lower for kw in edit_keywords)
            
            if has_edit_intent and file_ext in [".docx", ".doc"]:
                context_info = {"complexity": "complex"}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores, 
                    boosts={"DOC_ANNOTATE": 1.0},
                    reasons={"DOC_ANNOTATE": ["rule:doc_annotate"]}
                )
                print(f"[SmartDispatcher] 📄 检测到 Word 文档标注请求: {file_ext}")
                return "DOC_ANNOTATE", "📄 Doc-Annotate", context_info
            elif has_edit_intent and file_ext in [".md", ".txt"]:
                context_info = {"complexity": "complex", "is_multi_step_task": True}
                context_info["multi_step_info"] = {
                    "pattern": "document_workflow",
                    "description": "文档智能编辑工作流"
                }
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores, 
                    boosts={"MULTI_STEP": 1.0},
                    reasons={"MULTI_STEP": ["rule:doc_workflow"]}
                )
                print(f"[SmartDispatcher] 📄 检测到文件编辑请求: {file_ext}")
                return "MULTI_STEP", "📄 Doc-Workflow", context_info

        # === 快速通道: 超短输入 ===
        if len(user_input) <= 3:
            if LocalExecutor and LocalExecutor.is_system_command(user_input):
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"SYSTEM": 1.0},
                    reasons={"SYSTEM": ["rule:standalone_command"]}
                )
                return "SYSTEM", "🖥️ Rule-Detected", context_info
            return "CHAT", "⚡ Quick", None

        # === 本地 Ollama 路由（参考信号，不独裁） ===
        local_task, local_confidence, local_source = _get_local_model_router().classify(user_input, timeout=4.0)
        if local_task:
            if local_task == "CHAT" and WebSearcher and WebSearcher.needs_web_search(user_input):
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"WEB_SEARCH": 0.95},
                    reasons={"WEB_SEARCH": ["override:chat_to_web_search"]}
                )
                return "WEB_SEARCH", "🌐 Override-Detected", context_info

            if LocalExecutor and LocalExecutor.is_system_command(user_input) and local_task != "SYSTEM":
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"SYSTEM": 0.95},
                    reasons={"SYSTEM": ["local_override:system"]}
                )
                return "SYSTEM", "🖥️ Local-Override", context_info

            agent_overrides = [
                r"发微信", r"回微信", r"微信发", r"微信回",
                r"给.{1,6}发消息", r"给.{1,6}发微信",
                r"浏览器打开", r"点击.{1,6}按钮",
            ]
            if any(re.search(p, user_lower) for p in agent_overrides):
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"AGENT": 0.95},
                    reasons={"AGENT": ["local_override:agent"]}
                )
                return "AGENT", "🤖 Local-Override", context_info

            ticket_keywords = ["12306", "火车票", "高铁票", "动车票"]
            if any(k in user_lower for k in ticket_keywords):
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"AGENT": 0.95},
                    reasons={"AGENT": ["local_override:ticket"]}
                )
                return "AGENT", "🤖 Local-Override", context_info

            _easily_confused = {"DOC_ANNOTATE", "FILE_GEN"}
            if local_task in _easily_confused:
                has_file = file_context and file_context.get("has_file")
                if not has_file:
                    print(f"[SmartDispatcher] ⚠️ 本地模型返回 {local_task} 但无文件上下文，跳过")
                    pass 
                else:
                    context_info = context_info or {}
                    context_info["routing_list"] = cls._build_routing_list(
                        similarity_scores,
                        boosts={local_task: 0.9},
                        reasons={local_task: ["local_model_with_file"]}
                    )
                    return local_task, f"{local_confidence}", context_info
            else:
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={local_task: 0.9},
                    reasons={local_task: ["local_model"]}
                )
                return local_task, f"{local_confidence}", context_info

        # === 深度文档请求直通 FILE_GEN ===
        deep_doc_keywords = ["深度", "详细", "研究", "全面", "技术", "报告", "综述", "whitepaper", "word", "docx", "论文", "分析"]
        _file_format_kw = ["word", "doc", "docx", "pdf", "报告", "文档", "whitepaper", "论文", "综述"]
        if any(k in user_lower for k in deep_doc_keywords) and any(k in user_lower for k in _file_format_kw):
            context_info = {"complexity": "complex"}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"FILE_GEN": 1.0},
                reasons={"FILE_GEN": ["rule:deep-doc"]}
            )
            return "FILE_GEN", "📄 Rule-Detected", context_info
        
        # === 规则检测 ===
        
        if file_context and file_context.get("has_file"):
            _fc_ext = file_context.get("file_type", "")
            if _fc_ext in [".doc", ".docx"]:
                try:
                    if cls._should_use_annotation_system(user_input, has_file=True):
                        context_info = {"complexity": "complex"}
                        context_info["routing_list"] = cls._build_routing_list(
                            similarity_scores,
                            boosts={"DOC_ANNOTATE": 1.0},
                            reasons={"DOC_ANNOTATE": ["rule:annotation_with_file"]}
                        )
                        return "DOC_ANNOTATE", "📄 Annotation-Strict", context_info
                except Exception:
                    pass

        _ppt_direct_keywords = ["ppt", "幻灯片", "演示文稿", "presentation", "slide", "slides", ".pptx"]
        _ppt_action_words = ["做", "生成", "创建", "制作", "做一个", "做个", "帮我做", "帮我生成"]
        if any(k in user_lower for k in _ppt_direct_keywords) and any(a in user_lower for a in _ppt_action_words):
            context_info = {"complexity": "complex"}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"FILE_GEN": 1.0},
                reasons={"FILE_GEN": ["rule:ppt_direct"]}
            )
            print(f"[SmartDispatcher] 🎯 PPT 请求直通 FILE_GEN 专用管线")
            return "FILE_GEN", "📄 PPT-Direct", context_info

        if LocalExecutor and LocalExecutor.is_system_command(user_input):
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"SYSTEM": 0.9},
                reasons={"SYSTEM": ["rule:system"]}
            )
            return "SYSTEM", "🖥️ Rule-Detected", context_info

        _agent_keywords = [
            "发微信", "回微信", "微信发", "微信回", "给.*发消息", "给.*发微信",
            "设日程", "添加日程", "日历", "安排会议", "约.*时间",
            "删除日程", "取消日程", "列出日程", "查看日程",
            "提醒我", "让我", "通知我",
            "列出提醒", "取消提醒", "删除提醒", "有.*提醒", "查看提醒",
            "读取文件", "读文件", "看文件", "读取.*文件", "文件内容",
            "列出.*文件", "目录下.*文件", "有什么文件", "有哪些文件",
            "搜本地", "找文件", "查找.*文件",
            "写文件", "写入文件", "保存.*文件", "保存到.*文件",
            "workspace", "工作区",
            "剪贴板", "粘贴板", "剪切板", "复制了什么", "最近复制",
            "复制历史", "复制记录",
            "读取文档", "读文档", "打开文档",
            "打开网页", "浏览器打开", "访问.*网站",
            "浏览器截图", "网页截图", "截个图",
            "点击.*元素", "点击.*按钮", "输入.*文本",
            "获取.*文本", "获取网页.*内容",
        ]
        _agent_patterns = [
            "然后", "接着", "顺便", "再", "之后", "完成后",
            "帮我.*找.*然后", "先.*再.*", ".*完了.*",
            "保存到.*txt", "保存到.*文件", "写到.*文件",
        ]
        
        has_agent_keyword = any(re.search(k, user_lower) for k in _agent_keywords)
        has_agent_pattern = any(re.search(p, user_lower) for p in _agent_patterns)
        
        _question_words = ["怎么", "如何", "什么办法", "什么方法", "是什么", "什么是",
                          "为什么", "能不能", "可以吗", "怎样", "一般用", "哪些",
                          "用什么", "讲讲", "说说", "介绍", "教程", "原理",
                          "how to", "what is", "why", "which"]
        is_question = any(qw in user_lower for qw in _question_words)
        
        if (has_agent_keyword or (has_agent_pattern and len(user_input) > 15)) and not is_question:
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"AGENT": 1.0},
                reasons={"AGENT": ["rule:agent_tools"]}
            )
            print(f"[SmartDispatcher] 🤖 检测到 Agent 任务，使用工具调用")
            return "AGENT", "🤖 Agent-Tools", context_info

        _LocalPlanner = _get_local_planner()
        if _LocalPlanner.can_plan(user_input):
            plan = _LocalPlanner.plan(user_input)
            if plan and plan.get("use_planner") and plan.get("steps"):
                context_info = context_info or {}
                context_info["is_multi_step_task"] = True
                context_info["multi_step_info"] = {
                    "pattern": "local_plan",
                    "subtasks": plan.get("steps", [])
                }
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={"MULTI_STEP": 0.95},
                    reasons={"MULTI_STEP": ["local_planner"]}
                )
                return "MULTI_STEP", "🧭 Local-Plan", context_info

        initial_task_hint = cls._quick_task_hint(user_input)
        compound_info = _get_task_decomposer().detect_compound_task(user_input, initial_task_hint)
        
        if compound_info["is_compound"]:
            context_info = {
                "is_multi_step_task": True,
                "multi_step_info": compound_info
            }
            context_info["routing_list"] = base_routing_list
            return "MULTI_STEP", "🔄 Multi-Step", context_info

        if history and len(history) >= 2 and ContextAnalyzer:
            context_info = ContextAnalyzer.analyze_context(user_input, history)
            if context_info.get("is_continuation") and context_info.get("related_task") == "WEB_SEARCH":
                search_verbs = ["查", "搜", "搜索", "查询", "找", "再找", "再查", "再搜", "再看看"]
                if any(v in user_lower for v in search_verbs):
                    context_info["routing_list"] = cls._build_routing_list(
                        similarity_scores,
                        boosts={"WEB_SEARCH": 0.9},
                        reasons={"WEB_SEARCH": ["rag:search_followup"]}
                    )
                    return "WEB_SEARCH", "🌐 RAG-Followup", context_info
        
        file_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"]
        file_type_words = ["pdf", "word", "excel", "ppt", "docx", "文档", "报告", "简历", "合同", "表格", "幻灯片", "计划", "方案", "提案", "建议书", "会议记录"]
        file_action_words = [
            "生成", "创建", "导出", "写份", "写个", "写一个", "做个", "做一个", "制作", "输出", "编写", "撰写", "组织"
        ]
        
        has_extension = any(ext in user_lower for ext in file_extensions)
        has_file_type = any(ft in user_lower for ft in file_type_words)
        has_action = any(act in user_lower for act in file_action_words)
        has_write_file = ("写" in user_lower or "帮我写" in user_lower or "帮我" in user_lower) and (has_file_type or any(w in user_lower for w in ["计划", "方案", "报告"]))
        
        short_text_patterns = ["写一段", "写点", "介绍一下", "介绍下", "说说", "讲讲", "聊聊", "谈谈"]
        is_short_text_request = any(p in user_lower for p in short_text_patterns)
        
        convert_patterns = [
            "把这个做成", "把它做成", "把这份做成",
            "做成word", "做成pdf", "做成文档",
            "转成word", "转成pdf", "导出word", "导出pdf"
        ]
        is_convert_request = any(p in user_lower for p in convert_patterns)
        
        edit_markers = ["标注", "批注", "润色", "改写", "校对", "审校", "修订", "纠错"]
        has_edit_marker = any(m in user_lower for m in edit_markers) and has_file_type
        
        is_file_gen = False
        if not is_short_text_request:
            is_file_gen = (has_extension and has_action) or \
                          (has_file_type and (has_action or has_write_file)) or \
                          is_convert_request or \
                          has_edit_marker
        
        if is_file_gen:
            complex_markers = ["分析", "整理", "转换", "标注", "批注", "润色", "改写", "校对", "审校", "修订", "纠错", "翻译腔", "语序", "生硬"]
            context_info = {"complexity": "complex" if any(kw in user_lower for kw in complex_markers) else "normal"}
            if is_convert_request and history and len(history) >= 2 and ContextAnalyzer:
                context_info.update(ContextAnalyzer.analyze_context(user_input, history))
                context_info["continuation_type"] = "convert"
                context_info["related_task"] = "FILE_GEN"
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"FILE_GEN": 0.95},
                reasons={"FILE_GEN": ["rule:file_gen"]}
            )
            
            return "FILE_GEN", "📄 Rule-Detected", context_info
        
        research_markers = [
            "详细研究", "深入研究", "深入分析", "详细分析", "全面分析", "系统分析",
            "深度解读", "详细介绍", "充分介绍", "技术原理", "底层机制",
            "对比分析", "优缺点分析", "research", "in-depth"
        ]
        if any(m in user_lower for m in research_markers):
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"RESEARCH": 0.9},
                reasons={"RESEARCH": ["rule:research"]}
            )
            return "RESEARCH", "📚 Rule-Detected", context_info
        
        paint_chars = set("画绘")
        paint_words = ["图片", "图像", "壁纸", "头像", "插画", "海报", "照片", "draw", "paint", "image", "picture", "photo"]
        paint_actions = ["做一张图", "做张图", "做个图", "来张图", "生成图", "出张图", "一张图", "一幅图", "一张照片", "来张照片", "生成照片", "生成一张"]
        paint_modify = ["新的图", "新图片", "重新生成", "再生成", "再画", "换一张", "再来一张"]
        paint_verbs = ["做", "生成", "创作", "制作", "来"]
        
        if any(c in user_lower for c in paint_chars) or any(w in user_lower for w in paint_words) or \
           any(a in user_lower for a in paint_actions) or any(m in user_lower for m in paint_modify) or \
           ("图" in user_lower and any(v in user_lower for v in paint_verbs)):
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"PAINTER": 0.9},
                reasons={"PAINTER": ["rule:paint"]}
            )
            return "PAINTER", "🎨 Rule-Detected", context_info
        
        code_markers = ["```", "def ", "function ", "class ", "import ", "from ",
                       "代码", "编程", "脚本", "函数", "算法", "bug", "debug", "调试", "报错"]
        if any(m in user_lower for m in code_markers):
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"CODER": 0.9},
                reasons={"CODER": ["rule:code"]}
            )
            return "CODER", "💻 Rule-Detected", context_info
        
        ticket_keywords = ["12306", "火车票", "高铁票", "动车票", "车票", "买票", "购票", "余票", "车次"]
        if any(k in user_lower for k in ticket_keywords):
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"AGENT": 1.0},
                reasons={"AGENT": ["rule:ticket_tool"]}
            )
            return "AGENT", "🤖 Agent-Tools", context_info

        if WebSearcher and WebSearcher.needs_web_search(user_input):
            context_info = context_info or {}
            context_info["routing_list"] = cls._build_routing_list(
                similarity_scores,
                boosts={"WEB_SEARCH": 0.9},
                reasons={"WEB_SEARCH": ["rule:web_search"]}
            )
            return "WEB_SEARCH", "🌐 Rule-Detected", context_info
        
        if history and len(history) >= 2 and ContextAnalyzer:
            context_info = ContextAnalyzer.analyze_context(user_input, history)
            
            if context_info["is_continuation"] and context_info["confidence"] > 0.7:
                related_task = context_info["related_task"]
                continuation_type = context_info.get("continuation_type", "unknown")
                
                if continuation_type == "convert" or related_task == "FILE_GEN":
                    context_info["routing_list"] = cls._build_routing_list(
                        similarity_scores,
                        boosts={"FILE_GEN": 0.88},
                        reasons={"FILE_GEN": [f"rag:{continuation_type}"]}
                    )
                    return "FILE_GEN", f"📄 RAG-{continuation_type}", context_info
                
                if related_task == "PAINTER":
                    context_info["routing_list"] = cls._build_routing_list(
                        similarity_scores,
                        boosts={"PAINTER": 0.88},
                        reasons={"PAINTER": [f"rag:{continuation_type}"]}
                    )
                    return "PAINTER", f"🎨 RAG-{continuation_type}", context_info
                
                if related_task == "RESEARCH":
                    context_info["routing_list"] = cls._build_routing_list(
                        similarity_scores,
                        boosts={"RESEARCH": 0.88},
                        reasons={"RESEARCH": [f"rag:{continuation_type}"]}
                    )
                    return "RESEARCH", f"📚 RAG-{continuation_type}", context_info
                
                if related_task:
                    context_info["routing_list"] = cls._build_routing_list(
                        similarity_scores,
                        boosts={related_task: 0.88},
                        reasons={related_task: [f"rag:{continuation_type}"]}
                    )
                    return related_task, f"🔗 RAG-{continuation_type}", context_info
        
        if client:
            ai_task, ai_confidence, ai_source = _get_ai_router().classify(client, user_input, timeout=2.0)
            if ai_task:
                latency = (time.time() - start_time) * 1000
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={ai_task: 0.8},
                    reasons={ai_task: ["ai_router"]}
                )
                return ai_task, f"{ai_confidence} ({latency:.0f}ms)", context_info
        
        scores = similarity_scores
        best_task = max(scores, key=scores.get)
        best_score = scores[best_task]
        latency = (time.time() - start_time) * 1000
        
        if best_score > 0.3:
            _q_words = ["怎么", "如何", "什么", "为什么", "能不能", "可以吗",
                        "怎样", "咋", "啥", "how", "what", "why", "which"]
            is_q = any(qw in user_lower for qw in _q_words)
            if is_q and best_score < 0.5 and best_task != "CHAT":
                pass 
            else:
                confidence = f"🧠 ML ({best_score:.0%}, {latency:.1f}ms)"
                context_info = context_info or {}
                context_info["routing_list"] = cls._build_routing_list(
                    similarity_scores,
                    boosts={best_task: best_score},
                    reasons={best_task: ["similarity_best"]}
                )
                return best_task, confidence, context_info
        
        context_info = context_info or {}
        context_info["routing_list"] = base_routing_list
        return "CHAT", f"💬 Default ({latency:.1f}ms)", context_info
    
    @classmethod
    def get_model_for_task(cls, task_type, has_image=False, complexity="normal"):
        """根据任务类型获取最优模型"""
        MODEL_MAP = cls._get_dep("MODEL_MAP")
        if not MODEL_MAP:
             # Default fallback if MODEL_MAP is not configured
             MODEL_MAP = {"CHAT": "gemini-model"}

        if task_type == "FILE_GEN":
            if complexity == "complex":
                return "gemini-3-pro-preview"
            return "gemini-3-flash-preview"
        
        if task_type == "DOC_ANNOTATE":
            return "gemini-3-pro-preview"
            
        if task_type == "RESEARCH":
            return "gemini-3-pro-preview"
        
        if task_type == "CODER":
            return "gemini-3-pro-preview"

        if has_image and task_type != "PAINTER":
            return MODEL_MAP.get("VISION", MODEL_MAP.get("CHAT"))
        
        return MODEL_MAP.get(task_type, MODEL_MAP.get("CHAT"))
