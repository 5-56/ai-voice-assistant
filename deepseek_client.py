#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI客户端模块
实现与多个AI模型提供商的对话功能
支持DeepSeek、OpenAI、Claude、Gemini等多种模型
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, AsyncGenerator, Callable
from openai import OpenAI
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from config_manager import get_config

# 模型管理集成
try:
    from model_manager import get_model_manager
    from universal_api_client import get_universal_client
    MODEL_MANAGER_AVAILABLE = True
except ImportError:
    MODEL_MANAGER_AVAILABLE = False
    logging.warning("模型管理系统不可用，将使用传统DeepSeek客户端")

# RAG系统集成
try:
    from rag_system import get_rag_system, enhance_ai_query, format_ai_response_with_sources
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG系统不可用")

# 天气查询集成
try:
    from weather_query_handler import get_weather_query_handler, is_weather_query, handle_weather_query
    WEATHER_AVAILABLE = True
except ImportError:
    WEATHER_AVAILABLE = False
    logging.warning("天气查询功能不可用")

# IP查询集成
try:
    from ip_query_handler import get_ip_query_handler, is_ip_query, handle_ip_query
    IP_QUERY_AVAILABLE = True
except ImportError:
    IP_QUERY_AVAILABLE = False
    logging.warning("IP查询功能不可用")

class DeepSeekClient:
    """AI客户端（支持多模型提供商）"""

    def __init__(self):
        self.config = get_config()
        self.client: Optional[OpenAI] = None
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # 请求间隔（秒）

        # 初始化模型管理器和通用客户端
        if MODEL_MANAGER_AVAILABLE:
            self.model_manager = get_model_manager()
            self.universal_client = get_universal_client()
            self.use_universal_client = True
            logging.info("使用通用API客户端，支持多模型提供商")
        else:
            self.use_universal_client = False
            logging.info("使用传统DeepSeek客户端")

        self._initialize_client()
    
    def _initialize_client(self) -> bool:
        """初始化OpenAI客户端"""
        try:
            api_config = self.config.get_api_config()
            api_key = api_config.get("deepseek_api_key", "")
            base_url = api_config.get("base_url", "https://api.deepseek.com")
            
            if not api_key:
                logging.warning("DeepSeek API密钥未配置")
                return False
            
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=api_config.get("timeout", 30)
            )
            
            logging.info("DeepSeek客户端初始化成功")
            return True
            
        except Exception as e:
            logging.error(f"DeepSeek客户端初始化失败: {e}")
            self.client = None
            return False
    
    def is_configured(self) -> bool:
        """检查是否已正确配置"""
        return self.client is not None and self.config.is_api_configured()
    
    def _rate_limit(self):
        """实现简单的速率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _make_request(self, messages: list, stream: bool = False, **kwargs) -> Any:
        """发送API请求（带重试机制）"""
        if not self.is_configured():
            raise ValueError("DeepSeek客户端未正确配置")
        
        self._rate_limit()
        
        api_config = self.config.get_api_config()
        
        request_params = {
            "model": api_config.get("model", "deepseek-chat"),
            "messages": messages,
            "stream": stream,
            "max_tokens": api_config.get("max_tokens", 2000),
            "temperature": api_config.get("temperature", 0.7),
            **kwargs
        }
        
        logging.info(f"发送DeepSeek请求: {len(messages)} 条消息, stream={stream}")
        
        try:
            response = self.client.chat.completions.create(**request_params)
            logging.info("DeepSeek请求成功")
            return response
            
        except Exception as e:
            logging.error(f"DeepSeek请求失败: {e}")
            raise
    
    def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """同步聊天完成（支持RAG和天气查询）"""
        try:
            # 获取最后一条用户消息
            user_query = ""
            if len(messages) > 0:
                last_message = messages[-1]
                if last_message.get("role") == "user":
                    user_query = last_message.get("content", "")

            # IP查询处理
            if IP_QUERY_AVAILABLE and user_query and is_ip_query(user_query):
                logging.info(f"检测到IP查询: {user_query}")
                ip_result = handle_ip_query(user_query)

                if ip_result["success"]:
                    return {
                        "success": True,
                        "content": ip_result["response"],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        "model": "ip-service",
                        "created": int(time.time()),
                        "ip_data": ip_result.get("ip_data"),
                        "location_info": ip_result.get("location_info"),
                        "weather_data": ip_result.get("weather_data"),
                        "query_info": ip_result.get("query_type"),
                        "rag_sources": []
                    }
                else:
                    # IP查询失败，继续使用AI回答
                    logging.warning(f"IP查询失败: {ip_result.get('error')}")

            # 天气查询处理
            if WEATHER_AVAILABLE and user_query and is_weather_query(user_query):
                logging.info(f"检测到天气查询: {user_query}")
                weather_result = handle_weather_query(user_query)

                if weather_result["success"]:
                    return {
                        "success": True,
                        "content": weather_result["response"],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        "model": "weather-service",
                        "created": int(time.time()),
                        "weather_data": weather_result.get("weather_data"),
                        "query_info": weather_result.get("query_info"),
                        "rag_sources": []
                    }
                else:
                    # 天气查询失败，继续使用AI回答
                    logging.warning(f"天气查询失败: {weather_result.get('error')}")

            # RAG增强处理
            enhanced_messages = messages.copy()
            rag_sources = []

            if RAG_AVAILABLE and user_query:
                # 使用RAG增强查询
                enhanced_query, sources = enhance_ai_query(user_query)

                if sources:
                    # 替换最后一条消息为增强后的查询
                    enhanced_messages[-1] = {
                        "role": "user",
                        "content": enhanced_query
                    }
                    rag_sources = sources
                    logging.info(f"RAG增强: 找到 {len(sources)} 个相关文档")

            # 使用通用客户端或传统客户端
            if self.use_universal_client:
                # 使用通用API客户端（支持多模型）
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    api_result = loop.run_until_complete(
                        self.universal_client.chat_completion(enhanced_messages, **kwargs)
                    )
                finally:
                    loop.close()

                if not api_result["success"]:
                    return {
                        "success": False,
                        "error": api_result["error"],
                        "rag_sources": rag_sources
                    }

                ai_content = api_result["content"]
                model_name = api_result.get("model", "unknown")
                usage = api_result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

            else:
                # 使用传统DeepSeek客户端
                response = self._make_request(enhanced_messages, stream=False, **kwargs)
                ai_content = response.choices[0].message.content
                model_name = response.model
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }

            # 如果使用了RAG，添加来源信息
            if rag_sources:
                ai_content = format_ai_response_with_sources(ai_content, rag_sources)

            result = {
                "success": True,
                "content": ai_content,
                "usage": usage,
                "model": model_name,
                "created": int(time.time()),
                "rag_sources": rag_sources  # 添加RAG来源信息
            }

            logging.info(f"聊天完成成功: {usage['total_tokens']} tokens, RAG来源: {len(rag_sources)}")
            return result

        except Exception as e:
            logging.error(f"聊天完成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None,
                "usage": None,
                "rag_sources": []
            }
    
    async def chat_completion_async(self, messages: list, **kwargs) -> Dict[str, Any]:
        """异步聊天完成"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.chat_completion, messages, **kwargs)
    
    def chat_completion_stream(self, messages: list, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天完成"""
        try:
            response = self._make_request(messages, stream=True, **kwargs)
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield {
                        "success": True,
                        "content": chunk.choices[0].delta.content,
                        "finished": False
                    }
            
            # 发送完成信号
            yield {
                "success": True,
                "content": "",
                "finished": True
            }
            
        except Exception as e:
            logging.error(f"流式聊天失败: {e}")
            yield {
                "success": False,
                "error": str(e),
                "content": None,
                "finished": True
            }
    
    async def chat_completion_stream_async(self, 
                                         messages: list, 
                                         callback: Callable[[Dict[str, Any]], None] = None,
                                         **kwargs) -> Dict[str, Any]:
        """异步流式聊天完成"""
        try:
            full_content = ""
            total_chunks = 0
            
            def stream_generator():
                return self.chat_completion_stream(messages, **kwargs)
            
            # 在线程池中运行流式生成器
            loop = asyncio.get_event_loop()
            
            async def process_stream():
                nonlocal full_content, total_chunks
                
                for chunk in await loop.run_in_executor(None, lambda: list(stream_generator())):
                    if chunk["success"]:
                        if chunk["content"]:
                            full_content += chunk["content"]
                            total_chunks += 1
                        
                        if callback:
                            callback(chunk)
                        
                        if chunk["finished"]:
                            break
                    else:
                        if callback:
                            callback(chunk)
                        raise Exception(chunk.get("error", "流式处理失败"))
            
            await process_stream()
            
            return {
                "success": True,
                "content": full_content,
                "chunks": total_chunks,
                "usage": None  # 流式模式下通常不返回usage信息
            }
            
        except Exception as e:
            logging.error(f"异步流式聊天失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None,
                "chunks": 0
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        try:
            if not self.is_configured():
                return {
                    "success": False,
                    "error": "API未配置",
                    "details": "请检查API密钥和基础URL配置"
                }
            
            test_messages = [
                {"role": "user", "content": "Hello, this is a connection test."}
            ]
            
            start_time = time.time()
            result = self.chat_completion(test_messages)
            end_time = time.time()
            
            if result["success"]:
                return {
                    "success": True,
                    "response_time": round(end_time - start_time, 2),
                    "model": result.get("model", "unknown"),
                    "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                    "content_preview": result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "response_time": round(end_time - start_time, 2)
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": "连接测试过程中发生异常"
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        api_config = self.config.get_api_config()
        
        return {
            "model": api_config.get("model", "deepseek-chat"),
            "base_url": api_config.get("base_url", "https://api.deepseek.com"),
            "max_tokens": api_config.get("max_tokens", 2000),
            "temperature": api_config.get("temperature", 0.7),
            "timeout": api_config.get("timeout", 30),
            "configured": self.is_configured()
        }
    
    def update_config(self) -> bool:
        """更新配置（重新初始化客户端）"""
        return self._initialize_client()

# 全局DeepSeek客户端实例
deepseek_client = DeepSeekClient()

def get_deepseek_client() -> DeepSeekClient:
    """获取DeepSeek客户端实例"""
    return deepseek_client
