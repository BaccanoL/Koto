#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语音转写与总结系统 - 将音频转换为文本，并自动提取关键总结
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


class SpeechTranscriber:
    """语音转写与总结系统"""
    
    def __init__(self, output_dir: str = "workspace/transcripts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化语音识别引擎
        self.recognizer = self._init_recognizer()
    
    def _init_recognizer(self):
        """初始化语音识别引擎"""
        try:
            # 优先使用 SpeechRecognition 库（支持多种引擎）
            import speech_recognition as sr
            return sr.Recognizer()
        except ImportError:
            print("⚠️ 未安装 SpeechRecognition 库")
            print("安装方法: pip install SpeechRecognition pydub")
            return None
    
    def transcribe_audio_file(self, audio_path: str, language: str = "zh-CN") -> Dict[str, Any]:
        """
        转写音频文件
        
        Args:
            audio_path: 音频文件路径（支持 .mp3, .wav, .m4a 等）
            language: 语言代码（zh-CN/en-US/etc）
        
        Returns:
            转写结果
        """
        if self.recognizer is None:
            return {
                "success": False,
                "error": "语音识别引擎未初始化，请安装 SpeechRecognition"
            }
        
        if not os.path.exists(audio_path):
            return {
                "success": False,
                "error": f"音频文件不存在: {audio_path}"
            }
        
        try:
            import speech_recognition as sr
            
            # 加载音频文件
            with sr.AudioFile(audio_path) as source:
                audio = self.recognizer.record(source)
            
            # 尝试使用 Google Speech-to-Text API（需要网络）
            try:
                text = self.recognizer.recognize_google(audio, language=language)
                engine = "google"
            except sr.UnknownValueError:
                return {
                    "success": False,
                    "error": "无法识别音频内容，请尝试其他文件"
                }
            except sr.RequestError as e:
                return {
                    "success": False,
                    "error": f"语音识别服务连接失败: {str(e)}"
                }
            
            return {
                "success": True,
                "text": text,
                "engine": engine,
                "audio_file": audio_path,
                "language": language,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"转写失败: {str(e)}"
            }
    
    def transcribe_microphone(self, duration: int = 30, language: str = "zh-CN") -> Dict[str, Any]:
        """
        从麦克风录音并转写
        
        Args:
            duration: 录音时长（秒）
            language: 语言代码
        
        Returns:
            转写结果
        """
        if self.recognizer is None:
            return {
                "success": False,
                "error": "语音识别引擎未初始化"
            }
        
        try:
            import speech_recognition as sr
            
            print(f"🎤 开始录音（{duration}秒）...")
            
            with sr.Microphone() as source:
                # 调整麦克风灵敏度
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # 开始录音
                print("正在听取...")
                audio = self.recognizer.listen(source, timeout=duration)
            
            print("正在识别...")
            
            # 识别
            try:
                text = self.recognizer.recognize_google(audio, language=language)
                
                return {
                    "success": True,
                    "text": text,
                    "engine": "google",
                    "source": "microphone",
                    "duration": duration,
                    "language": language,
                    "timestamp": datetime.now().isoformat()
                }
            except sr.UnknownValueError:
                return {
                    "success": False,
                    "error": "无法识别音频内容"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"录音转写失败: {str(e)}"
            }
    
    def extract_keywords_and_summary(self, text: str, max_keywords: int = 10, 
                                    max_summary_lines: int = 3) -> Dict[str, Any]:
        """
        使用 AI 提取关键词和总结
        
        Args:
            text: 转写文本
            max_keywords: 最多提取关键词数
            max_summary_lines: 摘要最多行数
        
        Returns:
            关键词和摘要
        """
        try:
            from google import genai
            from dotenv import load_dotenv
            
            # 加载 API 密钥
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                return {
                    "success": False,
                    "error": "未配置 GEMINI_API_KEY"
                }
            
            client = genai.Client(api_key=api_key)
            
            # 构建提示词
            prompt = f"""分析以下转写文本，并执行两个任务：

1. 提取最多 {max_keywords} 个关键词或核心概念（用逗号分隔）
2. 生成最多 {max_summary_lines} 行的关键总结

转写文本：
---
{text}
---

请按以下格式输出：

关键词：[关键词列表]

关键总结：
[摘要第一行]
[摘要第二行]
[摘要第三行]
"""
            
            # 调用 API
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500
                )
            )
            
            result_text = response.text
            
            # 解析结果
            keywords = []
            summary = []
            
            lines = result_text.split('\n')
            in_summary = False
            
            for line in lines:
                line = line.strip()
                if line.startswith('关键词：'):
                    keywords_str = line.replace('关键词：', '').strip()
                    keywords = [k.strip() for k in keywords_str.split('，')]
                elif line.startswith('关键总结：'):
                    in_summary = True
                elif in_summary and line and not line.startswith('---'):
                    summary.append(line)
            
            return {
                "success": True,
                "keywords": keywords,
                "summary": summary,
                "raw_response": result_text
            }
        
        except Exception as e:
            # 本地简单处理（如果 API 不可用）
            return self._extract_keywords_simple(text, max_keywords, max_summary_lines)
    
    def _extract_keywords_simple(self, text: str, max_keywords: int = 10, 
                                 max_summary_lines: int = 3) -> Dict[str, Any]:
        """
        简单的本地关键词提取（不需要 API）
        """
        from collections import Counter
        import re
        
        # 分词（简单方式）
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
        
        # 过滤停用词
        stop_words = {
            '的', '了', '和', '是', '在', '中', '到', '了', '与', '或', '等',
            'a', 'the', 'is', 'are', 'and', 'or', 'of', 'in', 'to'
        }
        
        filtered_words = [w for w in words if w not in stop_words and len(w) > 1]
        
        # 统计词频
        word_freq = Counter(filtered_words)
        keywords = [w for w, _ in word_freq.most_common(max_keywords)]
        
        # 简单摘要（提取前几个句子）
        sentences = re.split(r'[。！？，；]', text)
        summary = [s.strip() for s in sentences[:max_summary_lines] if s.strip()]
        
        return {
            "success": True,
            "keywords": keywords,
            "summary": summary,
            "method": "simple"
        }

    def _extract_action_items_simple(self, text: str) -> Dict[str, List[str]]:
        """
        本地行动项与决策提取（不需要 API）
        """
        import re

        sentences = [s.strip() for s in re.split(r'[。！？!?\n\r]', text) if s.strip()]

        action_patterns = re.compile(
            r'(需要|应该|请|务必|安排|负责|跟进|完成|提交|确认|对接|准备|落实|处理|修复|改进|在.+?前)'
        )
        decision_patterns = re.compile(r'(决定|确认|达成|同意|通过|定为|确定|结论|共识)')

        action_items = [s for s in sentences if action_patterns.search(s)]
        decisions = [s for s in sentences if decision_patterns.search(s)]

        # 参会人提取（简单规则：参会人员/参会人/参会：后面的名单）
        participants = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("参会人员") or line.startswith("参会人") or line.startswith("参会："):
                parts = re.split(r'[:：]', line, maxsplit=1)
                if len(parts) == 2:
                    names = re.split(r'[、,，\s]+', parts[1].strip())
                    participants.extend([n for n in names if n])

        # 去重保持顺序
        def _dedupe(items: List[str]) -> List[str]:
            seen = set()
            result = []
            for item in items:
                if item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        return {
            "action_items": _dedupe(action_items),
            "decisions": _dedupe(decisions),
            "participants": _dedupe(participants)
        }

    def _segment_speakers_simple(self, text: str) -> List[Dict[str, str]]:
        """
        简单发言人分段（不需要 API）
        支持格式：
        - 张三：内容...
        - 张三: 内容...
        - [00:01] 张三：内容...
        """
        import re

        segments = []
        current_speaker = None
        current_text = []

        speaker_pattern = re.compile(r'^(\[\d{2}:\d{2}\]\s*)?([^:：]{1,20})[:：]\s*(.+)$')

        def flush():
            nonlocal current_speaker, current_text
            if current_speaker and current_text:
                segments.append({
                    "speaker": current_speaker,
                    "content": " ".join(current_text).strip()
                })
            current_speaker = None
            current_text = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = speaker_pattern.match(line)
            if match:
                flush()
                current_speaker = match.group(2).strip()
                current_text.append(match.group(3).strip())
            else:
                if current_speaker:
                    current_text.append(line)

        flush()
        return segments
    
    def generate_transcript_document(self, text: str, keywords: List[str] = None, 
                                    summary: List[str] = None, title: str = None,
                                    output_format: str = "txt",
                                    action_items: List[str] = None,
                                    decisions: List[str] = None,
                                    participants: List[str] = None,
                                    speaker_segments: List[Dict[str, str]] = None) -> str:
        """
        生成转写文档
        
        Args:
            text: 完整转写文本
            keywords: 关键词列表
            summary: 摘要行
            title: 文档标题
            output_format: 输出格式 (txt/md/docx)
            action_items: 行动项列表
            decisions: 决策要点
            participants: 参会人员
            speaker_segments: 发言人分段
        
        Returns:
            输出文件路径
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"transcript_{timestamp}"
        
        if title:
            filename_base = f"{title}_{timestamp}"
        
        # 生成内容
        content_lines = []
        
        if title:
            content_lines.append(f"# {title}\n")
        
        # 转写时间
        content_lines.append(f"转写时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 关键词
        if keywords:
            content_lines.append("## 关键词\n")
            keywords_str = "、".join(keywords)
            content_lines.append(f"{keywords_str}\n")
        
        # 关键总结
        if summary:
            content_lines.append("## 关键总结\n")
            for line in summary:
                content_lines.append(f"{line}\n")

        # 参会人员
        if participants:
            content_lines.append("## 参会人员\n")
            content_lines.append("、".join(participants) + "\n")

        # 行动项
        if action_items:
            content_lines.append("## 行动项\n")
            for item in action_items:
                content_lines.append(f"- {item}\n")

        # 决策要点
        if decisions:
            content_lines.append("## 决策要点\n")
            for item in decisions:
                content_lines.append(f"- {item}\n")

        # 发言人记录
        if speaker_segments:
            content_lines.append("## 发言人记录\n")
            for seg in speaker_segments:
                speaker = seg.get("speaker", "")
                content = seg.get("content", "")
                if speaker and content:
                    content_lines.append(f"【{speaker}】{content}\n")
        
        # 完整转写
        content_lines.append("## 完整转写\n")
        content_lines.append(f"{text}\n")
        
        content = "\n".join(content_lines)
        
        # 保存文件
        if output_format == "txt":
            filepath = os.path.join(self.output_dir, f"{filename_base}.txt")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        elif output_format == "md":
            filepath = os.path.join(self.output_dir, f"{filename_base}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        elif output_format == "docx":
            from web.document_generator import save_docx
            filepath = save_docx(
                content,
                title=title or "语音转写",
                output_dir=self.output_dir,
                filename=filename_base
            )
        
        return filepath
    
    def process_audio_complete(self, audio_path: str, language: str = "zh-CN", 
                               output_format: str = "txt", title: str = None,
                               auto_summary: bool = True,
                               extract_meeting_items: bool = True) -> Dict[str, Any]:
        """
        完整处理流程：转写 → 总结 → 生成文档
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码
            output_format: 输出格式
            title: 文档标题
            auto_summary: 是否自动生成总结
            extract_meeting_items: 是否提取会议行动项/决策/参会人
        
        Returns:
            完整处理结果
        """
        # 第一步：转写
        print(f"📝 开始转写 {audio_path}...")
        transcribe_result = self.transcribe_audio_file(audio_path, language)
        
        if not transcribe_result["success"]:
            return transcribe_result
        
        text = transcribe_result["text"]
        print(f"✅ 转写完成: {len(text)} 字符")
        
        keywords = None
        summary = None
        action_items = None
        decisions = None
        participants = None
        speaker_segments = None
        
        # 第二步：提取关键词和总结
        if auto_summary:
            print("📊 提取关键词和总结...")
            summary_result = self.extract_keywords_and_summary(text)
            
            if summary_result["success"]:
                keywords = summary_result.get("keywords")
                summary = summary_result.get("summary")
                print(f"✅ 提取完成: {len(keywords)} 个关键词, {len(summary)} 行摘要")
            else:
                print(f"⚠️ 总结失败: {summary_result.get('error')}")

        # 会议要素提取
        if extract_meeting_items:
            meeting_items = self._extract_action_items_simple(text)
            action_items = meeting_items.get("action_items")
            decisions = meeting_items.get("decisions")
            participants = meeting_items.get("participants")
            speaker_segments = self._segment_speakers_simple(text)
        
        # 第三步：生成文档
        print("📄 生成文档...")
        output_file = self.generate_transcript_document(
            text,
            keywords=keywords,
            summary=summary,
            title=title,
            output_format=output_format,
            action_items=action_items,
            decisions=decisions,
            participants=participants,
            speaker_segments=speaker_segments
        )
        
        print(f"✅ 文档已保存: {output_file}")
        
        return {
            "success": True,
            "text": text,
            "keywords": keywords,
            "summary": summary,
            "action_items": action_items,
            "decisions": decisions,
            "participants": participants,
            "speaker_segments": speaker_segments,
            "output_file": output_file,
            "format": output_format,
            "char_count": len(text),
            "word_count": len(text.split())
        }


if __name__ == "__main__":
    transcriber = SpeechTranscriber()
    
    print("=" * 60)
    print("语音转写与总结系统测试")
    print("=" * 60)
    
    # 测试音频文件（如果存在）
    test_audio = "test_audio.wav"
    
    if os.path.exists(test_audio):
        print(f"\n1. 测试文件转写: {test_audio}")
        result = transcriber.process_audio_complete(
            test_audio,
            language="zh-CN",
            output_format="txt",
            title="测试转写",
            auto_summary=True
        )
        
        if result["success"]:
            print(f"\n✅ 转写成功")
            print(f"   字符数: {result['char_count']}")
            print(f"   关键词: {', '.join(result['keywords'] or [])}")
            print(f"   保存位置: {result['output_file']}")
    else:
        print(f"\n⚠️ 测试音频文件不存在: {test_audio}")
        print("   支持的格式: .wav, .mp3, .m4a, .flac")
    
    print("\n✅ 语音转写系统就绪")
