#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PPT多模型协作系统 - 集成指南和使用说明

此文档说明如何在 Koto 应用中集成和使用多模型PPT生成系统。

## 系统架构

├── ppt_master.py               # 主协调器和蓝图系统
│   ├── PPTResourceManager      # 资源管理（搜索结果、图像、数据）
│   ├── PPTContentPlanner       # 内容规划（大纲、结构化内容）
│   ├── PPTLayoutPlanner        # 排版规划（自动布局决策）
│   ├── PPTImageMatcher         # 图文匹配和图像提示生成
│   └── PPTMasterOrchestrator   # 主编排器
│
├── ppt_synthesizer.py          # PPT合成引擎
│   ├── PPTSynthesizer          # 使用蓝图生成最终PPT
│   ├── PPTBeautyOptimizer      # 美化和视觉优化
│   └── PPTQualityEnsurance     # 质量验证
│
├── ppt_pipeline.py             # 完整生成管道
│   ├── PPTGenerationPipeline   # 统一的生成接口
│   └── PPTGenerationTaskHandler# 任务处理器（用于chat_stream）
│
└── app.py                       # 主应用（需要集成）

## 工作流程

1. **用户请求** 
   用户在Koto中说："做一个关于AI发展的PPT，要有配图和数据"

2. **任务检测**
   SmartDispatcher.analyze() 检测为 PPT 任务
   MultiTaskDecomposer 识别为复合任务 (搜索 -> 图像 -> PPT生成)

3. **资源收集**
   - WEB_SEARCH: 搜索AI发展相关数据
   - PAINTER: 生成2-3张关于AI的配图

4. **蓝图生成**
   PPTMasterOrchestrator 基于资源生成详细蓝图：
   - 标题页、章节页、内容页、总结页
   - 每页的完整排版配置
   - 图文映射和美化规则

5. **合成输出**
   PPTSynthesizer 使用蓝图生成最终PPT文件：
   - 应用配色方案
   - 排版和美化
   - 集成图片和内容

6. **质量验证**
   PPTQualityEnsurance 检查：
   - 幻灯片数量
   - 内容密度
   - 图片比例
   - 排版多样性

## 在 chat_stream 中的集成示例

在 app.py 的 chat_stream() 函数中，添加如下处理：

```python
# === 增强型PPT生成处理 ===
if task_type == "MULTI_STEP" and context_info.get("multi_step_info", {}).get("pattern") == "enhanced_ppt":
    print(f"[STREAM] 🎨 执行多模型协作PPT生成")
    
    def generate_enhanced_ppt():
        # 发生分类信息
        yield f"data: {json.dumps({'type': 'classification', 'task_type': 'PPT', 'route_method': route_method})}\n\n"
        
        # 初始化任务处理器
        handler = PPTGenerationTaskHandler(get_client(), WORKSPACE_DIR)
        
        # 定义回调函数
        async def search_executor(query, context):
            # 调用现有的web搜索功能
            result = await TaskOrchestrator._execute_web_search(query, context)
            return result
        
        async def image_generator(prompt, context):
            # 调用现有的图像生成功能
            result = await TaskOrchestrator._execute_painter(prompt, context)
            return result
        
        # 执行生成
        try:
            result = asyncio.run(handler.handle_ppt_generation_task(
                user_request=user_input,
                documents_dir=settings_manager.documents_dir,
                search_executor=search_executor,
                image_generator=image_generator
            ))
            
            # 格式化和返回结果
            formatted = format_ppt_generation_result(result)
            yield f"data: {json.dumps({'type': 'response', 'content': formatted})}\n\n"
            
            # 保存到历史记录
            history.append({
                'role': 'model',
                'parts': [formatted]
            })
            
        except Exception as e:
            error_msg = f"❌ PPT生成失败: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
    
    yield from generate_enhanced_ppt()
    session_manager.save(f"{session_name}.json", history)
    return
```

## 直接使用管道（独立脚本示例）

```python
import asyncio
from ppt_pipeline import PPTGenerationPipeline

async def main():
    pipeline = PPTGenerationPipeline(ai_client=client, workspace_dir="./workspace")
    
    result = await pipeline.generate(
        user_request="做一个关于量子计算的PPT",
        output_path="./workspace/documents/quantum_computing.pptx",
        search_results=[...],  # 可选搜索结果
        existing_images=[...]   # 可选现有图像
    )
    
    print(f"PPT已生成: {result['output_path']}")
    print(f"幻灯片数: {result['slide_count']}")
    print(f"质量评分: {result['quality']['score']}/100")

asyncio.run(main())
```

## 核心特性

### 1. 智能内容规划
- 使用 Gemini 2.0 Flash Exp 解析用户需求
- 生成结构化的PPT大纲
- 自动识别内容层次和关键要点

### 2. 多模型资源协调
- **文本模型**: 大纲生成、内容编写
- **图像模型**: 配图生成、视觉设计
- **规划模型**: 排版决策、布局优化

### 3. 智能排版系统
- 自适应布局：根据内容自动选择最优排版
- 内容密度自适应：避免过密或过稀
- 视觉层次设计：标题、重点、细节的合理分配

### 4. 质量保证体系
六维度质量评估：
- 幻灯片数量 (5-15张)
- 内容密度 (2-6个要点/页)
- 标题完整性 (100%)
- 图片比例 (10-70%)
- 文字长度 (≤700字/页)
- 排版多样性 (3+种类型)

### 5. 美化引擎
- 自动配色方案调整
- 文字排版优化（字体、大小、行距）
- 装饰元素添加（边框、阴影、强调）
- 视觉流畅性优化

## 自定义配置

### 调整质量标准

在 `ppt_quality.py` 中修改评分规则：

```python
QUALITY_RULES = {
    "slide_count": {"min": 5, "max": 15, "weight": 20},
    "avg_bullets": {"min": 2, "max": 6, "weight": 15},
    "img_ratio": {"min": 0.1, "max": 0.7, "weight": 20},
    "text_length": {"max": 700, "weight": 15},
    ...
}
```

### 配置关键词和促进词

在 `ppt_master.py` 的 PPTContentPlanner 中：

```python
# 添加特殊关键词处理
SPECIAL_KEYWORDS = {
    "活泼": "light",
    "专业": "formal",
    "创意": "creative",
}
```

## 扩展点

1. **新的幻灯片类型**
   在 `ppt_master.py` SlideType 枚举中添加

2. **自定义美化规则**
   在 `ppt_synthesizer.py` PPTBeautyOptimizer 中扩展

3. **新的数据源**
   在 PPTResourceManager 中添加新的数据收集方法

4. **本地模型支持**
   可集成 Ollama 本地模型进行内容生成

## 故障排除

### 问题：图像无法生成
**解决**: 检查图像模型是否可用，备用使用符号或纯文本

### 问题：排版混乱
**解决**: 调整 PPTLayoutPlanner 中的布局规则

### 问题：质量评分过低
**解决**: 检查 PPTQualityEnsurance 中的评分权重

## 性能指标

- 内容规划: ~3-5 秒（LLM调用）
- 图像生成: ~10-30 秒/张（模型相关）
- 排版规划: ~500ms（本地算法）
- PPT合成: ~2-3 秒
- **总耗时**: 15-50 秒（取决于资源）

## 未来增强方向

1. ✅ 多模型协作（已实现）
2. ✅ 智能排版（已实现）
3. ✅ 质量验证（已实现）
4. ⬜ 交互式编辑（UI集成）
5. ⬜ 模板库（预定义样式）
6. ⬜ 主题迁移（跨模板套用）
7. ⬜ 本地模型全离线支持

## 许可证

与 Koto 主项目相同

## 联系与支持

获取更多信息，请查看：
- docs/ 目录中的使用指南
- web/ 目录中的代码示例
"""

# 【导入示例】
if __name__ == "__main__":
    print(__doc__)
