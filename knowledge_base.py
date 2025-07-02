#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库管理模块
实现文档内容解析、索引、检索和向量化搜索功能
"""

import os
import json
import logging
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import sqlite3
import threading

# 文档解析相关导入
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# 向量化搜索相关导入
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

class DocumentParser:
    """文档内容解析器"""
    
    def __init__(self):
        self.supported_formats = {
            '.txt': self.parse_txt,
            '.md': self.parse_markdown,
            '.pdf': self.parse_pdf,
            '.docx': self.parse_docx,
            '.doc': self.parse_doc,
        }
        logging.info("文档解析器初始化完成")
    
    def parse_txt(self, file_path: str) -> str:
        """解析TXT文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            for encoding in ['gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            raise Exception("无法解析文件编码")
    
    def parse_markdown(self, file_path: str) -> str:
        """解析Markdown文件"""
        content = self.parse_txt(file_path)
        if MARKDOWN_AVAILABLE:
            # 转换为纯文本
            html = markdown.markdown(content)
            # 简单的HTML标签移除
            text = re.sub(r'<[^>]+>', '', html)
            return text
        return content
    
    def parse_pdf(self, file_path: str) -> str:
        """解析PDF文件"""
        if not PDF_AVAILABLE:
            raise Exception("PyPDF2库不可用，无法解析PDF文件")
        
        try:
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            raise Exception(f"PDF解析失败: {e}")
    
    def parse_docx(self, file_path: str) -> str:
        """解析DOCX文件"""
        if not DOCX_AVAILABLE:
            raise Exception("python-docx库不可用，无法解析DOCX文件")
        
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            raise Exception(f"DOCX解析失败: {e}")
    
    def parse_doc(self, file_path: str) -> str:
        """解析DOC文件（旧版Word格式）"""
        # DOC格式需要特殊处理，这里返回提示信息
        return "DOC格式文件需要转换为DOCX格式才能解析内容。"
    
    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """解析文档并返回结构化信息"""
        try:
            file_path = Path(file_path)
            extension = file_path.suffix.lower()
            
            if extension not in self.supported_formats:
                return {
                    "success": False,
                    "error": f"不支持的文件格式: {extension}",
                    "content": "",
                    "metadata": {}
                }
            
            # 解析内容
            content = self.supported_formats[extension](str(file_path))
            
            # 提取元数据
            metadata = {
                "file_size": file_path.stat().st_size,
                "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime),
                "word_count": len(content.split()),
                "char_count": len(content),
                "line_count": len(content.split('\n')),
                "format": extension
            }
            
            return {
                "success": True,
                "content": content,
                "metadata": metadata,
                "error": None
            }
            
        except Exception as e:
            logging.error(f"文档解析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "metadata": {}
            }

class KnowledgeBase:
    """知识库管理器"""
    
    def __init__(self, db_path: str = "knowledge_base.db"):
        self.db_path = db_path
        self.parser = DocumentParser()
        self.vectorizer = None
        self.document_vectors = None
        self.documents = []
        self.lock = threading.Lock()
        
        # 初始化数据库
        self.init_database()
        
        # 加载现有文档
        self.load_documents()
        
        logging.info("知识库管理器初始化完成")
    
    def init_database(self):
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建文档表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata TEXT NOT NULL,
                        tags TEXT DEFAULT '',
                        category TEXT DEFAULT '',
                        created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_file_id ON documents(file_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_tags ON documents(tags)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_category ON documents(category)
                ''')
                
                conn.commit()
                logging.info("知识库数据库初始化完成")
                
        except Exception as e:
            logging.error(f"数据库初始化失败: {e}")
    
    def add_document(self, file_id: str, file_name: str, file_path: str, 
                    tags: List[str] = None, category: str = "") -> Dict[str, Any]:
        """添加文档到知识库"""
        try:
            with self.lock:
                # 解析文档内容
                parse_result = self.parser.parse_document(file_path)
                
                if not parse_result["success"]:
                    return {
                        "success": False,
                        "error": f"文档解析失败: {parse_result['error']}"
                    }
                
                content = parse_result["content"]
                metadata = parse_result["metadata"]
                
                # 存储到数据库
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO documents 
                        (file_id, file_name, file_path, content, metadata, tags, category, updated_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        file_id,
                        file_name,
                        file_path,
                        content,
                        json.dumps(metadata, default=str),
                        ','.join(tags) if tags else '',
                        category
                    ))
                    
                    conn.commit()
                
                # 重新构建向量索引
                self.rebuild_vector_index()
                
                logging.info(f"文档已添加到知识库: {file_name}")
                
                return {
                    "success": True,
                    "message": "文档已成功添加到知识库",
                    "word_count": metadata.get("word_count", 0),
                    "char_count": metadata.get("char_count", 0)
                }
                
        except Exception as e:
            logging.error(f"添加文档到知识库失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def remove_document(self, file_id: str) -> Dict[str, Any]:
        """从知识库移除文档"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('DELETE FROM documents WHERE file_id = ?', (file_id,))
                    
                    if cursor.rowcount > 0:
                        conn.commit()
                        self.rebuild_vector_index()
                        logging.info(f"文档已从知识库移除: {file_id}")
                        return {"success": True, "message": "文档已从知识库移除"}
                    else:
                        return {"success": False, "error": "文档不存在"}
                        
        except Exception as e:
            logging.error(f"移除文档失败: {e}")
            return {"success": False, "error": str(e)}
    
    def load_documents(self):
        """加载所有文档"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM documents ORDER BY created_time DESC')
                
                self.documents = []
                for row in cursor.fetchall():
                    doc = {
                        "id": row[0],
                        "file_id": row[1],
                        "file_name": row[2],
                        "file_path": row[3],
                        "content": row[4],
                        "metadata": json.loads(row[5]),
                        "tags": row[6].split(',') if row[6] else [],
                        "category": row[7],
                        "created_time": row[8],
                        "updated_time": row[9]
                    }
                    self.documents.append(doc)
                
                logging.info(f"已加载 {len(self.documents)} 个文档")
                
        except Exception as e:
            logging.error(f"加载文档失败: {e}")
            self.documents = []
    
    def rebuild_vector_index(self):
        """重建向量索引"""
        if not VECTOR_SEARCH_AVAILABLE:
            logging.warning("向量搜索功能不可用，跳过索引构建")
            return
        
        try:
            if not self.documents:
                self.load_documents()
            
            if not self.documents:
                return
            
            # 提取文档内容
            texts = [doc["content"] for doc in self.documents]
            
            # 构建TF-IDF向量
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words=None,  # 保留中文支持
                ngram_range=(1, 2)
            )
            
            self.document_vectors = self.vectorizer.fit_transform(texts)
            
            logging.info(f"向量索引构建完成，包含 {len(texts)} 个文档")
            
        except Exception as e:
            logging.error(f"构建向量索引失败: {e}")

    def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索文档"""
        try:
            results = []

            # 1. 关键词搜索
            keyword_results = self.keyword_search(query, limit)
            results.extend(keyword_results)

            # 2. 向量搜索（如果可用）
            if VECTOR_SEARCH_AVAILABLE and self.vectorizer and self.document_vectors is not None:
                vector_results = self.vector_search(query, limit)
                results.extend(vector_results)

            # 去重并按相关性排序
            seen_ids = set()
            unique_results = []
            for result in results:
                if result["file_id"] not in seen_ids:
                    seen_ids.add(result["file_id"])
                    unique_results.append(result)

            # 按相关性分数排序
            unique_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

            return unique_results[:limit]

        except Exception as e:
            logging.error(f"搜索文档失败: {e}")
            return []

    def keyword_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """关键词搜索"""
        try:
            query_lower = query.lower()
            results = []

            for doc in self.documents:
                content_lower = doc["content"].lower()
                title_lower = doc["file_name"].lower()

                # 计算匹配分数
                content_matches = content_lower.count(query_lower)
                title_matches = title_lower.count(query_lower) * 3  # 标题匹配权重更高

                if content_matches > 0 or title_matches > 0:
                    # 提取相关片段
                    snippets = self.extract_snippets(doc["content"], query, max_snippets=3)

                    results.append({
                        "file_id": doc["file_id"],
                        "file_name": doc["file_name"],
                        "content": doc["content"],
                        "snippets": snippets,
                        "relevance_score": content_matches + title_matches,
                        "metadata": doc["metadata"],
                        "tags": doc["tags"],
                        "category": doc["category"],
                        "search_type": "keyword"
                    })

            return results

        except Exception as e:
            logging.error(f"关键词搜索失败: {e}")
            return []

    def vector_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """向量搜索"""
        try:
            if not self.vectorizer or self.document_vectors is None:
                return []

            # 将查询转换为向量
            query_vector = self.vectorizer.transform([query])

            # 计算相似度
            similarities = cosine_similarity(query_vector, self.document_vectors).flatten()

            # 获取最相似的文档
            top_indices = similarities.argsort()[-limit:][::-1]

            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # 相似度阈值
                    doc = self.documents[idx]
                    snippets = self.extract_snippets(doc["content"], query, max_snippets=2)

                    results.append({
                        "file_id": doc["file_id"],
                        "file_name": doc["file_name"],
                        "content": doc["content"],
                        "snippets": snippets,
                        "relevance_score": float(similarities[idx]),
                        "metadata": doc["metadata"],
                        "tags": doc["tags"],
                        "category": doc["category"],
                        "search_type": "vector"
                    })

            return results

        except Exception as e:
            logging.error(f"向量搜索失败: {e}")
            return []

    def extract_snippets(self, content: str, query: str, max_snippets: int = 3,
                        snippet_length: int = 200) -> List[str]:
        """提取相关文本片段"""
        try:
            query_lower = query.lower()
            content_lower = content.lower()
            snippets = []

            # 找到所有匹配位置
            positions = []
            start = 0
            while True:
                pos = content_lower.find(query_lower, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1

            # 为每个匹配位置提取片段
            for pos in positions[:max_snippets]:
                start = max(0, pos - snippet_length // 2)
                end = min(len(content), pos + len(query) + snippet_length // 2)

                snippet = content[start:end].strip()

                # 高亮查询词
                snippet = re.sub(
                    re.escape(query),
                    f"**{query}**",
                    snippet,
                    flags=re.IGNORECASE
                )

                if snippet not in snippets:
                    snippets.append(snippet)

            return snippets

        except Exception as e:
            logging.error(f"提取片段失败: {e}")
            return []

    def get_document_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文档"""
        for doc in self.documents:
            if doc["file_id"] == file_id:
                return doc
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            total_docs = len(self.documents)
            total_words = sum(doc["metadata"].get("word_count", 0) for doc in self.documents)
            total_chars = sum(doc["metadata"].get("char_count", 0) for doc in self.documents)

            # 按类别统计
            categories = {}
            for doc in self.documents:
                category = doc["category"] or "未分类"
                categories[category] = categories.get(category, 0) + 1

            # 按格式统计
            formats = {}
            for doc in self.documents:
                format_type = doc["metadata"].get("format", "unknown")
                formats[format_type] = formats.get(format_type, 0) + 1

            return {
                "total_documents": total_docs,
                "total_words": total_words,
                "total_characters": total_chars,
                "categories": categories,
                "formats": formats,
                "vector_index_available": VECTOR_SEARCH_AVAILABLE and self.vectorizer is not None
            }

        except Exception as e:
            logging.error(f"获取统计信息失败: {e}")
            return {
                "total_documents": 0,
                "total_words": 0,
                "total_characters": 0,
                "categories": {},
                "formats": {},
                "vector_index_available": False
            }

    def update_document_tags(self, file_id: str, tags: List[str]) -> Dict[str, Any]:
        """更新文档标签"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE documents
                    SET tags = ?, updated_time = CURRENT_TIMESTAMP
                    WHERE file_id = ?
                ''', (','.join(tags), file_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    self.load_documents()  # 重新加载
                    return {"success": True, "message": "标签已更新"}
                else:
                    return {"success": False, "error": "文档不存在"}

        except Exception as e:
            logging.error(f"更新标签失败: {e}")
            return {"success": False, "error": str(e)}

    def update_document_category(self, file_id: str, category: str) -> Dict[str, Any]:
        """更新文档分类"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE documents
                    SET category = ?, updated_time = CURRENT_TIMESTAMP
                    WHERE file_id = ?
                ''', (category, file_id))

                if cursor.rowcount > 0:
                    conn.commit()
                    self.load_documents()  # 重新加载
                    return {"success": True, "message": "分类已更新"}
                else:
                    return {"success": False, "error": "文档不存在"}

        except Exception as e:
            logging.error(f"更新分类失败: {e}")
            return {"success": False, "error": str(e)}

# 全局知识库实例
knowledge_base = KnowledgeBase()

def get_knowledge_base() -> KnowledgeBase:
    """获取知识库实例"""
    return knowledge_base
