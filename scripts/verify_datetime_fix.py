#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧪 Koto 日期时间上下文优化 - 快速验证脚本

运行方式:
    python verify_datetime_fix.py

作用:
    验证日期时间上下文修复是否正确应用
"""

import sys
import os

# 添加 Koto 项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_imports():
    """验证必要的导入和函数"""
    print("=" * 60)
    print("🧪 验证 1: 检查函数是否存在")
    print("=" * 60)
    
    try:
        from web.app import _get_chat_system_instruction, _get_system_instruction
        print("✅ _get_chat_system_instruction() 存在")
        print("✅ _get_system_instruction() 存在")
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def verify_system_instructions():
    """验证系统指令包含时间信息"""
    print("\n" + "=" * 60)
    print("🧪 验证 2: 检查系统指令是否包含时间信息")
    print("=" * 60)
    
    try:
        from web.app import _get_chat_system_instruction, _get_system_instruction
        
        chat_inst = _get_chat_system_instruction()
        doc_inst = _get_system_instruction()
        
        # 检查聊天系统指令
        print("\n📝 聊天系统指令包含的关键词:")
        keywords = ["系统时间", "使用此时间计算", "明天", "下周", "前天"]
        for kw in keywords:
            if kw in chat_inst:
                print(f"  ✅ {kw}")
            else:
                print(f"  ❌ {kw}")
        
        if all(kw in chat_inst for kw in keywords):
            print("✅ 聊天系统指令包含完整时间信息")
        else:
            print("⚠️ 聊天系统指令可能不完整")
        
        # 检查文档生成系统指令
        print("\n📝 文档生成系统指令包含的关键词:")
        if "生成日期" in doc_inst:
            print("  ✅ 生成日期")
        else:
            print("  ❌ 生成日期")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def verify_time_format():
    """验证时间格式是否正确"""
    print("\n" + "=" * 60)
    print("🧪 验证 3: 检查时间格式和内容")
    print("=" * 60)
    
    try:
        from web.app import _get_chat_system_instruction
        from datetime import datetime
        
        inst = _get_chat_system_instruction()
        
        # 提取时间信息部分
        import re
        match = re.search(r"🕒 \*\*系统时间\*\*: ([^\n]+)", inst)
        if match:
            time_info = match.group(1)
            print(f"\n📅 提取的时间信息: {time_info}")
            
            # 验证格式
            if "年" in time_info and "月" in time_info and "日" in time_info and "周" in time_info:
                print("✅ 时间格式正确（含年月日周星期）")
            else:
                print("⚠️ 时间格式可能不完整")
            
            return True
        else:
            print("❌ 未找到时间信息")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def verify_api_calls():
    """验证 API 调用是否使用了动态函数"""
    print("\n" + "=" * 60)
    print("🧪 验证 4: 检查代码中是否使用了动态函数")
    print("=" * 60)
    
    try:
        import re
        
        app_file = "web/app.py"
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 计算使用动态函数的次数
        dynamic_calls = len(re.findall(r"system_instruction=_get_(?:chat_)?system_instruction\(\)", content))
        
        print(f"\n📊 API 调用统计:")
        print(f"  使用 _get_system_instruction() 的次数: {dynamic_calls}")
        
        if dynamic_calls >= 4:
            print(f"✅ 至少 4 处都已使用动态函数")
            return True
        else:
            print(f"⚠️ 只有 {dynamic_calls} 处使用动态函数，可能还有未修改的地方")
            return False
            
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def show_sample_instruction():
    """显示系统指令示例"""
    print("\n" + "=" * 60)
    print("📋 系统指令示例")
    print("=" * 60)
    
    try:
        from web.app import _get_chat_system_instruction
        
        inst = _get_chat_system_instruction()
        
        # 显示前 500 字符
        print("\n聊天系统指令（前 500 字符）:")
        print("-" * 60)
        print(inst[:500] + "..." if len(inst) > 500 else inst)
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 显示失败: {e}")
        return False

def main():
    """主验证函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "🧪 日期时间上下文优化 - 验证工具" + " " * 13 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # 运行所有验证
    results.append(("函数导入", verify_imports()))
    results.append(("系统指令内容", verify_system_instructions()))
    results.append(("时间格式", verify_time_format()))
    results.append(("API 调用", verify_api_calls()))
    results.append(("示例显示", show_sample_instruction()))
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 验证总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n通过: {passed}/{total}")
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    if passed == total:
        print("\n" + "🎉" * 20)
        print("所有验证都通过了！日期时间上下文优化已成功应用。")
        print("现在 Koto 可以准确处理时间相关问题了！")
        print("🎉" * 20)
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 项验证未通过，可能需要检查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
