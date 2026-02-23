#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
剪贴板与截图助手 - 本地OCR识别、自动入库
"""

import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from PIL import Image, ImageGrab
import io


class ClipboardOCRAssistant:
    """剪贴板与截图助手"""
    
    def __init__(self, output_dir: str = "workspace/clipboard"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 尝试导入 OCR 引擎
        self.ocr_engine = self._init_ocr_engine()
    
    def _init_ocr_engine(self):
        """初始化 OCR 引擎"""
        try:
            # 优先使用 PaddleOCR（更适合中文）
            from paddleocr import PaddleOCR
            return PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        except ImportError:
            try:
                # 备选方案：pytesseract
                import pytesseract
                return "tesseract"
            except ImportError:
                print("⚠️ 未安装OCR引擎，OCR功能不可用")
                print("安装方法: pip install paddleocr 或 pip install pytesseract")
                return None
    
    def capture_screenshot(self, save_image: bool = True) -> Dict[str, Any]:
        """
        截取整个屏幕
        
        Args:
            save_image: 是否保存图片
        
        Returns:
            截图结果
        """
        try:
            # 截取屏幕
            screenshot = ImageGrab.grab()
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            if save_image:
                screenshot.save(filepath)
            
            return {
                "success": True,
                "image": screenshot,
                "filepath": filepath if save_image else None,
                "size": screenshot.size,
                "timestamp": timestamp
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def capture_clipboard_image(self, save_image: bool = True) -> Dict[str, Any]:
        """
        获取剪贴板中的图片
        
        Args:
            save_image: 是否保存图片
        
        Returns:
            图片信息
        """
        try:
            # 从剪贴板获取图片
            image = ImageGrab.grabclipboard()
            
            if image is None:
                return {
                    "success": False,
                    "error": "剪贴板中没有图片"
                }
            
            if not isinstance(image, Image.Image):
                return {
                    "success": False,
                    "error": "剪贴板内容不是图片格式"
                }
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"clipboard_{timestamp}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            if save_image:
                image.save(filepath)
            
            return {
                "success": True,
                "image": image,
                "filepath": filepath if save_image else None,
                "size": image.size,
                "timestamp": timestamp
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def ocr_image(self, image_path: str) -> Dict[str, Any]:
        """
        对图片执行OCR识别
        
        Args:
            image_path: 图片路径或PIL Image对象
        
        Returns:
            OCR结果
        """
        if self.ocr_engine is None:
            return {
                "success": False,
                "error": "OCR引擎未初始化"
            }
        
        try:
            # 加载图片
            if isinstance(image_path, str):
                if not os.path.exists(image_path):
                    return {"success": False, "error": "图片文件不存在"}
                image = Image.open(image_path)
            else:
                image = image_path
            
            # 执行OCR
            if isinstance(self.ocr_engine, str) and self.ocr_engine == "tesseract":
                # 使用 Tesseract
                import pytesseract
                text = pytesseract.image_to_string(image, lang='chi_sim+eng')
                
                return {
                    "success": True,
                    "text": text.strip(),
                    "engine": "tesseract"
                }
            else:
                # 使用 PaddleOCR
                result = self.ocr_engine.ocr(image_path if isinstance(image_path, str) else image, cls=True)
                
                # 提取文本
                texts = []
                for line in result[0]:
                    texts.append(line[1][0])  # line[1][0] 是识别的文本
                
                return {
                    "success": True,
                    "text": '\n'.join(texts),
                    "details": result,
                    "engine": "paddleocr"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR识别失败: {str(e)}"
            }
    
    def capture_and_ocr(self, source: str = "screenshot", save_image: bool = True) -> Dict[str, Any]:
        """
        截图/获取剪贴板图片并执行OCR
        
        Args:
            source: 来源 (screenshot/clipboard)
            save_image: 是否保存图片
        
        Returns:
            完整结果
        """
        # 获取图片
        if source == "screenshot":
            capture_result = self.capture_screenshot(save_image=save_image)
        else:
            capture_result = self.capture_clipboard_image(save_image=save_image)
        
        if not capture_result["success"]:
            return capture_result
        
        # 执行OCR
        image = capture_result["image"]
        ocr_result = self.ocr_image(image)
        
        # 合并结果
        return {
            "success": True,
            "source": source,
            "image_path": capture_result.get("filepath"),
            "image_size": capture_result["size"],
            "text": ocr_result.get("text", ""),
            "ocr_success": ocr_result["success"],
            "timestamp": capture_result["timestamp"]
        }
    
    def auto_index_to_knowledge_base(self, ocr_result: Dict[str, Any], kb_path: str = "workspace/knowledge_base"):
        """
        将OCR结果自动索引到知识库
        
        Args:
            ocr_result: OCR结果
            kb_path: 知识库路径
        """
        if not ocr_result.get("ocr_success"):
            return {"success": False, "error": "OCR未成功"}
        
        try:
            from knowledge_base import KnowledgeBase
            
            kb = KnowledgeBase(kb_path)
            
            # 创建文本文档
            timestamp = ocr_result.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
            doc_filename = f"ocr_{timestamp}.txt"
            doc_path = os.path.join(self.output_dir, doc_filename)
            
            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(f"# OCR识别结果\n")
                f.write(f"来源: {ocr_result.get('source', 'unknown')}\n")
                f.write(f"时间: {timestamp}\n")
                if ocr_result.get("image_path"):
                    f.write(f"图片: {ocr_result['image_path']}\n")
                f.write(f"\n## 识别文本\n\n{ocr_result['text']}\n")
            
            # 添加到知识库
            kb.add_document(doc_path)
            
            return {
                "success": True,
                "doc_path": doc_path,
                "indexed": True
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"索引到知识库失败: {str(e)}"
            }
    
    def monitor_clipboard(self, interval: int = 1, duration: int = 60, auto_ocr: bool = True):
        """
        监控剪贴板变化
        
        Args:
            interval: 检查间隔（秒）
            duration: 监控时长（秒）
            auto_ocr: 是否自动OCR
        """
        print(f"🔍 开始监控剪贴板（{duration}秒）...")
        
        last_image = None
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                current_image = ImageGrab.grabclipboard()
                
                # 检查是否有新图片
                if isinstance(current_image, Image.Image):
                    # 简单对比（可以优化为图片哈希）
                    if last_image is None or current_image.tobytes() != last_image.tobytes():
                        print("📋 检测到新图片！")
                        
                        result = self.capture_clipboard_image(save_image=True)
                        
                        if auto_ocr and result["success"]:
                            ocr_result = self.ocr_image(result["image"])
                            if ocr_result["success"]:
                                print(f"✅ OCR识别成功: {len(ocr_result['text'])} 字符")
                                print(f"内容预览: {ocr_result['text'][:100]}...")
                        
                        last_image = current_image
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n⏹️ 监控已停止")


if __name__ == "__main__":
    assistant = ClipboardOCRAssistant()
    
    print("=" * 60)
    print("剪贴板与截图助手测试")
    print("=" * 60)
    
    # 测试截图功能
    print("\n1. 测试截图功能...")
    screenshot_result = assistant.capture_screenshot(save_image=True)
    if screenshot_result["success"]:
        print(f"✅ 截图成功: {screenshot_result['filepath']}")
        print(f"   尺寸: {screenshot_result['size']}")
    
    # 测试剪贴板图片
    print("\n2. 测试剪贴板图片...")
    clipboard_result = assistant.capture_clipboard_image(save_image=False)
    if clipboard_result["success"]:
        print(f"✅ 获取剪贴板图片成功")
    else:
        print(f"ℹ️ {clipboard_result['error']}")
    
    # 测试OCR（如果有引擎）
    if assistant.ocr_engine:
        print("\n3. 测试OCR功能...")
        if screenshot_result["success"]:
            ocr_result = assistant.ocr_image(screenshot_result["filepath"])
            if ocr_result["success"]:
                print(f"✅ OCR识别成功")
                print(f"   文本长度: {len(ocr_result['text'])} 字符")
                print(f"   预览: {ocr_result['text'][:100]}...")
    else:
        print("\n⚠️ OCR引擎未安装，跳过OCR测试")
    
    print("\n✅ 剪贴板与截图助手就绪")
