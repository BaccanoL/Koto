#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动归纳调度器快速开始脚本
展示如何启用/禁用和手动执行归纳
"""
import os
import sys
import json
import time

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'web'))

from auto_catalog_scheduler import get_auto_catalog_scheduler


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 70)
    print(title.center(70))
    print("=" * 70 + "\n")


def print_status(scheduler):
    """打印当前状态"""
    enabled = scheduler.is_auto_catalog_enabled()
    schedule_time = scheduler.get_catalog_schedule()
    source_dirs = scheduler.get_source_directories()
    
    print(f"📊 自动归纳状态:")
    print(f"  • 启用: {'✅ 是' if enabled else '❌ 否'}")
    print(f"  • 调度时间: {schedule_time}")
    print(f"  • 源目录数: {len(source_dirs)}")
    
    if source_dirs:
        print(f"\n📁 源目录:")
        for i, d in enumerate(source_dirs, 1):
            print(f"  {i}. {d}")
    
    print(f"\n💾 备份目录: {scheduler.get_backup_directory()}")


def example_1_view_status():
    """示例 1: 查看当前状态"""
    print_header("示例 1: 查看自动归纳状态")
    
    scheduler = get_auto_catalog_scheduler()
    print_status(scheduler)


def example_2_enable():
    """示例 2: 启用自动归纳"""
    print_header("示例 2: 启用自动归纳")
    
    scheduler = get_auto_catalog_scheduler()
    
    print("启用自动归纳，设置每日凌晨 2 点执行...")
    print()
    
    scheduler.enable_auto_catalog(
        schedule_time="02:00",
        source_dirs=None  # 使用默认微信文件目录
    )
    
    print("✅ 已启用\n")
    print_status(scheduler)


def example_3_disable():
    """示例 3: 禁用自动归纳"""
    print_header("示例 3: 禁用自动归纳")
    
    scheduler = get_auto_catalog_scheduler()
    
    if scheduler.is_auto_catalog_enabled():
        print("禁用自动归纳...")
        scheduler.disable_auto_catalog()
        print("✅ 已禁用")
    else:
        print("⚠️  自动归纳已经禁用")
    
    print()
    print_status(scheduler)


def example_4_custom_schedule():
    """示例 4: 自定义调度时间"""
    print_header("示例 4: 自定义调度时间")
    
    scheduler = get_auto_catalog_scheduler()
    
    print("配置自动归纳在每天下午 3 点执行...")
    print()
    
    scheduler.enable_auto_catalog(
        schedule_time="15:00",
        source_dirs=None
    )
    
    print("✅ 已配置\n")
    print_status(scheduler)


def example_5_manual_execute():
    """示例 5: 手动立即执行一次"""
    print_header("示例 5: 手动立即执行")
    
    scheduler = get_auto_catalog_scheduler()
    
    source_dirs = scheduler.get_source_directories()
    
    if not source_dirs:
        print("❌ 没有配置源目录")
        print("\n提示: 请先调用示例 2 启用自动归纳")
        return
    
    print(f"将立即执行归纳，处理 {len(source_dirs)} 个源目录...\n")
    
    start_time = time.time()
    
    result = scheduler.manual_catalog_now()
    
    elapsed = time.time() - start_time
    
    print("\n" + "-" * 70)
    print("📋 归纳结果:")
    print("-" * 70)
    
    print(f"✅ 执行成功: {result.get('success', False)}")
    print(f"📊 统计:")
    print(f"  • 总文件数: {result.get('total_files', 0)}")
    print(f"  • 已归纳: {result.get('organized_count', 0)}")
    print(f"  • 已备份: {result.get('backed_up_count', 0)}")
    print(f"⏱️  耗时: {elapsed:.2f} 秒")
    
    if result.get('errors'):
        print(f"\n❌ 错误信息:")
        for error in result.get('errors', []):
            print(f"  • {error}")
    
    if result.get('report_path'):
        print(f"\n📄 报告文件:")
        print(f"  {result.get('report_path')}")
    
    print()


def example_6_list_backups():
    """示例 6: 查看备份清单"""
    print_header("示例 6: 查看备份清单")
    
    scheduler = get_auto_catalog_scheduler()
    backup_dir = scheduler.get_backup_directory()
    
    if not os.path.exists(backup_dir):
        print("❌ 备份目录不存在")
        print("提示: 请先执行一次归纳（示例 5）生成备份清单")
        return
    
    manifests = [f for f in os.listdir(backup_dir) if f.startswith('backup_manifest_')]
    
    if not manifests:
        print("⚠️  暂无备份清单")
        print("提示: 请先执行一次归纳（示例 5）生成备份清单")
        return
    
    print(f"找到 {len(manifests)} 个备份清单:\n")
    
    for i, manifest_file in enumerate(sorted(manifests, reverse=True)[:5], 1):
        print(f"{i}. {manifest_file}")
        
        manifest_path = os.path.join(backup_dir, manifest_file)
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        files_count = len(manifest_data.get('files', []))
        print(f"   ├─ 文件数: {files_count}")
        print(f"   ├─ 时间: {manifest_data.get('backup_time', '未知')}")
        
        # 统计备份检查结果
        if manifest_data.get('files'):
            source_exist = sum(1 for f in manifest_data['files'] if f.get('source_exists'))
            organized_exist = sum(1 for f in manifest_data['files'] if f.get('organized_exists'))
            
            print(f"   ├─ 源文件存在: {source_exist}/{files_count}")
            print(f"   └─ 归纳文件存在: {organized_exist}/{files_count}")
        
        print()


def interactive_menu():
    """交互式菜单"""
    print_header("自动归纳调度器 - 快速开始")
    
    print("""
选择一个操作:
  1. 查看当前状态
  2. 启用自动归纳（每日 02:00）
  3. 禁用自动归纳
  4. 自定义调度时间
  5. 手动立即执行一次
  6. 查看备份清单
  0. 退出

""")
    
    choice = input("请输入选项 (0-6): ").strip()
    
    print()
    
    if choice == "1":
        example_1_view_status()
    elif choice == "2":
        example_2_enable()
    elif choice == "3":
        example_3_disable()
    elif choice == "4":
        example_4_custom_schedule()
    elif choice == "5":
        example_5_manual_execute()
    elif choice == "6":
        example_6_list_backups()
    elif choice == "0":
        print("👋 再见！")
        return False
    else:
        print("⚠️  无效选项")
    
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 命令行模式
        cmd = sys.argv[1]
        
        if cmd == "status":
            example_1_view_status()
        elif cmd == "enable":
            example_2_enable()
        elif cmd == "disable":
            example_3_disable()
        elif cmd == "custom":
            example_4_custom_schedule()
        elif cmd == "run":
            example_5_manual_execute()
        elif cmd == "backups":
            example_6_list_backups()
        else:
            print(f"未知命令: {cmd}")
            print("\n支持的命令:")
            print("  status   - 查看状态")
            print("  enable   - 启用自动归纳")
            print("  disable  - 禁用自动归纳")
            print("  custom   - 自定义调度")
            print("  run      - 立即执行")
            print("  backups  - 查看备份清单")
    else:
        # 交互模式
        while interactive_menu():
            input("\n按 Enter 继续...")
