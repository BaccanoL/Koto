#!/usr/bin/env python3
"""
Koto 本地模型快速安装脚本
自动下载并初始化任务路由的本地模型
"""

import sys
import os

def install_dependencies():
    """安装必需的 Python 包"""
    print("📦 安装依赖包...")
    
    packages = [
        "transformers>=4.30.0",
        "torch>=2.0.0",
    ]
    
    import subprocess
    
    for package in packages:
        print(f"  📥 安装 {package}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package, "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"  ✅ {package} 已安装")
        except subprocess.CalledProcessError:
            print(f"  ❌ {package} 安装失败")
            return False
    
    return True


def download_model(model_name="facebook/bart-large-mnli"):
    """下载指定的本地模型"""
    print(f"\n📥 正在下载模型: {model_name}")
    print("   这可能需要几分钟（仅首次）...")
    
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        print("  📄 下载分词器...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        print("  🤖 下载模型...")
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        
        print(f"✅ 模型已下载: {model_name}")
        print(f"   位置: {os.path.expanduser('~/.cache/huggingface/')}")
        return True
        
    except Exception as e:
        print(f"❌ 模型下载失败: {e}")
        return False


def test_model():
    """测试本地模型是否可用"""
    print("\n🧪 测试本地模型...")
    
    try:
        # 这里假设我们在 web 目录中
        sys.path.insert(0, os.path.dirname(__file__))
        from app import LocalModelRouter
        
        # 初始化模型
        if not LocalModelRouter.init_model():
            print("❌ 模型初始化失败")
            return False
        
        # 测试分类
        test_inputs = [
            "画一只猫",
            "写一个 Python 函数",
            "最新的新闻",
            "你好，今天天气怎么样",
        ]
        
        print("\n📝 测试分类结果:")
        for test_input in test_inputs:
            task, confidence, source = LocalModelRouter.classify(test_input)
            print(f"  '{test_input}'")
            print(f"    → {task} ({confidence})")
        
        print("\n✅ 本地模型测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 Koto 本地模型安装向导")
    print("=" * 60)
    
    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("❌ 需要 Python 3.8 或更高版本")
        return False
    
    print(f"✅ Python 版本: {sys.version}")
    
    # 安装依赖
    if not install_dependencies():
        print("\n❌ 依赖安装失败")
        return False
    
    # 选择模型
    print("\n📋 可用的模型:")
    models = {
        "1": ("facebook/bart-large-mnli", "推荐 - 高准确率（~400MB）"),
        "2": ("facebook/bart-base-mnli", "均衡 - 中等准确率（~200MB）"),
        "3": ("cross-encoder/nli-distilroberta-base", "轻量 - 快速（~100MB）"),
        "4": ("hfl/chinese-roberta-wwm-ext", "中文 - 中文优化（~400MB）"),
    }
    
    for key, (model, desc) in models.items():
        print(f"  {key}. {desc}")
        print(f"     {model}")
    
    choice = input("\n选择模型 (1-4，默认 1): ").strip() or "1"
    
    if choice not in models:
        print("❌ 无效的选择")
        return False
    
    model_name, _ = models[choice]
    
    # 下载模型
    if not download_model(model_name):
        print("\n❌ 模型下载失败")
        print("   请检查网络连接或尝试其他镜像源")
        return False
    
    # 测试模型
    if not test_model():
        print("\n⚠️  模型测试失败，但文件已下载")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 安装完成！")
    print("=" * 60)
    print("\n后续步骤:")
    print("  1. 启动 Koto 应用")
    print("  2. 系统将自动使用本地模型进行任务分类")
    print("  3. 无需网络连接即可进行任务路由")
    print("\n💡 提示: 要更换模型，重新运行此脚本或编辑 app.py 中的")
    print("   LocalModelRouter.init_model(model_name='...')")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
