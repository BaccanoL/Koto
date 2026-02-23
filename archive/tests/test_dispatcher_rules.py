#!/usr/bin/env python3
"""
Koto 任务分类系统 - 完整 SmartDispatcher 测试
测试规则引擎的完整分类流程（不依赖 Ollama/Gemini API）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import SmartDispatcher, LocalModelRouter

# 临时禁用 Ollama 以测试规则引擎
LocalModelRouter._available = False
LocalModelRouter._check_time = float('inf')

print("=" * 70)
print("Koto SmartDispatcher 完整分类测试（仅规则引擎）")
print("=" * 70)

# 测试用例格式: (输入文本, 期望任务类型, 描述)
test_cases = [
    # ═══ CHAT（日常对话/知识问答） ═══
    ("你好", "CHAT", "简单问候"),
    ("在Windows环境里快速启动bash虚拟环境，一般用什么办法", "CHAT", "知识问答-含启动"),
    ("怎么启动docker容器", "CHAT", "知识问答-含启动"),
    ("如何打开隐藏文件显示", "CHAT", "知识问答-含打开"),
    ("什么是虚拟环境", "CHAT", "概念解释"),
    ("Python怎么安装第三方库", "CHAT", "教程问答"),
    ("vscode有什么好用的插件推荐", "CHAT", "推荐请求"),
    ("解释一下docker的原理", "CHAT", "概念解释"),
    ("写一段自我介绍", "CHAT", "短文本生成"),
    ("讲个笑话", "CHAT", "闲聊"),
    ("推荐几本好书", "CHAT", "推荐请求"),
    ("了解一下MicroLED技术", "CHAT", "了解=浅层知识"),
    ("研究一下这个问题", "CHAT", "研究一下=日常了解"),
    ("搜索怎么用git", "CHAT", "求教程"),
    ("有什么好的学习方法", "CHAT", "普通问答"),
    ("谢谢你的帮助", "CHAT", "感谢"),
    ("介绍一下Go语言", "CHAT", "知识介绍"),

    # ═══ SYSTEM（系统操作命令） ═══
    ("打开微信", "SYSTEM", "打开应用"),
    ("启动Chrome", "SYSTEM", "启动浏览器"),
    ("打开steam", "SYSTEM", "打开游戏平台"),
    ("关闭qq", "SYSTEM", "关闭应用"),
    ("打开计算器", "SYSTEM", "打开系统工具"),
    ("截图", "SYSTEM", "系统操作"),
    ("关机", "SYSTEM", "关机"),
    ("打开终端", "SYSTEM", "打开终端"),

    # ═══ CODER（代码编程） ═══
    ("写一个快速排序函数", "CODER", "写函数"),
    ("帮我写个Python脚本", "CODER", "写脚本"),
    ("这段代码有bug，帮我修复", "CODER", "调试代码"),
    ("用javascript实现一个轮播图", "CODER", "编程实现"),

    # ═══ PAINTER（图像生成） ═══
    ("画一只猫", "PAINTER", "画图"),
    ("帮我画个壁纸", "PAINTER", "画壁纸"),
    ("生成一张赛博朋克风格的图片", "PAINTER", "生成图片"),
    ("画一个可爱的头像", "PAINTER", "画头像"),

    # ═══ FILE_GEN（文档文件生成） ═══
    ("帮我做一个PPT", "FILE_GEN", "做PPT"),
    ("生成一份word报告", "FILE_GEN", "生成word"),
    ("写份项目方案做成pdf", "FILE_GEN", "生成pdf"),
    ("创建一个excel表格", "FILE_GEN", "创建表格"),
    ("帮我写份简历", "FILE_GEN", "写简历"),

    # ═══ WEB_SEARCH（联网搜索） ═══
    ("今天北京天气怎么样", "WEB_SEARCH", "天气查询"),
    ("特斯拉股价多少", "WEB_SEARCH", "股价查询"),
    ("今天新闻有什么", "WEB_SEARCH", "新闻查询"),
    ("美元汇率", "WEB_SEARCH", "汇率查询"),

    # ═══ AGENT（工具调用） ═══
    ("给张三发微信说明天开会", "AGENT", "发微信"),
    ("12306查下明天去上海的车票", "AGENT", "12306查票"),
    ("帮我回微信和老板说好的", "AGENT", "回微信"),

    # ═══ RESEARCH（深度研究） ═══
    ("深入研究MicroLED的技术原理和发展历程", "RESEARCH", "深入研究"),
    ("详细分析人工智能对就业市场的影响", "RESEARCH", "详细分析"),
    ("系统分析中美贸易战的经济影响", "RESEARCH", "系统分析"),
]

pass_count = 0
fail_count = 0
failures = []

for text, expected_task, description in test_cases:
    task, confidence, context = SmartDispatcher.analyze(text)
    
    # 对于某些特殊任务类型的映射
    is_pass = (task == expected_task)
    
    # 允许一些合理的近似匹配
    if not is_pass:
        # MULTI_STEP 包含 FILE_GEN 子任务时也算正确
        if expected_task == "FILE_GEN" and task == "MULTI_STEP":
            is_pass = True
        # SYSTEM 和 AGENT 对于"打开"类操作可以互通
        if expected_task == "AGENT" and task == "SYSTEM":
            is_pass = True

    if is_pass:
        pass_count += 1
        print(f"  ✅ '{text[:30]:<30s}' → {task:<12s} ({confidence}) [{description}]")
    else:
        fail_count += 1
        failures.append((text, expected_task, task, confidence, description))
        print(f"  ❌ '{text[:30]:<30s}' → {task:<12s} (期望 {expected_task}) [{description}]  路由: {confidence}")

total = pass_count + fail_count
print(f"\n{'=' * 70}")
print(f"结果: {pass_count}/{total} 通过 ({pass_count/total*100:.1f}%)")

if failures:
    print(f"\n❌ 失败用例 ({len(failures)}):")
    for text, expected, actual, conf, desc in failures:
        print(f"  [{desc}] '{text}' → 实际:{actual} 期望:{expected} 路由:{conf}")
else:
    print("🎉 全部通过！")
print("=" * 70)
