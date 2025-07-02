#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
管理智能语音助手的所有配置信息
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = {}
        self.default_config = self._get_default_config()
        self.load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "api": {
                "deepseek_api_key": "",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "max_tokens": 2000,
                "temperature": 0.7,
                "timeout": 30
            },
            "tts": {
                "engine": "edge",
                "voice": {
                    "chinese": "zh-CN-XiaoxiaoNeural",
                    "english": "en-US-JennyNeural"
                },
                "rate": 5,
                "volume": 80,
                "auto_read": True
            },
            "ui": {
                "theme": "light",
                "font_size": 12,
                "window_size": {
                    "width": 1000,
                    "height": 700
                },
                "auto_scroll": True
            },
            "conversation": {
                "max_history": 50,
                "save_history": True,
                "system_prompt": "你是一个智能语音助手，请用简洁、友好的语言回答用户的问题。如果用户使用中文提问，请用中文回答；如果使用英文提问，请用英文回答。",
                "stream_mode": False
            },
            "audio": {
                "playback_method": "auto",
                "concurrent_limit": 1
            }
        }
    
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                # 合并默认配置（处理新增配置项）
                self.config = self._merge_config(self.default_config, self.config)
                
                logging.info(f"配置文件加载成功: {self.config_file}")
                return True
            else:
                # 创建默认配置文件
                self.config = self.default_config.copy()
                self.save_config()
                logging.info(f"创建默认配置文件: {self.config_file}")
                return True
                
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            self.config = self.default_config.copy()
            return False
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logging.info(f"配置文件保存成功: {self.config_file}")
            return True
            
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")
            return False
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """合并配置（递归）"""
        result = default.copy()
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值（支持点分隔路径）"""
        try:
            keys = key_path.split('.')
            value = self.config
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """设置配置值（支持点分隔路径）"""
        try:
            keys = key_path.split('.')
            config = self.config
            
            # 导航到最后一级
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 设置值
            config[keys[-1]] = value
            return True
            
        except Exception as e:
            logging.error(f"设置配置值失败: {key_path} = {value}, 错误: {e}")
            return False
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self.get("api", {})
    
    def get_tts_config(self) -> Dict[str, Any]:
        """获取TTS配置"""
        return self.get("tts", {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置"""
        return self.get("ui", {})
    
    def get_conversation_config(self) -> Dict[str, Any]:
        """获取对话配置"""
        return self.get("conversation", {})
    
    def get_audio_config(self) -> Dict[str, Any]:
        """获取音频配置"""
        return self.get("audio", {})
    
    def is_api_configured(self) -> bool:
        """检查API是否已配置"""
        api_key = self.get("api.deepseek_api_key", "")
        return bool(api_key and api_key.strip())
    
    def validate_config(self) -> Dict[str, list]:
        """验证配置"""
        errors = {
            "api": [],
            "tts": [],
            "ui": [],
            "conversation": [],
            "audio": []
        }
        
        # 验证API配置
        if not self.is_api_configured():
            errors["api"].append("DeepSeek API密钥未配置")
        
        base_url = self.get("api.base_url", "")
        if not base_url or not base_url.startswith("http"):
            errors["api"].append("API基础URL无效")
        
        # 验证TTS配置
        engine = self.get("tts.engine", "")
        if engine not in ["edge", "windows"]:
            errors["tts"].append("TTS引擎配置无效")
        
        rate = self.get("tts.rate", 5)
        if not isinstance(rate, int) or rate < 0 or rate > 10:
            errors["tts"].append("语速配置无效（应为0-10）")
        
        volume = self.get("tts.volume", 80)
        if not isinstance(volume, int) or volume < 0 or volume > 100:
            errors["tts"].append("音量配置无效（应为0-100）")
        
        # 验证UI配置
        font_size = self.get("ui.font_size", 12)
        if not isinstance(font_size, int) or font_size < 8 or font_size > 24:
            errors["ui"].append("字体大小无效（应为8-24）")
        
        # 验证对话配置
        max_history = self.get("conversation.max_history", 50)
        if not isinstance(max_history, int) or max_history < 1 or max_history > 1000:
            errors["conversation"].append("历史记录数量无效（应为1-1000）")
        
        # 移除空的错误列表
        return {k: v for k, v in errors.items() if v}
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            # 保留API密钥
            api_key = self.get("api.deepseek_api_key", "")
            
            self.config = self.default_config.copy()
            
            # 恢复API密钥
            if api_key:
                self.set("api.deepseek_api_key", api_key)
            
            return self.save_config()
            
        except Exception as e:
            logging.error(f"重置配置失败: {e}")
            return False
    
    def export_config(self, export_file: str) -> bool:
        """导出配置"""
        try:
            export_path = Path(export_file)
            
            # 创建导出配置（移除敏感信息）
            export_config = self.config.copy()
            if "api" in export_config and "deepseek_api_key" in export_config["api"]:
                export_config["api"]["deepseek_api_key"] = "***HIDDEN***"
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_config, f, indent=2, ensure_ascii=False)
            
            logging.info(f"配置导出成功: {export_path}")
            return True
            
        except Exception as e:
            logging.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, import_file: str) -> bool:
        """导入配置"""
        try:
            import_path = Path(import_file)
            
            if not import_path.exists():
                logging.error(f"导入文件不存在: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 保留当前API密钥
            current_api_key = self.get("api.deepseek_api_key", "")
            
            # 合并配置
            self.config = self._merge_config(self.default_config, imported_config)
            
            # 恢复API密钥（如果导入的配置中是隐藏的）
            if (self.get("api.deepseek_api_key", "") == "***HIDDEN***" and 
                current_api_key):
                self.set("api.deepseek_api_key", current_api_key)
            
            return self.save_config()
            
        except Exception as e:
            logging.error(f"导入配置失败: {e}")
            return False

# 全局配置管理器实例
config_manager = ConfigManager()

def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    return config_manager
