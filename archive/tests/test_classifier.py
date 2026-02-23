#!/usr/bin/env python3
"""
Koto 任务分类系统 - 全面测试套件
测试所有任务类型的分类准确性

只测试本地规则 + is_system_command 逻辑（不依赖 Ollama / Gemini）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import LocalExecutor, WebSearcher

print("=" * 70)
print("Koto 任务分类测试套件")
print("=" * 70)

# ═══════════════════════════════════════════════════
# 测试 1: is_system_command() 精确性
# ═══════════════════════════════════════════════════
print("\n📋 测试 1: is_system_command() 正确识别")
print("-" * 70)

# 应该返回 True 的用例（真正的系统命令）
should_be_system = [
    "打开微信",
    "启动Chrome",
    "打开steam",
    "关闭qq",
    "启动vscode",
    "打开计算器",
    "打开网易云",
    "打开任务管理器",
    "open chrome",
    "start wechat",
    "关机",
    "重启",
    "截图",
    "open notepad",
    "打开终端",
    "打开edge",
]

# 应该返回 False 的用例（知识问答/非命令）
should_not_be_system = [
    "在Windows环境里快速启动bash虚拟环境，一般用什么办法",
    "怎么启动docker容器",
    "如何打开隐藏文件显示",
    "运行Python程序的方法是什么",
    "关闭防火墙的步骤有哪些",
    "启动黑屏怎么解决",
    "打开开发者模式的方法",
    "电脑开机启动慢是什么原因",
    "怎么运行一个Flask项目",
    "shutdown命令怎么用",
    "如何关闭后台进程",
    "Windows启动修复怎么操作",
    "什么是虚拟环境",
    "解释一下docker的原理",
    "Python怎么安装第三方库",
    "vscode有什么好用的插件推荐",
    "搜索引擎是怎么工作的",
    "怎么打开PowerShell的管理员模式",
    "我想了解一下最近有什么好看的电影推荐？",
    "了解一下MicroLED技术",
    "搜索怎么用git",
]

pass_count = 0
fail_count = 0
failures = []

for text in should_be_system:
    result = LocalExecutor.is_system_command(text)
    if result:
        pass_count += 1
        print(f"  ✅ PASS: '{text}' → True")
    else:
        fail_count += 1
        failures.append(("SYSTEM应True", text, result))
        print(f"  ❌ FAIL: '{text}' → False (期望 True)")

for text in should_not_be_system:
    result = LocalExecutor.is_system_command(text)
    if not result:
        pass_count += 1
        print(f"  ✅ PASS: '{text}' → False")
    else:
        fail_count += 1
        failures.append(("非SYSTEM应False", text, result))
        print(f"  ❌ FAIL: '{text}' → True (期望 False)")

print(f"\n  结果: {pass_count}/{pass_count + fail_count} 通过")

# ═══════════════════════════════════════════════════
# 测试 2: WebSearcher.needs_web_search() 精确性
# ═══════════════════════════════════════════════════
print("\n📋 测试 2: WebSearcher.needs_web_search() 精确性")
print("-" * 70)

# 应该返回 True（确实需要搜索）
should_search = [
    "今天北京天气怎么样",
    "明天会下雨吗",
    "特斯拉股价多少",
    "今天新闻有什么",
    "比特币价格",
    "昨天曼联比分",
    "A股今天涨了吗",
    "美元汇率",
]

# 应该返回 False（日常用词不应触发搜索）
should_not_search = [
    "在Windows环境里快速启动bash虚拟环境，一般用什么办法",
    "帮我分析一下这段代码",
    "写一段自我介绍",
    "什么是机器学习",
    "研究一下这个问题",
    "Python数据结构对比",
    "帮我做一个PPT",
    "推荐一下好看的电影",
    "今天学了什么",  # "今天"不应单独触发
    "我最近在学Python",  # "最近"不应单独触发
    "现在开始写代码",  # "现在"不应单独触发
    "给你发布一个任务",  # "发布"不应单独触发
    "帮我统计一下数据",  # "统计"不应触发
    "对比一下React和Vue",  # "对比"不应触发
    "行业发展趋势分析",  # "趋势""分析"不应触发
    "这个建议不错",  # "建议"不应触发
    "预测一下明年就业形势",  # 一般性讨论不触发
    "有什么好的学习方法",
]

pass_count2 = 0
fail_count2 = 0

for text in should_search:
    result = WebSearcher.needs_web_search(text)
    if result:
        pass_count2 += 1
        print(f"  ✅ PASS: '{text}' → True")
    else:
        fail_count2 += 1
        failures.append(("搜索应True", text, result))
        print(f"  ❌ FAIL: '{text}' → False (期望 True)")

for text in should_not_search:
    result = WebSearcher.needs_web_search(text)
    if not result:
        pass_count2 += 1
        print(f"  ✅ PASS: '{text}' → False")
    else:
        fail_count2 += 1
        failures.append(("非搜索应False", text, result))
        print(f"  ❌ FAIL: '{text}' → True (期望 False)")

print(f"\n  结果: {pass_count2}/{pass_count2 + fail_count2} 通过")

# ═══════════════════════════════════════════════════
# 总结
# ═══════════════════════════════════════════════════
total_pass = pass_count + pass_count2
total_fail = fail_count + fail_count2
total = total_pass + total_fail

print("\n" + "=" * 70)
print(f"总结: {total_pass}/{total} 通过 ({total_pass/total*100:.1f}%)")
if failures:
    print(f"\n❌ 失败用例 ({len(failures)}):")
    for category, text, result in failures:
        print(f"  [{category}] '{text}' → {result}")
else:
    print("🎉 全部通过！")
print("=" * 70)
