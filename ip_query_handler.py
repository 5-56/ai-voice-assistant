#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP查询处理模块
智能识别用户的IP查询意图并调用相应的IP服务
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List

# IP服务导入
try:
    from ip_location_service import get_ip_location_service
    IP_SERVICE_AVAILABLE = True
except ImportError:
    IP_SERVICE_AVAILABLE = False
    logging.warning("IP查询服务不可用")

# 天气服务导入（用于基于IP的天气查询）
try:
    from weather_service import get_weather_service
    WEATHER_SERVICE_AVAILABLE = True
except ImportError:
    WEATHER_SERVICE_AVAILABLE = False
    logging.warning("天气服务不可用")

class IPQueryHandler:
    """IP查询处理器"""
    
    def __init__(self):
        self.ip_service = None
        self.weather_service = None
        
        if IP_SERVICE_AVAILABLE:
            self.ip_service = get_ip_location_service()
        
        if WEATHER_SERVICE_AVAILABLE:
            self.weather_service = get_weather_service()
        
        # IP查询相关关键词
        self.ip_keywords = {
            "current_ip": [
                "我的IP", "当前IP", "本机IP", "IP地址", "公网IP", "外网IP", "我的ip",
                "查询IP", "查看IP", "获取IP", "显示IP", "IP是什么", "IP是多少",
                "my ip", "current ip", "ip address", "public ip", "external ip",
                "what is my ip", "show my ip", "get my ip", "check ip"
            ],
            "ip_location": [
                "IP位置", "IP地理位置", "IP归属地", "IP所在地", "IP定位", "查询IP位置",
                "ip location", "ip geolocation", "where is ip", "ip address location",
                "locate ip", "find ip location", "ip info", "ip information"
            ],
            "ip_weather": [
                "我这里的天气", "本地天气", "当前位置天气", "我所在地天气", "这里天气",
                "local weather", "weather here", "my location weather", "current location weather"
            ]
        }
        
        # IP地址正则表达式
        self.ip_patterns = [
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IPv4
            r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',  # IPv6完整格式
            r'\b[0-9a-fA-F:]+::[0-9a-fA-F:]*\b'  # IPv6压缩格式
        ]
        
        logging.info("IP查询处理器初始化完成")
    
    def is_ip_query(self, query: str) -> bool:
        """判断是否为IP查询"""
        if not query:
            return False
        
        query_lower = query.lower()
        
        # 检查是否包含IP相关关键词
        all_keywords = []
        for keywords in self.ip_keywords.values():
            all_keywords.extend(keywords)
        
        return any(keyword in query_lower for keyword in all_keywords)
    
    def parse_ip_query(self, query: str) -> Dict[str, Any]:
        """解析IP查询"""
        if not self.is_ip_query(query):
            return {
                "is_ip_query": False,
                "error": "不是IP查询"
            }
        
        try:
            # 确定查询类型
            query_type = self._determine_query_type(query)
            
            # 提取IP地址（如果有）
            ip_address = self._extract_ip_address(query)
            
            result = {
                "is_ip_query": True,
                "query_type": query_type,
                "ip_address": ip_address,
                "original_query": query
            }
            
            logging.info(f"IP查询解析结果: {result}")
            return result
            
        except Exception as e:
            logging.error(f"解析IP查询失败: {e}")
            return {
                "is_ip_query": False,
                "error": f"解析失败: {str(e)}"
            }
    
    def _determine_query_type(self, query: str) -> str:
        """确定查询类型"""
        query_lower = query.lower()
        
        # 检查IP天气查询关键词
        for keyword in self.ip_keywords["ip_weather"]:
            if keyword in query_lower:
                return "ip_weather"
        
        # 检查IP位置查询关键词
        for keyword in self.ip_keywords["ip_location"]:
            if keyword in query_lower:
                return "ip_location"
        
        # 检查当前IP查询关键词
        for keyword in self.ip_keywords["current_ip"]:
            if keyword in query_lower:
                return "current_ip"
        
        # 如果包含IP地址，默认为IP位置查询
        if self._extract_ip_address(query):
            return "ip_location"
        
        # 默认为当前IP查询
        return "current_ip"
    
    def _extract_ip_address(self, query: str) -> Optional[str]:
        """提取IP地址"""
        for pattern in self.ip_patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(0)
        return None
    
    def handle_ip_query(self, query: str) -> Dict[str, Any]:
        """处理IP查询"""
        if not IP_SERVICE_AVAILABLE:
            return {
                "success": False,
                "error": "IP查询服务不可用",
                "response": "❌ IP查询服务暂时不可用，请稍后再试。"
            }
        
        # 解析查询
        parse_result = self.parse_ip_query(query)
        
        if not parse_result.get("is_ip_query"):
            return {
                "success": False,
                "error": "不是IP查询",
                "response": "这不是一个IP查询问题。"
            }
        
        try:
            query_type = parse_result["query_type"]
            ip_address = parse_result["ip_address"]
            
            # 根据查询类型调用相应的服务
            if query_type == "current_ip":
                return self._handle_current_ip_query()
            
            elif query_type == "ip_location":
                if ip_address:
                    return self._handle_ip_location_query(ip_address)
                else:
                    return self._handle_current_ip_query()
            
            elif query_type == "ip_weather":
                return self._handle_ip_weather_query()
            
            else:
                return {
                    "success": False,
                    "error": "不支持的查询类型",
                    "response": "❌ 不支持的IP查询类型。"
                }
            
        except Exception as e:
            logging.error(f"处理IP查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"❌ IP查询失败: {str(e)}"
            }
    
    def _handle_current_ip_query(self) -> Dict[str, Any]:
        """处理当前IP查询"""
        try:
            ip_info = self.ip_service.get_current_ip_info()
            
            if ip_info["success"]:
                response = self.ip_service.format_ip_info_response(ip_info)
                return {
                    "success": True,
                    "query_type": "current_ip",
                    "ip_data": ip_info,
                    "response": response
                }
            else:
                return {
                    "success": False,
                    "error": ip_info.get("error", "未知错误"),
                    "response": f"❌ 获取当前IP信息失败: {ip_info.get('error', '未知错误')}"
                }
                
        except Exception as e:
            logging.error(f"处理当前IP查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"❌ 当前IP查询失败: {str(e)}"
            }
    
    def _handle_ip_location_query(self, ip_address: str) -> Dict[str, Any]:
        """处理IP位置查询"""
        try:
            ip_info = self.ip_service.get_ip_info(ip_address)
            
            if ip_info["success"]:
                response = self.ip_service.format_ip_info_response(ip_info)
                return {
                    "success": True,
                    "query_type": "ip_location",
                    "ip_address": ip_address,
                    "ip_data": ip_info,
                    "response": response
                }
            else:
                return {
                    "success": False,
                    "error": ip_info.get("error", "未知错误"),
                    "response": f"❌ 获取IP {ip_address} 信息失败: {ip_info.get('error', '未知错误')}"
                }
                
        except Exception as e:
            logging.error(f"处理IP位置查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"❌ IP位置查询失败: {str(e)}"
            }
    
    def _handle_ip_weather_query(self) -> Dict[str, Any]:
        """处理基于IP的天气查询"""
        try:
            if not WEATHER_SERVICE_AVAILABLE:
                return {
                    "success": False,
                    "error": "天气服务不可用",
                    "response": "❌ 天气服务暂时不可用，无法查询本地天气。"
                }
            
            # 获取当前位置信息
            location_info = self.ip_service.get_current_location_for_weather()
            
            if not location_info["success"]:
                return {
                    "success": False,
                    "error": location_info.get("error", "获取位置失败"),
                    "response": f"❌ 获取当前位置失败: {location_info.get('error', '未知错误')}"
                }
            
            # 查询天气信息
            location_string = location_info["location_string"]
            weather_data = self.weather_service.get_current_weather(location_string)
            
            if weather_data["success"]:
                # 格式化天气响应
                weather_response = self.weather_service.format_weather_response(weather_data, "current")
                
                # 添加IP位置信息
                ip_location_info = f"""📍 **基于IP的位置检测**
🔗 您的IP: {location_info['ip']}
🏙️ 检测位置: {location_string}
🌐 时区: {location_info['timezone']}

"""
                
                combined_response = ip_location_info + weather_response
                
                return {
                    "success": True,
                    "query_type": "ip_weather",
                    "location_info": location_info,
                    "weather_data": weather_data,
                    "response": combined_response
                }
            else:
                return {
                    "success": False,
                    "error": weather_data.get("error", "天气查询失败"),
                    "response": f"❌ 本地天气查询失败: {weather_data.get('error', '未知错误')}"
                }
                
        except Exception as e:
            logging.error(f"处理IP天气查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"❌ 本地天气查询失败: {str(e)}"
            }
    
    def get_ip_query_suggestions(self) -> List[str]:
        """获取IP查询建议"""
        return [
            "我的IP地址是什么？",
            "查询当前IP位置",
            "我这里的天气怎么样？",
            "本地天气如何？",
            "查询IP 8.8.8.8 的位置",
            "我的公网IP是多少？",
            "当前位置的天气",
            "我所在地的天气情况"
        ]

# 全局IP查询处理器实例
ip_query_handler = IPQueryHandler()

def get_ip_query_handler() -> IPQueryHandler:
    """获取IP查询处理器实例"""
    return ip_query_handler

def is_ip_query(query: str) -> bool:
    """快速判断是否为IP查询"""
    return ip_query_handler.is_ip_query(query)

def handle_ip_query(query: str) -> Dict[str, Any]:
    """快速处理IP查询"""
    return ip_query_handler.handle_ip_query(query)
