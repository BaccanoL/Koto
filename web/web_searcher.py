#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSearcher 桥接模块 — 避免 tool_registry → app.py 循环导入
从 app.py 中的 WebSearcher 类代理 search_with_grounding 方法
"""


def search_with_grounding(query: str) -> dict:
    """
    使用 Gemini Google Search Grounding 进行实时搜索
    
    返回格式: {"success": bool, "response": str, "message": str}
    """
    try:
        # 延迟导入，避免模块加载时的循环依赖
        from app import get_client
        from google.genai import types
    except ImportError:
        from web.app import get_client
        from google.genai import types
    
    try:
        client = get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction="你是 Koto，一个智能助手。使用搜索结果提供准确、实时的信息。用中文回答，格式清晰。"
            )
        )
        
        if response.text:
            return {
                "success": True,
                "message": response.text,
                "response": response.text,  # 向后兼容
            }
        else:
            return {
                "success": False,
                "error": "搜索未返回结果",
                "message": "搜索未返回结果",
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"搜索失败: {str(e)}",
            "message": f"搜索失败: {str(e)}",
        }
