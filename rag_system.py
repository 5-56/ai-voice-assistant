#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG (检索增强生成) 系统
实现基于知识库的智能问答功能
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re

# 知识库集成
try:
    from knowledge_base import get_knowledge_base
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    logging.warning("知识库模块不可用，RAG功能将被禁用")

class RAGSystem:
    """RAG系统"""
    
    def __init__(self):
        self.knowledge_base = None
        self.max_context_length = 4000  # 最大上下文长度
        self.min_relevance_score = 0.1  # 最小相关性分数
        self.max_documents = 3  # 最大引用文档数
        
        if KNOWLEDGE_BASE_AVAILABLE:
            try:
                self.knowledge_base = get_knowledge_base()
                logging.info("RAG系统初始化成功")
            except Exception as e:
                logging.error(f"RAG系统初始化失败: {e}")
                self.knowledge_base = None
        else:
            logging.warning("知识库不可用，RAG功能禁用")
    
    def is_available(self) -> bool:
        """检查RAG系统是否可用"""
        return self.knowledge_base is not None
    
    def should_use_rag(self, query: str) -> bool:
        """判断是否应该使用RAG"""
        if not self.is_available():
            return False
        
        # 检查查询是否包含知识相关的关键词
        knowledge_keywords = [
            "文档", "资料", "内容", "信息", "数据", "记录", "报告", "说明",
            "什么是", "如何", "怎么", "为什么", "介绍", "解释", "定义",
            "根据", "基于", "参考", "查找", "搜索", "找到", "显示",
            "document", "file", "content", "information", "data", "what", "how", "why"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in knowledge_keywords)
    
    def retrieve_relevant_documents(self, query: str) -> List[Dict[str, Any]]:
        """检索相关文档"""
        if not self.is_available():
            return []
        
        try:
            # 搜索相关文档
            results = self.knowledge_base.search_documents(query, limit=self.max_documents)
            
            # 过滤低相关性文档
            filtered_results = [
                result for result in results 
                if result.get("relevance_score", 0) >= self.min_relevance_score
            ]
            
            logging.info(f"检索到 {len(filtered_results)} 个相关文档")
            return filtered_results
            
        except Exception as e:
            logging.error(f"文档检索失败: {e}")
            return []
    
    def build_context(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """构建上下文"""
        if not documents:
            return ""
        
        context_parts = []
        current_length = 0
        
        context_parts.append("以下是相关的文档内容：\n")
        current_length += len(context_parts[0])
        
        for i, doc in enumerate(documents, 1):
            # 构建文档引用
            doc_header = f"\n【文档{i}：{doc['file_name']}】\n"
            
            # 使用片段或完整内容
            if doc.get("snippets"):
                content = "\n".join(doc["snippets"])
            else:
                content = doc["content"]
            
            # 截断过长的内容
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            doc_content = doc_header + content + "\n"
            
            # 检查长度限制
            if current_length + len(doc_content) > self.max_context_length:
                break
            
            context_parts.append(doc_content)
            current_length += len(doc_content)
        
        context_parts.append(f"\n请基于以上文档内容回答问题：{query}")
        
        return "".join(context_parts)
    
    def enhance_query(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """增强查询（RAG核心功能）"""
        if not self.should_use_rag(query):
            return query, []
        
        # 检索相关文档
        relevant_docs = self.retrieve_relevant_documents(query)
        
        if not relevant_docs:
            return query, []
        
        # 构建增强的上下文
        enhanced_context = self.build_context(query, relevant_docs)
        
        return enhanced_context, relevant_docs
    
    def format_response_with_sources(self, response: str, sources: List[Dict[str, Any]]) -> str:
        """格式化响应，添加来源信息"""
        if not sources:
            return response
        
        # 添加来源信息
        sources_text = "\n\n📚 **参考来源：**\n"
        for i, source in enumerate(sources, 1):
            sources_text += f"{i}. **{source['file_name']}**"
            
            # 添加相关性分数
            if source.get("relevance_score"):
                score = source["relevance_score"]
                if isinstance(score, float):
                    sources_text += f" (相关性: {score:.2f})"
            
            # 添加搜索类型
            if source.get("search_type"):
                sources_text += f" [{source['search_type']}]"
            
            sources_text += "\n"
            
            # 添加关键片段
            if source.get("snippets") and len(source["snippets"]) > 0:
                snippet = source["snippets"][0]
                if len(snippet) > 100:
                    snippet = snippet[:100] + "..."
                sources_text += f"   💡 {snippet}\n"
        
        return response + sources_text
    
    def get_knowledge_base_status(self) -> Dict[str, Any]:
        """获取知识库状态"""
        if not self.is_available():
            return {
                "available": False,
                "total_documents": 0,
                "total_words": 0,
                "message": "知识库不可用"
            }
        
        try:
            stats = self.knowledge_base.get_statistics()
            return {
                "available": True,
                "total_documents": stats.get("total_documents", 0),
                "total_words": stats.get("total_words", 0),
                "total_characters": stats.get("total_characters", 0),
                "categories": stats.get("categories", {}),
                "formats": stats.get("formats", {}),
                "vector_index_available": stats.get("vector_index_available", False)
            }
        except Exception as e:
            logging.error(f"获取知识库状态失败: {e}")
            return {
                "available": False,
                "total_documents": 0,
                "total_words": 0,
                "message": f"获取状态失败: {e}"
            }
    
    def search_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库"""
        if not self.is_available():
            return []
        
        try:
            return self.knowledge_base.search_documents(query, limit)
        except Exception as e:
            logging.error(f"搜索知识库失败: {e}")
            return []
    
    def update_document_metadata(self, file_id: str, tags: List[str] = None, 
                                category: str = None) -> Dict[str, Any]:
        """更新文档元数据"""
        if not self.is_available():
            return {"success": False, "error": "知识库不可用"}
        
        try:
            results = []
            
            if tags is not None:
                result = self.knowledge_base.update_document_tags(file_id, tags)
                results.append(("tags", result))
            
            if category is not None:
                result = self.knowledge_base.update_document_category(file_id, category)
                results.append(("category", result))
            
            # 检查所有操作是否成功
            all_success = all(result["success"] for _, result in results)
            
            if all_success:
                return {"success": True, "message": "元数据更新成功"}
            else:
                errors = [result["error"] for _, result in results if not result["success"]]
                return {"success": False, "error": "; ".join(errors)}
                
        except Exception as e:
            logging.error(f"更新文档元数据失败: {e}")
            return {"success": False, "error": str(e)}

# 全局RAG系统实例
rag_system = RAGSystem()

def get_rag_system() -> RAGSystem:
    """获取RAG系统实例"""
    return rag_system

def enhance_ai_query(query: str) -> Tuple[str, List[Dict[str, Any]]]:
    """增强AI查询（便捷函数）"""
    return rag_system.enhance_query(query)

def format_ai_response_with_sources(response: str, sources: List[Dict[str, Any]]) -> str:
    """格式化AI响应，添加来源（便捷函数）"""
    return rag_system.format_response_with_sources(response, sources)
