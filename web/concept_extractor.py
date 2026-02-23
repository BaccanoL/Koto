#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
概念提取模块 - Koto智能文件大脑的核心
使用TF-IDF算法从文件内容中提取关键概念和主题
"""

import re
import math
import sqlite3
from typing import List, Dict, Tuple, Set
from collections import Counter, defaultdict
from pathlib import Path
import json
from datetime import datetime

# 简化的中文停用词表
CHINESE_STOPWORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '里', '为', '能', '这个', '与', '及', '而', '或', '等',
    '可以', '但', '因为', '所以', '如果', '这样', '那样', '什么', '怎么', '为什么',
    'how', 'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in',
    'with', 'to', 'for', 'of', 'as', 'by', 'from', 'that', 'this', 'it', 'be', 'are'
}

class ConceptExtractor:
    """概念提取器 - 使用TF-IDF算法提取文件关键概念"""
    
    def __init__(self, db_path: str = "config/concepts.db"):
        """
        初始化概念提取器
        
        Args:
            db_path: SQLite数据库路径，用于存储概念和文件关联
        """
        self.db_path = db_path
        self._ensure_db()
        
    def _ensure_db(self):
        """确保数据库和表结构存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 文件概念表 - 存储每个文件提取的概念
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                concept TEXT NOT NULL,
                tf_idf_score REAL NOT NULL,
                extraction_time TEXT NOT NULL,
                UNIQUE(file_path, concept)
            )
        """)
        
        # 概念统计表 - 存储全局概念统计
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concept_stats (
                concept TEXT PRIMARY KEY,
                document_frequency INTEGER DEFAULT 1,
                total_occurrences INTEGER DEFAULT 0,
                last_updated TEXT
            )
        """)
        
        # 文件元数据表 - 存储文件处理信息
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_path TEXT PRIMARY KEY,
                total_words INTEGER,
                unique_concepts INTEGER,
                last_analyzed TEXT,
                content_hash TEXT
            )
        """)
        
        # 创建索引加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_concepts_path ON file_concepts(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_concepts_concept ON file_concepts(concept)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_concepts_score ON file_concepts(tf_idf_score DESC)")
        
        conn.commit()
        conn.close()
    
    def tokenize(self, text: str) -> List[str]:
        """
        分词 - 支持中英文混合
        
        Args:
            text: 要分词的文本
            
        Returns:
            词语列表
        """
        # 尝试导入jieba进行中文分词
        try:
            import jieba
            # 使用jieba分词
            words = list(jieba.cut(text))
        except ImportError:
            # 如果没有jieba，使用简单的正则分词
            # 提取中文字符（2-3个字的词）和英文单词
            chinese_pattern = r'[\u4e00-\u9fff]{2,3}'
            english_pattern = r'\b[a-zA-Z]{3,}\b'
            
            chinese_words = re.findall(chinese_pattern, text)
            english_words = re.findall(english_pattern, text.lower())
            
            words = chinese_words + english_words
        
        # 过滤停用词和短词
        filtered_words = [
            w.strip().lower() for w in words 
            if len(w.strip()) >= 2 and w.strip().lower() not in CHINESE_STOPWORDS
        ]
        
        return filtered_words
    
    def calculate_tf(self, words: List[str]) -> Dict[str, float]:
        """
        计算词频(TF - Term Frequency)
        
        Args:
            words: 词语列表
            
        Returns:
            {词语: TF值} 字典
        """
        if not words:
            return {}
        
        word_count = Counter(words)
        total_words = len(words)
        
        # TF = 词在文档中出现次数 / 文档总词数
        tf_dict = {word: count / total_words for word, count in word_count.items()}
        
        return tf_dict
    
    def get_idf(self, concept: str) -> float:
        """
        获取逆文档频率(IDF - Inverse Document Frequency)
        
        Args:
            concept: 概念/词语
            
        Returns:
            IDF值
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取包含该概念的文档数
        cursor.execute("SELECT document_frequency FROM concept_stats WHERE concept = ?", (concept,))
        result = cursor.fetchone()
        
        # 获取总文档数
        cursor.execute("SELECT COUNT(DISTINCT file_path) FROM file_metadata")
        total_docs = cursor.fetchone()[0] or 1
        
        conn.close()
        
        if result:
            doc_freq = result[0]
        else:
            doc_freq = 1  # 新概念，假设出现在1个文档中
        
        # IDF = log(总文档数 / (包含该词的文档数 + 1))
        idf = math.log((total_docs + 1) / (doc_freq + 1)) + 1
        
        return idf
    
    def extract_concepts(self, text: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        从文本中提取关键概念
        
        Args:
            text: 要分析的文本
            top_n: 返回前N个关键概念
            
        Returns:
            [(概念, TF-IDF分数), ...] 按分数降序排列
        """
        # 分词
        words = self.tokenize(text)
        
        if not words:
            return []
        
        # 计算TF
        tf_dict = self.calculate_tf(words)
        
        # 计算TF-IDF
        tfidf_scores = {}
        for word, tf in tf_dict.items():
            idf = self.get_idf(word)
            tfidf_scores[word] = tf * idf
        
        # 按分数排序，返回topN
        sorted_concepts = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_concepts[:top_n]
    
    def analyze_file(self, file_path: str, content: str = None) -> Dict:
        """
        分析文件并提取概念
        
        Args:
            file_path: 文件路径
            content: 文件内容（如果已读取）
            
        Returns:
            分析结果字典
        """
        # 如果没有提供内容，尝试读取文件
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except Exception as e:
                    return {"error": f"无法读取文件: {str(e)}"}
        
        # 计算内容hash
        import hashlib
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # 检查是否已分析过且内容未变
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT content_hash, last_analyzed FROM file_metadata WHERE file_path = ?",
            (file_path,)
        )
        result = cursor.fetchone()
        
        if result and result[0] == content_hash:
            # 内容未变，返回缓存的概念
            cursor.execute(
                "SELECT concept, tf_idf_score FROM file_concepts WHERE file_path = ? ORDER BY tf_idf_score DESC",
                (file_path,)
            )
            concepts = cursor.fetchall()
            conn.close()
            
            return {
                "file_path": file_path,
                "concepts": [{"concept": c[0], "score": c[1]} for c in concepts],
                "cached": True,
                "analyzed_at": result[1]
            }
        
        conn.close()
        
        # 提取新概念
        concepts = self.extract_concepts(content, top_n=20)
        
        # 保存到数据库
        self._save_concepts(file_path, concepts, content_hash, len(self.tokenize(content)))
        
        return {
            "file_path": file_path,
            "concepts": [{"concept": c[0], "score": c[1]} for c in concepts],
            "cached": False,
            "analyzed_at": datetime.now().isoformat()
        }
    
    def _save_concepts(self, file_path: str, concepts: List[Tuple[str, float]], 
                       content_hash: str, total_words: int):
        """保存提取的概念到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        # 删除旧概念
        cursor.execute("DELETE FROM file_concepts WHERE file_path = ?", (file_path,))
        
        # 插入新概念
        for concept, score in concepts:
            cursor.execute("""
                INSERT OR REPLACE INTO file_concepts (file_path, concept, tf_idf_score, extraction_time)
                VALUES (?, ?, ?, ?)
            """, (file_path, concept, score, current_time))
            
            # 更新全局概念统计
            cursor.execute("""
                INSERT INTO concept_stats (concept, document_frequency, total_occurrences, last_updated)
                VALUES (?, 1, 1, ?)
                ON CONFLICT(concept) DO UPDATE SET
                    document_frequency = document_frequency + 1,
                    total_occurrences = total_occurrences + 1,
                    last_updated = ?
            """, (concept, current_time, current_time))
        
        # 更新文件元数据
        cursor.execute("""
            INSERT OR REPLACE INTO file_metadata 
            (file_path, total_words, unique_concepts, last_analyzed, content_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (file_path, total_words, len(concepts), current_time, content_hash))
        
        conn.commit()
        conn.close()
    
    def get_file_concepts(self, file_path: str, limit: int = 10) -> List[Dict]:
        """
        获取文件的概念
        
        Args:
            file_path: 文件路径
            limit: 返回数量限制
            
        Returns:
            概念列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT concept, tf_idf_score, extraction_time
            FROM file_concepts
            WHERE file_path = ?
            ORDER BY tf_idf_score DESC
            LIMIT ?
        """, (file_path, limit))
        
        concepts = []
        for row in cursor.fetchall():
            concepts.append({
                "concept": row[0],
                "score": row[1],
                "extracted_at": row[2]
            })
        
        conn.close()
        return concepts
    
    def find_related_files(self, file_path: str, limit: int = 5) -> List[Dict]:
        """
        查找与指定文件相关的其他文件（基于共享概念）
        
        Args:
            file_path: 文件路径
            limit: 返回数量限制
            
        Returns:
            相关文件列表，按相似度排序
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取该文件的概念
        cursor.execute("""
            SELECT concept, tf_idf_score FROM file_concepts WHERE file_path = ?
        """, (file_path,))
        
        file_concepts = {row[0]: row[1] for row in cursor.fetchall()}
        
        if not file_concepts:
            conn.close()
            return []
        
        # 查找共享概念的其他文件
        concepts_str = ','.join(['?' for _ in file_concepts.keys()])
        cursor.execute(f"""
            SELECT file_path, concept, tf_idf_score
            FROM file_concepts
            WHERE concept IN ({concepts_str}) AND file_path != ?
        """, (*file_concepts.keys(), file_path))
        
        # 计算余弦相似度
        file_vectors = defaultdict(dict)
        for row in cursor.fetchall():
            other_file, concept, score = row
            file_vectors[other_file][concept] = score
        
        # 计算相似度分数
        similarities = []
        for other_file, other_concepts in file_vectors.items():
            # 计算共享概念的加权得分
            shared_score = sum(
                file_concepts.get(c, 0) * score 
                for c, score in other_concepts.items()
            )
            
            # 归一化
            norm1 = math.sqrt(sum(v**2 for v in file_concepts.values()))
            norm2 = math.sqrt(sum(v**2 for v in other_concepts.values()))
            
            if norm1 > 0 and norm2 > 0:
                similarity = shared_score / (norm1 * norm2)
                
                # 获取共享概念
                shared_concepts = set(file_concepts.keys()) & set(other_concepts.keys())
                
                similarities.append({
                    "file_path": other_file,
                    "similarity": similarity,
                    "shared_concepts": list(shared_concepts)[:5]  # 最多显示5个
                })
        
        conn.close()
        
        # 按相似度排序
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:limit]
    
    def get_top_concepts(self, limit: int = 20) -> List[Dict]:
        """
        获取全局最热门的概念
        
        Args:
            limit: 返回数量限制
            
        Returns:
            概念列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT concept, document_frequency, total_occurrences, last_updated
            FROM concept_stats
            ORDER BY document_frequency DESC, total_occurrences DESC
            LIMIT ?
        """, (limit,))
        
        concepts = []
        for row in cursor.fetchall():
            concepts.append({
                "concept": row[0],
                "document_count": row[1],
                "total_occurrences": row[2],
                "last_updated": row[3]
            })
        
        conn.close()
        return concepts
    
    def get_statistics(self) -> Dict:
        """获取概念提取器的统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM file_metadata")
        total_files = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM concept_stats")
        total_concepts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM file_concepts")
        total_relations = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(unique_concepts) FROM file_metadata")
        avg_concepts_per_file = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_files_analyzed": total_files,
            "total_unique_concepts": total_concepts,
            "total_concept_relations": total_relations,
            "avg_concepts_per_file": round(avg_concepts_per_file, 2)
        }


if __name__ == "__main__":
    # 测试代码
    extractor = ConceptExtractor()
    
    # 测试文本
    test_text = """
    人工智能技术正在改变世界。机器学习和深度学习是人工智能的核心技术。
    神经网络模型可以处理复杂的数据。自然语言处理让计算机理解人类语言。
    计算机视觉技术能够识别图像中的物体。强化学习用于训练智能代理。
    """
    
    print("🧠 概念提取测试")
    print("=" * 50)
    
    concepts = extractor.extract_concepts(test_text, top_n=10)
    print("\n提取的关键概念：")
    for concept, score in concepts:
        print(f"  • {concept}: {score:.4f}")
    
    print("\n" + "=" * 50)
    print("✅ 概念提取模块已就绪")
