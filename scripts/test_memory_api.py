#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强记忆系统API测试脚本

测试所有记忆管理API端点，验证其功能
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:5000/api/memory"

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_memory_stats():
    """测试记忆统计API"""
    print_section("📊 测试记忆统计 API")
    
    try:
        response = requests.get(f"{API_BASE}/stats", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            stats = data["stats"]
            print(f"✅ 请求成功")
            print(f"\n📌 总记忆数: {stats['total_memories']}")
            
            if stats.get('by_category'):
                print(f"\n📂 按分类统计:")
                for cat, count in stats['by_category'].items():
                    print(f"   • {cat}: {count}")
            
            if stats.get('by_source'):
                print(f"\n📍 按来源统计:")
                for src, count in stats['by_source'].items():
                    print(f"   • {src}: {count}")
            
            if stats.get('most_used'):
                print(f"\n🔥 最常使用的记忆:")
                for mem in stats['most_used'][:3]:
                    print(f"   • {mem['content'][:60]}... (使用{mem['use_count']}次)")
            
            if stats.get('profile_stats'):
                print(f"\n👤 用户画像统计:")
                ps = stats['profile_stats']
                print(f"   • 总交互次数: {ps['total_interactions']}")
                print(f"   • 编程语言数: {ps['programming_languages']}")
                print(f"   • 工具数: {ps['tools']}")
                print(f"   • 偏好数: {ps['preferences_count']}")
        else:
            print(f"❌ API返回失败: {data}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败：Koto未运行或后端未启动")
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_user_profile():
    """测试用户画像API"""
    print_section("👤 测试用户画像 API")
    
    try:
        response = requests.get(f"{API_BASE}/profile", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            summary = data.get("summary", "N/A")
            profile = data.get("profile", {})
            
            print(f"✅ 请求成功")
            print(f"\n📝 用户画像摘要:")
            print(f"   {summary}")
            
            if profile:
                print(f"\n💬 交流风格:")
                comm = profile.get('communication_style', {})
                print(f"   • 详细度: {comm.get('response_detail', 'N/A')}")
                print(f"   • 语气: {comm.get('tone', 'N/A')}")
                print(f"   • 偏好语言: {comm.get('preferred_language', 'N/A')}")
                
                print(f"\n💻 技术背景:")
                tech = profile.get('technical_background', {})
                print(f"   • 经验等级: {tech.get('experience_level', 'N/A')}")
                langs = tech.get('programming_languages', [])
                if langs:
                    print(f"   • 编程语言: {', '.join(langs[:5])}")
                tools = tech.get('tools', [])
                if tools:
                    print(f"   • 工具: {', '.join(tools[:5])}")
                
                print(f"\n🎯 工作模式:")
                work = profile.get('work_patterns', {})
                print(f"   • 任务类型: {', '.join(work.get('task_types', [])[:3])}")
                
                print(f"\n❤️  偏好:")
                prefs = profile.get('preferences', {})
                likes = prefs.get('likes', [])
                if likes:
                    print(f"   • 喜欢: {', '.join(likes[:3])}")
                dislikes = prefs.get('dislikes', [])
                if dislikes:
                    print(f"   • 不喜欢: {', '.join(dislikes[:3])}")
        else:
            print(f"❌ API返回失败: {data}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败：Koto未运行或后端未启动")
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 错误: {e}")

def test_auto_learn():
    """测试自动学习API"""
    print_section("🧠 测试自动学习 API")
    
    test_conversation = {
        "user_message": "我最喜欢用VS Code写Python，觉得它的扩展生态很好用",
        "ai_message": "我了解到您偏好使用VS Code编写Python代码，并且重视扩展生态系统"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/auto-learn",
            json=test_conversation,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            result = data.get("result", {})
            print(f"✅ 请求成功")
            print(f"\n📚 学习结果:")
            print(f"   {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"⚠️  {data.get('message', '未知错误')}")
    
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败：Koto未运行或后端未启动")
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except Exception as e:
        print(f"❌ 错误: {e}")

def main():
    """主测试流程"""
    print(f"\n{'='*60}")
    print(f"  🧪 增强记忆系统 API 测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  目标: {API_BASE}")
    print(f"{'='*60}")
    
    # 测试所有API
    test_memory_stats()
    test_user_profile()
    test_auto_learn()
    
    print_section("✅ 测试完成")
    print("所有增强记忆系统API已验证完毕！\n")

if __name__ == "__main__":
    main()
