#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用API客户端
支持多个AI模型提供商的统一API调用
"""

import json
import logging
import asyncio
import httpx
import time
import hashlib
import hmac
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator
from model_manager import ModelConfig, get_model_manager

class UniversalAPIClient:
    """通用API客户端"""
    
    def __init__(self):
        self.model_manager = get_model_manager()
        self.timeout = 30
        
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            model_id: Optional[str] = None,
                            stream: bool = False,
                            **kwargs) -> Dict[str, Any]:
        """统一的聊天完成接口"""
        try:
            # 获取模型配置
            if model_id:
                model = self.model_manager.get_model(model_id)
            else:
                model = self.model_manager.get_current_model()
            
            if not model:
                return {"success": False, "error": "未找到可用模型"}
            
            # 根据提供商类型调用相应的API
            provider_info = self.model_manager.providers.get(model.provider)
            if not provider_info:
                return {"success": False, "error": f"不支持的提供商: {model.provider}"}
            
            api_type = provider_info.get("api_type", "openai")
            
            if api_type == "openai":
                return await self._call_openai_api(model, messages, stream, **kwargs)
            elif api_type == "anthropic":
                return await self._call_anthropic_api(model, messages, stream, **kwargs)
            elif api_type == "google":
                return await self._call_google_api(model, messages, stream, **kwargs)
            elif api_type == "baidu":
                return await self._call_baidu_api(model, messages, stream, **kwargs)
            elif api_type == "alibaba":
                return await self._call_alibaba_api(model, messages, stream, **kwargs)
            elif api_type == "xunfei":
                return await self._call_xunfei_api(model, messages, stream, **kwargs)
            elif api_type == "zhipu":
                return await self._call_zhipu_api(model, messages, stream, **kwargs)
            else:
                return {"success": False, "error": f"不支持的API类型: {api_type}"}
                
        except Exception as e:
            logging.error(f"API调用失败: {e}")
            return {"success": False, "error": f"API调用失败: {e}"}
    
    async def _call_openai_api(self, model: ModelConfig, messages: List[Dict[str, str]], 
                              stream: bool = False, **kwargs) -> Dict[str, Any]:
        """调用OpenAI兼容的API"""
        try:
            provider_info = self.model_manager.providers[model.provider]
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                f"{provider_info['auth_header']}": f"{provider_info['auth_prefix']}{model.api_key}".strip()
            }
            
            # 添加额外头部
            if "additional_headers" in provider_info:
                headers.update(provider_info["additional_headers"])
            
            # 构建请求数据
            data = {
                "model": model.model_identifier,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", model.max_tokens),
                "temperature": kwargs.get("temperature", model.temperature),
                "stream": stream
            }
            
            # 添加其他参数
            for key in ["top_p", "frequency_penalty", "presence_penalty"]:
                if key in kwargs:
                    data[key] = kwargs[key]
            
            # 构建URL
            endpoint = provider_info["endpoints"]["chat"]
            url = f"{model.api_base_url}{endpoint}"
            
            # 发送请求
            async with httpx.AsyncClient(timeout=model.timeout) as client:
                response = await client.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 提取回复内容
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0]["message"]["content"]
                        return {
                            "success": True,
                            "content": content,
                            "model": model.model_identifier,
                            "provider": model.provider,
                            "usage": result.get("usage", {}),
                            "raw_response": result
                        }
                    else:
                        return {"success": False, "error": "API返回格式异常"}
                else:
                    error_text = response.text
                    return {"success": False, "error": f"API调用失败: HTTP {response.status_code}", "details": error_text}
                    
        except Exception as e:
            logging.error(f"OpenAI API调用失败: {e}")
            return {"success": False, "error": f"OpenAI API调用失败: {e}"}
    
    async def _call_anthropic_api(self, model: ModelConfig, messages: List[Dict[str, str]], 
                                 stream: bool = False, **kwargs) -> Dict[str, Any]:
        """调用Anthropic Claude API"""
        try:
            provider_info = self.model_manager.providers[model.provider]
            
            # 构建请求头
            headers = {
                "Content-Type": "application/json",
                "x-api-key": model.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            # 转换消息格式
            system_message = ""
            claude_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # 构建请求数据
            data = {
                "model": model.model_identifier,
                "max_tokens": kwargs.get("max_tokens", model.max_tokens),
                "messages": claude_messages
            }
            
            if system_message:
                data["system"] = system_message
            
            if "temperature" in kwargs:
                data["temperature"] = kwargs["temperature"]
            
            # 构建URL
            endpoint = provider_info["endpoints"]["chat"]
            url = f"{model.api_base_url}{endpoint}"
            
            # 发送请求
            async with httpx.AsyncClient(timeout=model.timeout) as client:
                response = await client.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 提取回复内容
                    if "content" in result and result["content"]:
                        content = result["content"][0]["text"]
                        return {
                            "success": True,
                            "content": content,
                            "model": model.model_identifier,
                            "provider": model.provider,
                            "usage": result.get("usage", {}),
                            "raw_response": result
                        }
                    else:
                        return {"success": False, "error": "API返回格式异常"}
                else:
                    error_text = response.text
                    return {"success": False, "error": f"API调用失败: HTTP {response.status_code}", "details": error_text}
                    
        except Exception as e:
            logging.error(f"Anthropic API调用失败: {e}")
            return {"success": False, "error": f"Anthropic API调用失败: {e}"}
    
    async def _call_google_api(self, model: ModelConfig, messages: List[Dict[str, str]], 
                              stream: bool = False, **kwargs) -> Dict[str, Any]:
        """调用Google Gemini API"""
        try:
            # 构建请求头
            headers = {
                "Content-Type": "application/json"
            }
            
            # 转换消息格式
            contents = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            # 构建请求数据
            data = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": kwargs.get("max_tokens", model.max_tokens),
                    "temperature": kwargs.get("temperature", model.temperature)
                }
            }
            
            # 构建URL
            endpoint = self.model_manager.providers[model.provider]["endpoints"]["chat"]
            url = f"{model.api_base_url}{endpoint.format(model=model.model_identifier)}"
            url += f"?key={model.api_key}"
            
            # 发送请求
            async with httpx.AsyncClient(timeout=model.timeout) as client:
                response = await client.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 提取回复内容
                    if "candidates" in result and result["candidates"]:
                        content = result["candidates"][0]["content"]["parts"][0]["text"]
                        return {
                            "success": True,
                            "content": content,
                            "model": model.model_identifier,
                            "provider": model.provider,
                            "usage": result.get("usageMetadata", {}),
                            "raw_response": result
                        }
                    else:
                        return {"success": False, "error": "API返回格式异常"}
                else:
                    error_text = response.text
                    return {"success": False, "error": f"API调用失败: HTTP {response.status_code}", "details": error_text}
                    
        except Exception as e:
            logging.error(f"Google API调用失败: {e}")
            return {"success": False, "error": f"Google API调用失败: {e}"}
    
    async def _call_baidu_api(self, model: ModelConfig, messages: List[Dict[str, str]], 
                             stream: bool = False, **kwargs) -> Dict[str, Any]:
        """调用百度文心一言API"""
        # 百度API需要特殊的access_token处理，这里提供基础实现
        return {"success": False, "error": "百度API需要特殊配置，请参考官方文档"}
    
    async def _call_alibaba_api(self, model: ModelConfig, messages: List[Dict[str, str]], 
                               stream: bool = False, **kwargs) -> Dict[str, Any]:
        """调用阿里通义千问API"""
        # 阿里API有特殊的格式要求，这里提供基础实现
        return {"success": False, "error": "阿里API需要特殊配置，请参考官方文档"}
    
    async def _call_xunfei_api(self, model: ModelConfig, messages: List[Dict[str, str]], 
                              stream: bool = False, **kwargs) -> Dict[str, Any]:
        """调用讯飞星火API"""
        # 讯飞API需要特殊的签名认证，这里提供基础实现
        return {"success": False, "error": "讯飞API需要特殊配置，请参考官方文档"}
    
    async def _call_zhipu_api(self, model: ModelConfig, messages: List[Dict[str, str]], 
                             stream: bool = False, **kwargs) -> Dict[str, Any]:
        """调用智谱ChatGLM API"""
        # 智谱API使用JWT认证，这里使用OpenAI兼容格式
        return await self._call_openai_api(model, messages, stream, **kwargs)

# 全局客户端实例
universal_client = UniversalAPIClient()

def get_universal_client() -> UniversalAPIClient:
    """获取通用API客户端实例"""
    return universal_client
