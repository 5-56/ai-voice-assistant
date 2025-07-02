#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气查询处理模块
智能识别用户的天气查询意图并调用相应的天气服务
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import jieba

# 天气服务导入
try:
    from weather_service import get_weather_service
    WEATHER_SERVICE_AVAILABLE = True
except ImportError:
    WEATHER_SERVICE_AVAILABLE = False
    logging.warning("天气服务不可用")

class WeatherQueryHandler:
    """天气查询处理器"""
    
    def __init__(self):
        self.weather_service = None
        if WEATHER_SERVICE_AVAILABLE:
            self.weather_service = get_weather_service()
        
        # 天气相关关键词
        self.weather_keywords = {
            "current": [
                "天气", "气温", "温度", "现在", "当前", "今天", "今日",
                "weather", "temperature", "current", "today", "now"
            ],
            "forecast": [
                "预报", "预测", "明天", "后天", "未来", "几天", "一周",
                "forecast", "prediction", "tomorrow", "future", "week"
            ],
            "historical": [
                "历史", "过去", "昨天", "前天", "之前", "那天",
                "historical", "past", "yesterday", "before", "history"
            ]
        }
        
        # 地点识别模式
        self.location_patterns = [
            r"(.+?)的天气",
            r"(.+?)天气",
            r"在(.+?)的",
            r"(.+?)地区",
            r"(.+?)市",
            r"(.+?)省",
            r"(.+?)国",
            # 英文模式
            r"weather in (.+?)[\?\s]",
            r"weather in (.+?)$",
            r"in (.+?) weather",
            r"(.+?) weather",
        ]
        
        # 时间识别模式
        self.time_patterns = {
            "今天": 0,
            "今日": 0,
            "现在": 0,
            "当前": 0,
            "明天": 1,
            "明日": 1,
            "后天": 2,
            "昨天": -1,
            "昨日": -1,
            "前天": -2,
        }
        
        # 常见城市别名
        self.city_aliases = {
            "北京": "Beijing",
            "上海": "Shanghai",
            "广州": "Guangzhou",
            "深圳": "Shenzhen",
            "杭州": "Hangzhou",
            "南京": "Nanjing",
            "武汉": "Wuhan",
            "成都": "Chengdu",
            "西安": "Xi'an",
            "重庆": "Chongqing",
            "天津": "Tianjin",
            "苏州": "Suzhou",
            "青岛": "Qingdao",
            "大连": "Dalian",
            "厦门": "Xiamen",
            "宁波": "Ningbo",
            "无锡": "Wuxi",
            "佛山": "Foshan",
            "东莞": "Dongguan",
            "泉州": "Quanzhou",
            "纽约": "New York"
        }

        # 英文城市名
        self.english_cities = [
            "Tokyo", "London", "Paris", "Berlin", "Rome", "Madrid", "Amsterdam",
            "Vienna", "Prague", "Budapest", "Warsaw", "Stockholm", "Oslo",
            "Copenhagen", "Helsinki", "Dublin", "Edinburgh", "Manchester",
            "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
            "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
            "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte",
            "San Francisco", "Indianapolis", "Seattle", "Denver", "Washington",
            "Boston", "El Paso", "Detroit", "Nashville", "Portland", "Memphis",
            "Oklahoma City", "Las Vegas", "Louisville", "Baltimore", "Milwaukee",
            "Albuquerque", "Tucson", "Fresno", "Sacramento", "Kansas City",
            "Mesa", "Atlanta", "Colorado Springs", "Raleigh", "Omaha",
            "Miami", "Oakland", "Minneapolis", "Tulsa", "Cleveland",
            "Wichita", "Arlington", "New Orleans", "Bakersfield", "Tampa",
            "Honolulu", "Aurora", "Anaheim", "Santa Ana", "St. Louis",
            "Riverside", "Corpus Christi", "Lexington", "Pittsburgh", "Anchorage",
            "Stockton", "Cincinnati", "St. Paul", "Toledo", "Greensboro",
            "Newark", "Plano", "Henderson", "Lincoln", "Buffalo", "Jersey City",
            "Chula Vista", "Fort Wayne", "Orlando", "St. Petersburg",
            "Chandler", "Laredo", "Norfolk", "Durham", "Madison", "Lubbock",
            "Irvine", "Winston-Salem", "Glendale", "Garland", "Hialeah",
            "Reno", "Chesapeake", "Gilbert", "Baton Rouge", "Irving",
            "Scottsdale", "North Las Vegas", "Fremont", "Boise", "Richmond"
        ]
        
        logging.info("天气查询处理器初始化完成")
    
    def is_weather_query(self, query: str) -> bool:
        """判断是否为天气查询"""
        if not query:
            return False
        
        query_lower = query.lower()
        
        # 检查是否包含天气相关关键词
        all_keywords = []
        for keywords in self.weather_keywords.values():
            all_keywords.extend(keywords)
        
        return any(keyword in query_lower for keyword in all_keywords)
    
    def parse_weather_query(self, query: str) -> Dict[str, Any]:
        """解析天气查询"""
        if not self.is_weather_query(query):
            return {
                "is_weather_query": False,
                "error": "不是天气查询"
            }
        
        try:
            # 确定查询类型
            query_type = self._determine_query_type(query)
            
            # 提取地点
            location = self._extract_location(query)
            
            # 提取时间信息
            time_info = self._extract_time_info(query)
            
            # 如果没有指定地点，使用默认地点
            if not location:
                location = "北京"  # 默认地点
            
            # 处理城市别名
            if location in self.city_aliases:
                location = self.city_aliases[location]
            
            result = {
                "is_weather_query": True,
                "query_type": query_type,
                "location": location,
                "time_info": time_info,
                "original_query": query
            }
            
            logging.info(f"天气查询解析结果: {result}")
            return result
            
        except Exception as e:
            logging.error(f"解析天气查询失败: {e}")
            return {
                "is_weather_query": False,
                "error": f"解析失败: {str(e)}"
            }
    
    def _determine_query_type(self, query: str) -> str:
        """确定查询类型"""
        query_lower = query.lower()
        
        # 检查历史天气关键词
        for keyword in self.weather_keywords["historical"]:
            if keyword in query_lower:
                return "historical"
        
        # 检查预报关键词
        for keyword in self.weather_keywords["forecast"]:
            if keyword in query_lower:
                return "forecast"
        
        # 默认为当前天气
        return "current"
    
    def _extract_location(self, query: str) -> Optional[str]:
        """提取地点信息"""
        # 首先检查英文城市名（精确匹配）
        query_lower = query.lower()
        for city in self.english_cities:
            if city.lower() in query_lower:
                return city

        # 检查中文城市别名
        for city in self.city_aliases.keys():
            if city in query:
                return city

        # 使用jieba分词提取地名
        try:
            words = jieba.lcut(query)
            for word in words:
                if len(word) >= 2 and (
                    word.endswith("市") or
                    word.endswith("省") or
                    word.endswith("区") or
                    word.endswith("县") or
                    word in self.city_aliases
                ):
                    return word
        except:
            pass

        # 尝试各种地点模式（作为备选）
        for pattern in self.location_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # 过滤掉时间词和无意义的词
                time_words = ["今天", "明天", "后天", "昨天", "前天", "现在", "当前", "未来", "一周", "几天",
                             "today", "tomorrow", "yesterday", "now", "current", "future", "week", "days"]
                filter_words = ["这里", "那里", "哪里", "什么", "怎么", "the", "a", "an", "is", "are", "will", "be"]

                if location and location.lower() not in [w.lower() for w in filter_words + time_words]:
                    # 进一步清理时间词
                    for time_word in time_words:
                        location = re.sub(r'\b' + re.escape(time_word) + r'\b', '', location, flags=re.IGNORECASE).strip()
                    if location:
                        return location

        return None
    
    def _extract_time_info(self, query: str) -> Dict[str, Any]:
        """提取时间信息"""
        time_info = {
            "type": "current",
            "date": None,
            "days_offset": 0
        }
        
        # 检查时间关键词
        for time_word, offset in self.time_patterns.items():
            if time_word in query:
                if offset < 0:
                    time_info["type"] = "historical"
                elif offset > 0:
                    time_info["type"] = "forecast"
                else:
                    time_info["type"] = "current"
                
                time_info["days_offset"] = offset
                
                # 计算具体日期
                target_date = datetime.now() + timedelta(days=offset)
                time_info["date"] = target_date.strftime("%Y-%m-%d")
                break
        
        # 检查是否包含"几天"、"一周"等
        if re.search(r"[几\d]+天|一周|七天", query):
            time_info["type"] = "forecast"
        
        return time_info
    
    def handle_weather_query(self, query: str) -> Dict[str, Any]:
        """处理天气查询"""
        if not WEATHER_SERVICE_AVAILABLE:
            return {
                "success": False,
                "error": "天气服务不可用",
                "response": "❌ 天气服务暂时不可用，请稍后再试。"
            }
        
        # 解析查询
        parse_result = self.parse_weather_query(query)
        
        if not parse_result.get("is_weather_query"):
            return {
                "success": False,
                "error": "不是天气查询",
                "response": "这不是一个天气查询问题。"
            }
        
        try:
            query_type = parse_result["query_type"]
            location = parse_result["location"]
            time_info = parse_result["time_info"]
            
            # 根据查询类型调用相应的服务
            if query_type == "current":
                weather_data = self.weather_service.get_current_weather(location)
                response = self.weather_service.format_weather_response(weather_data, "current")
            
            elif query_type == "forecast":
                weather_data = self.weather_service.get_weather_forecast(location)
                response = self.weather_service.format_weather_response(weather_data, "forecast")
            
            elif query_type == "historical":
                if time_info.get("date"):
                    weather_data = self.weather_service.get_historical_weather(location, time_info["date"])
                    response = self.weather_service.format_weather_response(weather_data, "historical")
                else:
                    return {
                        "success": False,
                        "error": "缺少历史日期",
                        "response": "❌ 查询历史天气需要指定具体日期。"
                    }
            
            else:
                return {
                    "success": False,
                    "error": "不支持的查询类型",
                    "response": "❌ 不支持的天气查询类型。"
                }
            
            return {
                "success": weather_data.get("success", False),
                "query_info": parse_result,
                "weather_data": weather_data,
                "response": response,
                "error": weather_data.get("error") if not weather_data.get("success") else None
            }
            
        except Exception as e:
            logging.error(f"处理天气查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": f"❌ 天气查询失败: {str(e)}"
            }
    
    def get_weather_suggestions(self) -> List[str]:
        """获取天气查询建议"""
        return [
            "北京今天天气怎么样？",
            "上海明天的天气预报",
            "广州未来一周天气",
            "深圳昨天的天气",
            "杭州的当前气温",
            "成都今天会下雨吗？",
            "西安明天温度多少？",
            "武汉这几天天气如何？"
        ]

# 全局天气查询处理器实例
weather_query_handler = WeatherQueryHandler()

def get_weather_query_handler() -> WeatherQueryHandler:
    """获取天气查询处理器实例"""
    return weather_query_handler

def is_weather_query(query: str) -> bool:
    """快速判断是否为天气查询"""
    return weather_query_handler.is_weather_query(query)

def handle_weather_query(query: str) -> Dict[str, Any]:
    """快速处理天气查询"""
    return weather_query_handler.handle_weather_query(query)
