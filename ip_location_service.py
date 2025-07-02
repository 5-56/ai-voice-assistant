#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP地址查询和地理位置服务模块
支持查询当前IP地址、IP地理位置信息和基于IP的天气查询
"""

import requests
import json
import logging
from typing import Dict, Any, Optional
import re

class IPLocationService:
    """IP地址和地理位置查询服务"""
    
    def __init__(self):
        # ipapi.co API配置
        self.ipapi_base_url = "https://ipapi.co"
        
        # 请求超时设置
        self.timeout = 10
        
        # 请求头设置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        logging.info("IP地址查询服务初始化完成")
    
    def get_current_ip_info(self) -> Dict[str, Any]:
        """获取当前IP地址的完整信息"""
        try:
            url = f"{self.ipapi_base_url}/json/"
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查是否有错误
            if "error" in data:
                return {
                    "success": False,
                    "error": data.get("reason", "未知错误")
                }
            
            # 解析IP信息
            ip_info = {
                "success": True,
                "ip": data.get("ip", "未知"),
                "version": data.get("version", "未知"),
                "city": data.get("city", "未知"),
                "region": data.get("region", "未知"),
                "region_code": data.get("region_code", ""),
                "country": data.get("country_name", "未知"),
                "country_code": data.get("country_code", ""),
                "continent": data.get("continent_code", ""),
                "postal": data.get("postal", ""),
                "latitude": data.get("latitude", 0),
                "longitude": data.get("longitude", 0),
                "timezone": data.get("timezone", "未知"),
                "utc_offset": data.get("utc_offset", ""),
                "country_calling_code": data.get("country_calling_code", ""),
                "currency": data.get("currency", ""),
                "currency_name": data.get("currency_name", ""),
                "languages": data.get("languages", ""),
                "asn": data.get("asn", ""),
                "org": data.get("org", ""),
                "data_source": "ipapi.co"
            }
            
            logging.info(f"获取IP信息成功: {ip_info['ip']}")
            return ip_info
            
        except requests.exceptions.RequestException as e:
            logging.error(f"获取IP信息失败: {e}")
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            logging.error(f"解析IP信息失败: {e}")
            return {
                "success": False,
                "error": f"数据解析失败: {str(e)}"
            }
    
    def get_ip_info(self, ip_address: str) -> Dict[str, Any]:
        """获取指定IP地址的信息"""
        try:
            # 验证IP地址格式
            if not self._is_valid_ip(ip_address):
                return {
                    "success": False,
                    "error": "无效的IP地址格式"
                }
            
            url = f"{self.ipapi_base_url}/{ip_address}/json/"
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查是否有错误
            if "error" in data:
                return {
                    "success": False,
                    "error": data.get("reason", "未知错误")
                }
            
            # 解析IP信息
            ip_info = {
                "success": True,
                "ip": data.get("ip", ip_address),
                "version": data.get("version", "未知"),
                "city": data.get("city", "未知"),
                "region": data.get("region", "未知"),
                "region_code": data.get("region_code", ""),
                "country": data.get("country_name", "未知"),
                "country_code": data.get("country_code", ""),
                "continent": data.get("continent_code", ""),
                "postal": data.get("postal", ""),
                "latitude": data.get("latitude", 0),
                "longitude": data.get("longitude", 0),
                "timezone": data.get("timezone", "未知"),
                "utc_offset": data.get("utc_offset", ""),
                "country_calling_code": data.get("country_calling_code", ""),
                "currency": data.get("currency", ""),
                "currency_name": data.get("currency_name", ""),
                "languages": data.get("languages", ""),
                "asn": data.get("asn", ""),
                "org": data.get("org", ""),
                "data_source": "ipapi.co"
            }
            
            logging.info(f"获取IP信息成功: {ip_address}")
            return ip_info
            
        except requests.exceptions.RequestException as e:
            logging.error(f"获取IP信息失败: {e}")
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            logging.error(f"解析IP信息失败: {e}")
            return {
                "success": False,
                "error": f"数据解析失败: {str(e)}"
            }
    
    def get_ip_field(self, ip_address: str, field: str) -> Dict[str, Any]:
        """获取IP地址的特定字段信息"""
        try:
            # 验证IP地址格式
            if not self._is_valid_ip(ip_address):
                return {
                    "success": False,
                    "error": "无效的IP地址格式"
                }
            
            # 验证字段名
            valid_fields = [
                "ip", "city", "region", "region_code", "country", "country_code",
                "country_name", "continent_code", "postal", "latitude", "longitude",
                "timezone", "utc_offset", "country_calling_code", "currency",
                "currency_name", "languages", "asn", "org"
            ]
            
            if field not in valid_fields:
                return {
                    "success": False,
                    "error": f"无效的字段名: {field}"
                }
            
            url = f"{self.ipapi_base_url}/{ip_address}/{field}/"
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            # 获取字段值
            field_value = response.text.strip()
            
            return {
                "success": True,
                "ip": ip_address,
                "field": field,
                "value": field_value,
                "data_source": "ipapi.co"
            }
            
        except requests.exceptions.RequestException as e:
            logging.error(f"获取IP字段信息失败: {e}")
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            logging.error(f"解析IP字段信息失败: {e}")
            return {
                "success": False,
                "error": f"数据解析失败: {str(e)}"
            }
    
    def get_current_location_for_weather(self) -> Dict[str, Any]:
        """获取当前位置信息用于天气查询"""
        try:
            ip_info = self.get_current_ip_info()
            
            if not ip_info["success"]:
                return ip_info
            
            # 构建位置信息
            city = ip_info.get("city", "")
            region = ip_info.get("region", "")
            country = ip_info.get("country", "")
            
            # 构建位置字符串
            location_parts = []
            if city and city != "未知":
                location_parts.append(city)
            if region and region != "未知" and region != city:
                location_parts.append(region)
            
            location_string = ", ".join(location_parts) if location_parts else country
            
            return {
                "success": True,
                "location_string": location_string,
                "city": city,
                "region": region,
                "country": country,
                "latitude": ip_info.get("latitude", 0),
                "longitude": ip_info.get("longitude", 0),
                "ip": ip_info.get("ip", ""),
                "timezone": ip_info.get("timezone", "")
            }
            
        except Exception as e:
            logging.error(f"获取当前位置失败: {e}")
            return {
                "success": False,
                "error": f"获取当前位置失败: {str(e)}"
            }
    
    def _is_valid_ip(self, ip_address: str) -> bool:
        """验证IP地址格式"""
        try:
            # IPv4格式验证
            ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            if re.match(ipv4_pattern, ip_address):
                parts = ip_address.split('.')
                return all(0 <= int(part) <= 255 for part in parts)
            
            # IPv6格式验证（简单验证）
            ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
            if re.match(ipv6_pattern, ip_address):
                return True
            
            # 压缩IPv6格式
            if '::' in ip_address:
                return True
            
            return False
            
        except Exception:
            return False
    
    def format_ip_info_response(self, ip_info: Dict[str, Any]) -> str:
        """格式化IP信息响应"""
        if not ip_info.get("success"):
            return f"❌ IP信息查询失败: {ip_info.get('error', '未知错误')}"
        
        try:
            response = f"""🌐 **IP地址信息查询结果**

📍 **基本信息**
🔗 IP地址: {ip_info['ip']}
📊 IP版本: IPv{ip_info['version']}
🏢 网络组织: {ip_info.get('org', '未知')}
🆔 ASN: {ip_info.get('asn', '未知')}

🗺️ **地理位置**
🏙️ 城市: {ip_info['city']}
🏞️ 地区: {ip_info['region']} ({ip_info.get('region_code', '')})
🇨🇳 国家: {ip_info['country']} ({ip_info.get('country_code', '')})
🌍 大洲: {ip_info.get('continent', '未知')}
📮 邮编: {ip_info.get('postal', '未知')}

📐 **坐标信息**
📍 纬度: {ip_info['latitude']}
📍 经度: {ip_info['longitude']}

🕐 **时区信息**
⏰ 时区: {ip_info['timezone']}
🌐 UTC偏移: {ip_info.get('utc_offset', '未知')}

💰 **区域信息**
💱 货币: {ip_info.get('currency_name', '未知')} ({ip_info.get('currency', '')})
🗣️ 语言: {ip_info.get('languages', '未知')}
📞 国际区号: {ip_info.get('country_calling_code', '未知')}

📡 数据来源: {ip_info['data_source']}"""
            
            return response
            
        except Exception as e:
            logging.error(f"格式化IP信息响应失败: {e}")
            return f"❌ 格式化IP信息失败: {str(e)}"

# 全局IP地址查询服务实例
ip_location_service = IPLocationService()

def get_ip_location_service() -> IPLocationService:
    """获取IP地址查询服务实例"""
    return ip_location_service
