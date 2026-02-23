#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识图谱模块 - 构建文件关系网络
将文件、概念和关联关系组织成可视化的知识图谱
"""

import sqlite3
import json
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import math

from concept_extractor import ConceptExtractor


class KnowledgeGraph:
    """知识图谱 - 文件关系网络管理器"""
    
    def __init__(self, db_path: str = "config/knowledge_graph.db"):
        """
        初始化知识图谱
        
        Args:
            db_path: 图数据库路径
        """
        self.db_path = db_path
        self.concept_extractor = ConceptExtractor()
        self._ensure_db()
    
    def _ensure_db(self):
        """确保数据库和表结构存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 节点表 - 存储文件和概念节点
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT UNIQUE NOT NULL,
                node_type TEXT NOT NULL,  -- 'file' or 'concept'
                label TEXT NOT NULL,
                metadata TEXT,  -- JSON格式的额外信息
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 边表 - 存储节点之间的关系
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,  -- 'contains', 'relates_to', 'shares_concept'
                weight REAL DEFAULT 1.0,
                metadata TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(source_id, target_id, edge_type)
            )
        """)
        
        # 图快照表 - 存储完整图的快照用于快速加载
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_data TEXT NOT NULL,  -- JSON格式的完整图数据
                node_count INTEGER,
                edge_count INTEGER,
                created_at TEXT NOT NULL
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_weight ON edges(weight DESC)")
        
        conn.commit()
        conn.close()
    
    def add_file_node(self, file_path: str, metadata: Dict = None) -> str:
        """
        添加文件节点到图中
        
        Args:
            file_path: 文件路径
            metadata: 文件元数据
            
        Returns:
            节点ID
        """
        node_id = f"file:{file_path}"
        label = Path(file_path).name
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute("""
            INSERT OR REPLACE INTO nodes (node_id, node_type, label, metadata, created_at, updated_at)
            VALUES (?, 'file', ?, ?, ?, ?)
        """, (node_id, label, metadata_json, current_time, current_time))
        
        conn.commit()
        conn.close()
        
        return node_id
    
    def add_concept_node(self, concept: str, metadata: Dict = None) -> str:
        """
        添加概念节点到图中
        
        Args:
            concept: 概念名称
            metadata: 概念元数据
            
        Returns:
            节点ID
        """
        node_id = f"concept:{concept}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute("""
            INSERT OR REPLACE INTO nodes (node_id, node_type, label, metadata, created_at, updated_at)
            VALUES (?, 'concept', ?, ?, ?, ?)
        """, (node_id, concept, metadata_json, current_time, current_time))
        
        conn.commit()
        conn.close()
        
        return node_id
    
    def add_edge(self, source_id: str, target_id: str, edge_type: str, 
                 weight: float = 1.0, metadata: Dict = None):
        """
        添加边到图中
        
        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            edge_type: 边类型
            weight: 边的权重
            metadata: 边的元数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute("""
            INSERT OR REPLACE INTO edges (source_id, target_id, edge_type, weight, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source_id, target_id, edge_type, weight, metadata_json, current_time))
        
        conn.commit()
        conn.close()
    
    def build_file_graph(self, file_paths: List[str], force_rebuild: bool = False):
        """
        为文件列表构建知识图谱
        
        Args:
            file_paths: 文件路径列表
            force_rebuild: 是否强制重建图
        """
        print(f"🔨 开始构建知识图谱... ({len(file_paths)} 个文件)")
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                # 分析文件提取概念
                result = self.concept_extractor.analyze_file(file_path)
                
                if "error" in result:
                    continue
                
                # 添加文件节点
                file_node_id = self.add_file_node(file_path, {
                    "analyzed_at": result.get("analyzed_at"),
                    "cached": result.get("cached", False)
                })
                
                # 添加概念节点和边
                for concept_data in result.get("concepts", []):
                    concept = concept_data["concept"]
                    score = concept_data["score"]
                    
                    # 添加概念节点
                    concept_node_id = self.add_concept_node(concept, {
                        "score": score
                    })
                    
                    # 添加 file -> concept 边
                    self.add_edge(
                        file_node_id, 
                        concept_node_id,
                        "contains",
                        weight=score,
                        metadata={"tf_idf_score": score}
                    )
                
                if i % 10 == 0:
                    print(f"  ✓ 已处理 {i}/{len(file_paths)} 个文件")
                    
            except Exception as e:
                print(f"  ✗ 处理文件失败 {file_path}: {str(e)}")
        
        # 构建文件间关联
        self._build_file_relations()
        
        # 创建快照
        self._create_snapshot()
        
        print(f"✅ 知识图谱构建完成")
    
    def _build_file_relations(self):
        """构建文件之间的关联边"""
        print("🔗 构建文件关联...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取所有文件节点
        cursor.execute("SELECT node_id FROM nodes WHERE node_type = 'file'")
        file_nodes = [row[0] for row in cursor.fetchall()]
        
        relation_count = 0
        
        for file_node_id in file_nodes:
            file_path = file_node_id.replace("file:", "")
            
            # 查找相关文件
            related_files = self.concept_extractor.find_related_files(file_path, limit=5)
            
            for related in related_files:
                related_path = related["file_path"]
                similarity = related["similarity"]
                
                if similarity > 0.1:  # 只保留相似度大于0.1的关联
                    related_node_id = f"file:{related_path}"
                    
                    self.add_edge(
                        file_node_id,
                        related_node_id,
                        "relates_to",
                        weight=similarity,
                        metadata={
                            "similarity": similarity,
                            "shared_concepts": related["shared_concepts"]
                        }
                    )
                    
                    relation_count += 1
        
        conn.close()
        
        print(f"  ✓ 创建了 {relation_count} 个文件关联")
    
    def get_graph_data(self, max_nodes: int = 100) -> Dict:
        """
        获取图数据用于可视化
        
        Args:
            max_nodes: 最多返回的节点数
            
        Returns:
            D3.js格式的图数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取节点
        cursor.execute("""
            SELECT node_id, node_type, label, metadata
            FROM nodes
            LIMIT ?
        """, (max_nodes,))
        
        nodes = []
        node_ids = set()
        
        for row in cursor.fetchall():
            node_id, node_type, label, metadata_str = row
            node_ids.add(node_id)
            
            try:
                metadata = json.loads(metadata_str)
            except:
                metadata = {}
            
            nodes.append({
                "id": node_id,
                "type": node_type,
                "label": label,
                "metadata": metadata
            })
        
        # 获取边（只包含已加载节点之间的边）
        if node_ids:
            placeholders = ','.join(['?' for _ in node_ids])
            cursor.execute(f"""
                SELECT source_id, target_id, edge_type, weight, metadata
                FROM edges
                WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})
            """, (*node_ids, *node_ids))
            
            edges = []
            for row in cursor.fetchall():
                source, target, edge_type, weight, metadata_str = row
                
                try:
                    metadata = json.loads(metadata_str)
                except:
                    metadata = {}
                
                edges.append({
                    "source": source,
                    "target": target,
                    "type": edge_type,
                    "weight": weight,
                    "metadata": metadata
                })
        else:
            edges = []
        
        conn.close()
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def get_file_neighbors(self, file_path: str, depth: int = 1) -> Dict:
        """
        获取文件的邻居节点（相关文件和概念）
        
        Args:
            file_path: 文件路径
            depth: 搜索深度
            
        Returns:
            邻居图数据
        """
        file_node_id = f"file:{file_path}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查节点是否存在
        cursor.execute("SELECT 1 FROM nodes WHERE node_id = ?", (file_node_id,))
        if not cursor.fetchone():
            conn.close()
            return {"error": "文件节点不存在"}
        
        visited_nodes = set([file_node_id])
        nodes_to_visit = [file_node_id]
        all_nodes = []
        all_edges = []
        
        for _ in range(depth):
            if not nodes_to_visit:
                break
            
            current_batch = nodes_to_visit
            nodes_to_visit = []
            
            for current_node in current_batch:
                # 获取节点信息
                cursor.execute("""
                    SELECT node_id, node_type, label, metadata
                    FROM nodes
                    WHERE node_id = ?
                """, (current_node,))
                
                node_data = cursor.fetchone()
                if node_data:
                    node_id, node_type, label, metadata_str = node_data
                    try:
                        metadata = json.loads(metadata_str)
                    except:
                        metadata = {}
                    
                    all_nodes.append({
                        "id": node_id,
                        "type": node_type,
                        "label": label,
                        "metadata": metadata
                    })
                
                # 获取出边
                cursor.execute("""
                    SELECT target_id, edge_type, weight, metadata
                    FROM edges
                    WHERE source_id = ?
                    ORDER BY weight DESC
                    LIMIT 10
                """, (current_node,))
                
                for row in cursor.fetchall():
                    target, edge_type, weight, metadata_str = row
                    
                    try:
                        metadata = json.loads(metadata_str)
                    except:
                        metadata = {}
                    
                    all_edges.append({
                        "source": current_node,
                        "target": target,
                        "type": edge_type,
                        "weight": weight,
                        "metadata": metadata
                    })
                    
                    if target not in visited_nodes:
                        visited_nodes.add(target)
                        nodes_to_visit.append(target)
        
        conn.close()
        
        return {
            "nodes": all_nodes,
            "edges": all_edges,
            "center_node": file_node_id,
            "depth": depth
        }
    
    def get_concept_cluster(self, concept: str, limit: int = 20) -> Dict:
        """
        获取与概念相关的文件集群
        
        Args:
            concept: 概念名称
            limit: 最多返回的文件数
            
        Returns:
            文件集群数据
        """
        concept_node_id = f"concept:{concept}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查找包含该概念的文件
        cursor.execute("""
            SELECT e.source_id, e.weight, n.label, n.metadata
            FROM edges e
            JOIN nodes n ON e.source_id = n.node_id
            WHERE e.target_id = ? AND e.edge_type = 'contains'
            ORDER BY e.weight DESC
            LIMIT ?
        """, (concept_node_id, limit))
        
        files = []
        for row in cursor.fetchall():
            file_id, weight, label, metadata_str = row
            
            try:
                metadata = json.loads(metadata_str)
            except:
                metadata = {}
            
            files.append({
                "file_id": file_id,
                "file_path": file_id.replace("file:", ""),
                "label": label,
                "relevance": weight,
                "metadata": metadata
            })
        
        conn.close()
        
        return {
            "concept": concept,
            "file_count": len(files),
            "files": files
        }
    
    def _create_snapshot(self):
        """创建图的快照"""
        graph_data = self.get_graph_data(max_nodes=1000)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO graph_snapshots (snapshot_data, node_count, edge_count, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            json.dumps(graph_data),
            graph_data["metadata"]["total_nodes"],
            graph_data["metadata"]["total_edges"],
            datetime.now().isoformat()
        ))
        
        # 只保留最近3个快照
        cursor.execute("""
            DELETE FROM graph_snapshots
            WHERE id NOT IN (
                SELECT id FROM graph_snapshots
                ORDER BY created_at DESC
                LIMIT 3
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        """获取图统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE node_type = 'file'")
        file_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nodes WHERE node_type = 'concept'")
        concept_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM edges WHERE edge_type = 'contains'")
        contains_edges = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM edges WHERE edge_type = 'relates_to'")
        relation_edges = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(degree) FROM (SELECT COUNT(*) as degree FROM edges GROUP BY source_id)")
        avg_degree = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_files": file_count,
            "total_concepts": concept_count,
            "file_concept_edges": contains_edges,
            "file_relation_edges": relation_edges,
            "average_degree": round(avg_degree, 2),
            "graph_density": round(relation_edges / max(file_count * (file_count - 1), 1), 4)
        }


if __name__ == "__main__":
    # 测试代码
    kg = KnowledgeGraph()
    
    print("📊 知识图谱测试")
    print("=" * 50)
    
    # 测试添加节点
    file_id = kg.add_file_node("test_doc.txt", {"size": 1024})
    concept_id = kg.add_concept_node("机器学习", {"frequency": 10})
    
    # 测试添加边
    kg.add_edge(file_id, concept_id, "contains", weight=0.8)
    
    # 获取统计信息
    stats = kg.get_statistics()
    print("\n图统计信息：")
    for key, value in stats.items():
        print(f"  • {key}: {value}")
    
    print("\n" + "=" * 50)
    print("✅ 知识图谱模块已就绪")
