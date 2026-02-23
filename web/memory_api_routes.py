# ═══════════════════════════════════════════════════════════════
# 增强记忆系统API端点
# ═══════════════════════════════════════════════════════════════

from flask import jsonify, request

def register_memory_routes(app, get_memory_manager):
    """注册记忆系统API路由到Flask app
    
    Args:
        app: Flask应用实例
        get_memory_manager: 获取记忆管理器的函数
    """
    
    # ==================== 基础记忆 CRUD API ====================
    
    @app.route('/api/memories', methods=['GET'])
    def get_all_memories():
        """获取所有记忆"""
        try:
            memory_mgr = get_memory_manager()
            memories = memory_mgr.get_all_memories()
            return jsonify(memories)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/memories', methods=['POST'])
    def add_memory():
        """添加新记忆"""
        try:
            data = request.json
            content = data.get('content', '').strip()
            category = data.get('category', 'user_preference')
            source = data.get('source', 'user')
            
            if not content:
                return jsonify({"success": False, "error": "内容不能为空"}), 400
            
            memory_mgr = get_memory_manager()
            new_memory = memory_mgr.add_memory(content, category, source)
            
            return jsonify({
                "success": True,
                "memory": new_memory
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/memories/<int:memory_id>', methods=['DELETE'])
    def delete_memory(memory_id):
        """删除记忆"""
        try:
            memory_mgr = get_memory_manager()
            success = memory_mgr.delete_memory(memory_id)
            
            if success:
                return jsonify({"success": True, "message": "记忆已删除"})
            else:
                return jsonify({"success": False, "error": "记忆不存在"}), 404
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    # ==================== 增强功能 API ====================
    
    @app.route('/api/memory/profile', methods=['GET'])
    def get_user_profile():
        """获取用户画像"""
        try:
            memory_mgr = get_memory_manager()
            
            # 检查是否是增强版本
            if hasattr(memory_mgr, 'user_profile'):
                profile = memory_mgr.get_profile()
                summary = memory_mgr.user_profile.get_brief_summary()
                
                return jsonify({
                    "success": True,
                    "profile": profile,
                    "summary": summary
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "当前使用基础记忆管理器，不支持用户画像"
                })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500


    @app.route('/api/memory/profile', methods=['POST'])
    def update_user_profile():
        """手动更新用户画像"""
        try:
            data = request.json
            memory_mgr = get_memory_manager()
            
            if hasattr(memory_mgr, 'update_profile_manually'):
                memory_mgr.update_profile_manually(data)
                return jsonify({"success": True, "message": "用户画像已更新"})
            else:
                return jsonify({
                    "success": False,
                    "message": "当前使用基础记忆管理器"
                })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500


    @app.route('/api/memory/auto-learn', methods=['POST'])
    def trigger_auto_learn():
        """触发自动学习（测试用）"""
        try:
            data = request.json
            user_msg = data.get('user_message', '')
            ai_msg = data.get('ai_message', '')
            
            memory_mgr = get_memory_manager()
            
            if hasattr(memory_mgr, 'auto_extract_from_conversation'):
                result = memory_mgr.auto_extract_from_conversation(
                    user_msg, ai_msg
                )
                return jsonify({
                    "success": True,
                    "result": result
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "当前版本不支持自动学习"
                })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500


    @app.route('/api/memory/stats', methods=['GET'])
    def get_memory_stats():
        """获取记忆系统统计"""
        try:
            memory_mgr = get_memory_manager()
            
            memories = memory_mgr.get_all_memories()
            
            # 统计信息
            stats = {
                "total_memories": len(memories),
                "by_category": {},
                "by_source": {},
                "most_used": []
            }
            
            # 按分类统计
            for m in memories:
                cat = m.get("category", "unknown")
                stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
                
                src = m.get("source", "unknown")
                stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
            
            # 最常使用的记忆
            sorted_memories = sorted(
                memories, 
                key=lambda x: x.get("use_count", 0), 
                reverse=True
            )
            stats["most_used"] = [
                {
                    "content": m["content"][:50] + "..." if len(m["content"]) > 50 else m["content"],
                    "use_count": m.get("use_count", 0)
                }
                for m in sorted_memories[:5]
            ]
            
            # 用户画像统计
            if hasattr(memory_mgr, 'user_profile'):
                profile = memory_mgr.user_profile.profile
                stats["profile_stats"] = {
                    "total_interactions": profile["metadata"]["total_interactions"],
                    "programming_languages": len(profile["technical_background"]["programming_languages"]),
                    "tools": len(profile["technical_background"]["tools"]),
                    "preferences_count": len(profile["preferences"]["likes"]) + len(profile["preferences"]["dislikes"])
                }
            
            return jsonify({
                "success": True,
                "stats": stats
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    print("🧠 增强记忆系统API路由已注册")
