#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的记忆管理器 - Phase 1: 自动提取 + 用户画像
支持从对话中自动学习用户偏好，建立用户画像
"""

import json
import os
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path


class UserProfile:
    """用户画像：综合理解用户特征"""
    
    def __init__(self, profile_path: str = "config/user_profile.json"):
        self.profile_path = profile_path
        self.profile = self._load_or_create()
    
    def _load_or_create(self) -> Dict:
        """加载或创建用户画像"""
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[UserProfile] 加载失败: {e}")
        
        # 默认画像
        return {
            "communication_style": {
                "preferred_detail_level": "moderate",  # brief/moderate/detailed
                "preferred_language": "zh-CN",
                "formality": "casual",  # formal/casual/mixed
                "emoji_usage": True,
                "code_style": "concise"  # concise/detailed/explained
            },
            "technical_background": {
                "programming_languages": [],
                "experience_level": "intermediate",  # beginner/intermediate/advanced
                "domains": [],
                "tools": []
            },
            "work_patterns": {
                "frequent_topics": {},  # topic -> count
                "typical_tasks": [],  # coding, research, document_editing, etc.
                "last_active": None
            },
            "preferences": {
                "likes": [],  # 用户明确喜欢的东西
                "dislikes": [],  # 用户明确不喜欢的东西
                "habits": []  # 观察到的使用习惯
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "total_interactions": 0,
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def save(self):
        """保存用户画像"""
        try:
            os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
            with open(self.profile_path, 'w', encoding='utf-8') as f:
                json.dump(self.profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[UserProfile] 保存失败: {e}")
    
    def update_from_extraction(self, extracted_info: Dict):
        """从LLM提取的信息更新画像"""
        try:
            # 更新技术背景
            if "programming_languages" in extracted_info:
                for lang in extracted_info["programming_languages"]:
                    if lang not in self.profile["technical_background"]["programming_languages"]:
                        self.profile["technical_background"]["programming_languages"].append(lang)
            
            # 更新工具偏好
            if "tools" in extracted_info:
                for tool in extracted_info["tools"]:
                    if tool not in self.profile["technical_background"]["tools"]:
                        self.profile["technical_background"]["tools"].append(tool)
            
            # 更新领域
            if "domains" in extracted_info:
                for domain in extracted_info["domains"]:
                    if domain not in self.profile["technical_background"]["domains"]:
                        self.profile["technical_background"]["domains"].append(domain)
            
            # 更新偏好
            if "likes" in extracted_info:
                for item in extracted_info["likes"]:
                    if item not in self.profile["preferences"]["likes"]:
                        self.profile["preferences"]["likes"].append(item)
            
            if "dislikes" in extracted_info:
                for item in extracted_info["dislikes"]:
                    if item not in self.profile["preferences"]["dislikes"]:
                        self.profile["preferences"]["dislikes"].append(item)
            
            # 更新沟通风格
            if "communication_style" in extracted_info:
                self.profile["communication_style"].update(extracted_info["communication_style"])
            
            # 更新元数据
            self.profile["metadata"]["last_updated"] = datetime.now().isoformat()
            self.profile["metadata"]["total_interactions"] += 1
            
            self.save()
            
        except Exception as e:
            print(f"[UserProfile] 更新失败: {e}")
    
    def increment_topic(self, topic: str):
        """增加话题计数"""
        topics = self.profile["work_patterns"]["frequent_topics"]
        topics[topic] = topics.get(topic, 0) + 1
        self.save()
    
    def to_context_string(self) -> str:
        """转换为LLM上下文字符串"""
        lines = ["\n[用户画像]"]
        
        # 沟通风格
        style = self.profile["communication_style"]
        lines.append(f"• 回复风格：{style['preferred_detail_level']}详细度，{style['formality']}语气")
        if style.get('code_style'):
            lines.append(f"• 代码风格：{style['code_style']}")
        
        # 技术背景
        tech = self.profile["technical_background"]
        if tech.get("programming_languages"):
            lines.append(f"• 编程语言：{', '.join(tech['programming_languages'][:5])}")
        if tech.get("experience_level"):
            lines.append(f"• 经验水平：{tech['experience_level']}")
        
        # 偏好
        prefs = self.profile["preferences"]
        if prefs.get("likes"):
            lines.append(f"• 喜欢：{', '.join(prefs['likes'][:3])}")
        if prefs.get("dislikes"):
            lines.append(f"• 不喜欢：{', '.join(prefs['dislikes'][:3])}")
        
        # 常用话题
        topics = self.profile["work_patterns"].get("frequent_topics", {})
        if topics:
            top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]
            lines.append(f"• 常见话题：{', '.join([t[0] for t in top_topics])}")
        
        return "\n".join(lines) + "\n"
    
    def get_brief_summary(self) -> str:
        """获取简短总结"""
        tech = self.profile["technical_background"]
        langs = tech.get("programming_languages", [])[:2]
        level = tech.get("experience_level", "intermediate")
        
        return f"{level}级别开发者" + (f"，熟悉{'/'.join(langs)}" if langs else "")


class EnhancedMemoryManager:
    """增强的记忆管理器"""
    
    def __init__(self, memory_path: str = "config/memory.json", 
                 profile_path: str = "config/user_profile.json"):
        self.memory_path = memory_path
        self.memories: List[Dict] = []
        self.user_profile = UserProfile(profile_path)
        self._load()
        
        print(f"[EnhancedMemory] ✅ 记忆系统已启动")
        print(f"[EnhancedMemory] 📊 当前记忆数：{len(self.memories)}")
        print(f"[EnhancedMemory] 👤 用户画像：{self.user_profile.get_brief_summary()}")
    
    def _load(self):
        """加载记忆"""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
            except Exception as e:
                print(f"[EnhancedMemory] 加载失败: {e}")
                self.memories = []
    
    def _save(self):
        """保存记忆"""
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[EnhancedMemory] 保存失败: {e}")
    
    def add_memory(self, content: str, category: str = "user_preference", 
                   source: str = "user", metadata: Optional[Dict] = None) -> Dict:
        """添加记忆"""
        item = {
            "id": int(time.time() * 1000),
            "content": content.strip(),
            "category": category,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "use_count": 0,
            "metadata": metadata or {}
        }
        
        self.memories.append(item)
        self._save()
        
        print(f"[EnhancedMemory] ➕ 新记忆: {content[:50]}...")
        return item
    
    def auto_extract_from_conversation(self, user_msg: str, ai_msg: str, 
                                       history: Optional[List] = None) -> Dict:
        """
        从对话中自动提取记忆（需要LLM支持）
        这是一个占位函数，实际需要调用LLM进行分析
        
        返回提取的信息字典
        """
        # TODO: 在app.py中集成LLM调用
        extracted = {
            "memories": [],
            "profile_updates": {}
        }
        
        # 简单的关键词检测（临时方案）
        user_lower = user_msg.lower()
        
        # 检测编程语言
        lang_keywords = {
            "python": ["python", "py"],
            "javascript": ["javascript", "js", "node"],
            "java": ["java"],
            "c++": ["c++", "cpp"],
            "go": ["golang", "go语言"]
        }
        
        for lang, keywords in lang_keywords.items():
            if any(kw in user_lower for kw in keywords):
                if lang not in self.user_profile.profile["technical_background"]["programming_languages"]:
                    extracted["profile_updates"].setdefault("programming_languages", []).append(lang)
        
        # 检测偏好信号
        if any(word in user_lower for word in ["喜欢", "prefer", "倾向", "更喜欢"]):
            # 提取偏好（简化版）
            if "简洁" in user_lower or "简单" in user_lower:
                extracted["profile_updates"]["communication_style"] = {"preferred_detail_level": "brief"}
        
        if any(word in user_lower for word in ["不喜欢", "不要", "避免"]):
            # 提取不喜欢的内容
            pass
        
        # 应用提取的信息
        if extracted["profile_updates"]:
            self.user_profile.update_from_extraction(extracted["profile_updates"])
            print(f"[EnhancedMemory] 🔄 从对话中学习：{extracted['profile_updates']}")
        
        return extracted
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索相关记忆（关键词版本）"""
        if not query:
            return []
        
        query_lower = query.lower()
        scored = []
        keywords = [k for k in query_lower.split() if len(k) > 1]
        
        for m in self.memories:
            content_lower = m["content"].lower()
            score = 0
            
            # 分类加权
            if m["category"] == "user_preference":
                score += 3
            elif m["category"] == "correction":
                score += 2
            
            # 完全匹配
            if query_lower in content_lower:
                score += 5
            
            # 关键词匹配
            for kw in keywords:
                if kw in content_lower:
                    score += 1
            
            if score > 0:
                scored.append((score, m))
        
        # 排序
        scored.sort(key=lambda x: (x[0], x[1]["created_at"]), reverse=True)
        
        # 增加使用计数
        results = [item[1] for item in scored[:limit]]
        for m in results:
            m["use_count"] = m.get("use_count", 0) + 1
        
        if results:
            self._save()
        
        return results
    
    def get_context_string(self, user_input: str) -> str:
        """获取用于注入LLM的上下文"""
        lines = []
        
        # 添加用户画像
        profile_context = self.user_profile.to_context_string()
        lines.append(profile_context)
        
        # 添加相关记忆
        relevant = self.search_memories(user_input, limit=3)
        if relevant:
            lines.append("\n[相关记忆]")
            for m in relevant:
                lines.append(f"• {m['content']}")
        
        return "\n".join(lines) if lines else ""
    
    def get_all_memories(self) -> List[Dict]:
        """获取所有记忆"""
        return sorted(self.memories, key=lambda x: x["created_at"], reverse=True)
    
    def delete_memory(self, memory_id: int) -> bool:
        """删除记忆"""
        initial_len = len(self.memories)
        self.memories = [m for m in self.memories if m["id"] != memory_id]
        
        if len(self.memories) < initial_len:
            self._save()
            return True
        return False
    
    def get_profile(self) -> Dict:
        """获取用户画像"""
        return self.user_profile.profile
    
    def update_profile_manually(self, updates: Dict):
        """手动更新用户画像"""
        self.user_profile.profile.update(updates)
        self.user_profile.save()


# 向后兼容的别名
MemoryManager = EnhancedMemoryManager


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("  增强记忆管理器测试")
    print("=" * 60)
    
    mgr = EnhancedMemoryManager()
    
    # 测试添加记忆
    mgr.add_memory("用户喜欢简洁的代码，不要太多注释", category="user_preference")
    mgr.add_memory("项目名称：Koto AI助手", category="project_info")
    
    # 测试自动提取
    mgr.auto_extract_from_conversation(
        "我在用Python开发一个Web应用",
        "好的，我可以帮你..."
    )
    
    # 测试搜索
    results = mgr.search_memories("代码")
    print(f"\n搜索结果：{len(results)} 条")
    
    # 显示用户画像
    print(mgr.user_profile.to_context_string())
    
    print("\n✅ 测试完成")
