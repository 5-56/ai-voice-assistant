#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型管理系统
支持多个AI模型的配置、管理和切换
"""

import json
import logging
import asyncio
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid

@dataclass
class ModelConfig:
    """模型配置数据类"""
    id: str
    display_name: str
    api_base_url: str
    api_key: str
    model_identifier: str
    provider: str
    description: str = ""
    max_tokens: int = 4000
    temperature: float = 0.7
    timeout: int = 30
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.config_file = Path("models_config.json")
        self.models: Dict[str, ModelConfig] = {}
        self.current_model_id: Optional[str] = None
        
        # 预定义的模型提供商
        self.providers = {
            "openai": {
                "name": "OpenAI",
                "default_base_url": "https://api.openai.com/v1",
                "common_models": ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "openai",
                "endpoints": {
                    "chat": "/chat/completions",
                    "models": "/models"
                }
            },
            "deepseek": {
                "name": "DeepSeek",
                "default_base_url": "https://api.deepseek.com/v1",
                "common_models": ["deepseek-chat", "deepseek-coder"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "openai",
                "endpoints": {
                    "chat": "/chat/completions",
                    "models": "/models"
                }
            },
            "anthropic": {
                "name": "Anthropic Claude",
                "default_base_url": "https://api.anthropic.com/v1",
                "common_models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                "auth_header": "x-api-key",
                "auth_prefix": "",
                "api_type": "anthropic",
                "endpoints": {
                    "chat": "/messages",
                    "complete": "/complete"
                },
                "additional_headers": {
                    "anthropic-version": "2023-06-01"
                }
            },
            "google": {
                "name": "Google Gemini",
                "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
                "common_models": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro", "gemini-pro-vision"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "google",
                "endpoints": {
                    "chat": "/models/{model}:generateContent",
                    "stream": "/models/{model}:generateContentStream"
                }
            },
            "baidu": {
                "name": "百度文心一言",
                "default_base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
                "common_models": ["ernie-4.0-8k", "ernie-3.5-8k", "ernie-turbo-8k", "ernie-speed-8k"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "baidu",
                "endpoints": {
                    "chat": "/completions"
                },
                "requires_access_token": True
            },
            "alibaba": {
                "name": "阿里通义千问",
                "default_base_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation",
                "common_models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "alibaba",
                "endpoints": {
                    "chat": "/generation"
                }
            },
            "xunfei": {
                "name": "讯飞星火",
                "default_base_url": "https://spark-api.xf-yun.com/v1.1",
                "common_models": ["spark-3.5", "spark-3.0", "spark-2.0", "spark-1.5"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "xunfei",
                "endpoints": {
                    "chat": "/chat"
                },
                "requires_signature": True
            },
            "zhipu": {
                "name": "智谱ChatGLM",
                "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
                "common_models": ["glm-4", "glm-4v", "glm-3-turbo"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "zhipu",
                "endpoints": {
                    "chat": "/chat/completions"
                }
            },
            "baichuan": {
                "name": "百川智能",
                "default_base_url": "https://api.baichuan-ai.com/v1",
                "common_models": ["baichuan2-turbo", "baichuan2-turbo-192k"],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "openai",
                "endpoints": {
                    "chat": "/chat/completions"
                }
            },
            "custom": {
                "name": "自定义",
                "default_base_url": "",
                "common_models": [],
                "auth_header": "Authorization",
                "auth_prefix": "Bearer ",
                "api_type": "openai",
                "endpoints": {
                    "chat": "/chat/completions"
                }
            }
        }
        
        # 初始化
        self._load_models()
        
        logging.info("模型管理器初始化成功")
    
    def _load_models(self):
        """加载模型配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载模型配置
                for model_data in data.get("models", []):
                    model = ModelConfig(**model_data)
                    self.models[model.id] = model
                
                # 设置当前模型
                self.current_model_id = data.get("current_model_id")
                
                # 如果没有当前模型，设置第一个可用模型
                if not self.current_model_id and self.models:
                    self.current_model_id = next(iter(self.models.keys()))
            
            else:
                # 创建默认配置
                self._create_default_models()
                
        except Exception as e:
            logging.error(f"加载模型配置失败: {e}")
            self._create_default_models()
    
    def _create_default_models(self):
        """创建默认模型配置"""
        try:
            # 添加DeepSeek默认配置
            deepseek_model = ModelConfig(
                id=str(uuid.uuid4()),
                display_name="DeepSeek Chat",
                api_base_url="https://api.deepseek.com/v1",
                api_key="",
                model_identifier="deepseek-chat",
                provider="deepseek",
                description="DeepSeek官方聊天模型",
                max_tokens=4000,
                temperature=0.7
            )
            
            self.models[deepseek_model.id] = deepseek_model
            self.current_model_id = deepseek_model.id
            
            self._save_models()
            
        except Exception as e:
            logging.error(f"创建默认模型配置失败: {e}")
    
    def _save_models(self):
        """保存模型配置"""
        try:
            data = {
                "current_model_id": self.current_model_id,
                "models": [asdict(model) for model in self.models.values()],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"保存模型配置失败: {e}")
    
    def add_model(self, 
                  display_name: str,
                  api_base_url: str,
                  api_key: str,
                  model_identifier: str,
                  provider: str,
                  description: str = "",
                  **kwargs) -> Dict[str, Any]:
        """添加新模型"""
        try:
            # 验证必填字段
            if not all([display_name, api_base_url, api_key, model_identifier, provider]):
                return {"success": False, "error": "请填写所有必填字段"}
            
            # 检查显示名称是否重复
            for model in self.models.values():
                if model.display_name == display_name:
                    return {"success": False, "error": "模型显示名称已存在"}
            
            # 创建新模型配置
            model_id = str(uuid.uuid4())
            model = ModelConfig(
                id=model_id,
                display_name=display_name,
                api_base_url=api_base_url.rstrip('/'),
                api_key=api_key,
                model_identifier=model_identifier,
                provider=provider,
                description=description,
                **kwargs
            )
            
            self.models[model_id] = model
            
            # 如果是第一个模型，设为当前模型
            if not self.current_model_id:
                self.current_model_id = model_id
            
            self._save_models()
            
            logging.info(f"添加模型成功: {display_name}")
            
            return {
                "success": True,
                "model_id": model_id,
                "message": f"模型 '{display_name}' 添加成功"
            }
            
        except Exception as e:
            logging.error(f"添加模型失败: {e}")
            return {"success": False, "error": f"添加失败: {e}"}
    
    def update_model(self, model_id: str, **kwargs) -> Dict[str, Any]:
        """更新模型配置"""
        try:
            if model_id not in self.models:
                return {"success": False, "error": "模型不存在"}
            
            model = self.models[model_id]
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            
            model.updated_at = datetime.now().isoformat()
            
            self._save_models()
            
            logging.info(f"更新模型成功: {model.display_name}")
            
            return {
                "success": True,
                "message": f"模型 '{model.display_name}' 更新成功"
            }
            
        except Exception as e:
            logging.error(f"更新模型失败: {e}")
            return {"success": False, "error": f"更新失败: {e}"}
    
    def delete_model(self, model_id: str) -> Dict[str, Any]:
        """删除模型"""
        try:
            if model_id not in self.models:
                return {"success": False, "error": "模型不存在"}
            
            model = self.models[model_id]
            display_name = model.display_name
            
            # 删除模型
            del self.models[model_id]
            
            # 如果删除的是当前模型，切换到其他模型
            if self.current_model_id == model_id:
                if self.models:
                    self.current_model_id = next(iter(self.models.keys()))
                else:
                    self.current_model_id = None
            
            self._save_models()
            
            logging.info(f"删除模型成功: {display_name}")
            
            return {
                "success": True,
                "message": f"模型 '{display_name}' 删除成功"
            }
            
        except Exception as e:
            logging.error(f"删除模型失败: {e}")
            return {"success": False, "error": f"删除失败: {e}"}
    
    def set_current_model(self, model_id: str) -> Dict[str, Any]:
        """设置当前使用的模型"""
        try:
            if model_id not in self.models:
                return {"success": False, "error": "模型不存在"}
            
            old_model_name = ""
            if self.current_model_id and self.current_model_id in self.models:
                old_model_name = self.models[self.current_model_id].display_name
            
            self.current_model_id = model_id
            new_model_name = self.models[model_id].display_name
            
            self._save_models()
            
            logging.info(f"切换模型: {old_model_name} -> {new_model_name}")
            
            return {
                "success": True,
                "message": f"已切换到模型: {new_model_name}"
            }
            
        except Exception as e:
            logging.error(f"设置当前模型失败: {e}")
            return {"success": False, "error": f"设置失败: {e}"}
    
    def get_current_model(self) -> Optional[ModelConfig]:
        """获取当前模型配置"""
        if self.current_model_id and self.current_model_id in self.models:
            return self.models[self.current_model_id]
        return None
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """获取指定模型配置"""
        return self.models.get(model_id)
    
    def get_all_models(self) -> List[ModelConfig]:
        """获取所有模型配置"""
        return list(self.models.values())
    
    def get_models_by_provider(self, provider: str) -> List[ModelConfig]:
        """根据提供商获取模型列表"""
        return [model for model in self.models.values() if model.provider == provider]
    
    async def test_model_connection(self, model_id: str) -> Dict[str, Any]:
        """测试模型连接"""
        try:
            model = self.get_model(model_id)
            if not model:
                return {"success": False, "error": "模型不存在"}
            
            # 构建测试请求
            headers = {
                "Content-Type": "application/json"
            }
            
            # 根据提供商设置认证头
            provider_info = self.providers.get(model.provider, self.providers["custom"])
            auth_header = provider_info["auth_header"]
            auth_prefix = provider_info["auth_prefix"]
            headers[auth_header] = f"{auth_prefix}{model.api_key}".strip()
            
            # 构建测试消息
            test_data = {
                "model": model.model_identifier,
                "messages": [
                    {"role": "user", "content": "Hello, this is a connection test."}
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            # 发送测试请求
            async with httpx.AsyncClient(timeout=model.timeout) as client:
                response = await client.post(
                    f"{model.api_base_url}/chat/completions",
                    headers=headers,
                    json=test_data
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "连接测试成功",
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"连接失败: HTTP {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logging.error(f"测试模型连接失败: {e}")
            return {"success": False, "error": f"连接测试失败: {e}"}
    
    def get_providers(self) -> Dict[str, Dict[str, Any]]:
        """获取支持的提供商列表"""
        return self.providers
    
    def get_status(self) -> Dict[str, Any]:
        """获取模型管理器状态"""
        current_model = self.get_current_model()
        
        return {
            "total_models": len(self.models),
            "current_model": {
                "id": current_model.id if current_model else None,
                "display_name": current_model.display_name if current_model else None,
                "provider": current_model.provider if current_model else None
            } if current_model else None,
            "providers": list(self.providers.keys()),
            "config_file": str(self.config_file)
        }

# 全局模型管理器实例
model_manager = ModelManager()

def get_model_manager() -> ModelManager:
    """获取模型管理器实例"""
    return model_manager
