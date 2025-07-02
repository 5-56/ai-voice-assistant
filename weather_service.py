#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气查询服务模块
支持实时天气、历史天气和天气预报查询
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import re

class WeatherService:
    """天气查询服务"""
    
    def __init__(self):
        # WeatherStack API配置（实时+历史天气）
        self.weatherstack_api_key = "7056f4f64899db0646232edc2b2e5568"
        self.weatherstack_base_url = "http://api.weatherstack.com"
        
        # OpenWeatherMap API配置（全球天气预报）
        self.openweather_api_key = "5809b5cf4ee8eeb8ac073f6acb37b798"
        # 使用2.5版本API，更稳定且免费计划支持
        self.openweather_base_url = "https://api.openweathermap.org/data/2.5/onecall"
        self.openweather_geo_url = "https://api.openweathermap.org/geo/1.0/direct"
        # 备用API - 当前天气和5天预报
        self.openweather_current_url = "https://api.openweathermap.org/data/2.5/weather"
        self.openweather_forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        
        # 请求超时设置
        self.timeout = 10
        
        logging.info("天气查询服务初始化完成")
    
    def get_current_weather(self, location: str) -> Dict[str, Any]:
        """获取当前天气"""
        try:
            url = f"{self.weatherstack_base_url}/current"
            params = {
                "access_key": self.weatherstack_api_key,
                "query": location,
                "units": "m"  # 使用公制单位
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                return {
                    "success": False,
                    "error": data["error"]["info"]
                }
            
            # 解析天气数据
            current = data.get("current", {})
            location_info = data.get("location", {})
            
            weather_info = {
                "success": True,
                "location": {
                    "name": location_info.get("name", "未知"),
                    "country": location_info.get("country", "未知"),
                    "region": location_info.get("region", ""),
                    "lat": location_info.get("lat", 0),
                    "lon": location_info.get("lon", 0),
                    "timezone": location_info.get("timezone_id", ""),
                    "local_time": location_info.get("localtime", "")
                },
                "current": {
                    "temperature": current.get("temperature", 0),
                    "feels_like": current.get("feelslike", 0),
                    "humidity": current.get("humidity", 0),
                    "pressure": current.get("pressure", 0),
                    "visibility": current.get("visibility", 0),
                    "uv_index": current.get("uv_index", 0),
                    "wind_speed": current.get("wind_speed", 0),
                    "wind_direction": current.get("wind_dir", ""),
                    "wind_degree": current.get("wind_degree", 0),
                    "weather_descriptions": current.get("weather_descriptions", []),
                    "weather_icons": current.get("weather_icons", []),
                    "is_day": current.get("is_day", "yes") == "yes"
                },
                "observation_time": current.get("observation_time", ""),
                "data_source": "WeatherStack"
            }
            
            logging.info(f"获取当前天气成功: {location}")
            return weather_info
            
        except requests.exceptions.RequestException as e:
            logging.error(f"获取当前天气失败: {e}")
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            logging.error(f"解析天气数据失败: {e}")
            return {
                "success": False,
                "error": f"数据解析失败: {str(e)}"
            }
    
    def get_historical_weather(self, location: str, date: str) -> Dict[str, Any]:
        """获取历史天气"""
        try:
            url = f"{self.weatherstack_base_url}/historical"
            params = {
                "access_key": self.weatherstack_api_key,
                "query": location,
                "historical_date": date,
                "units": "m"
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                return {
                    "success": False,
                    "error": data["error"]["info"]
                }
            
            # 解析历史天气数据
            historical = data.get("historical", {})
            location_info = data.get("location", {})
            
            weather_info = {
                "success": True,
                "location": {
                    "name": location_info.get("name", "未知"),
                    "country": location_info.get("country", "未知"),
                    "region": location_info.get("region", "")
                },
                "date": date,
                "historical": historical,
                "data_source": "WeatherStack"
            }
            
            logging.info(f"获取历史天气成功: {location} - {date}")
            return weather_info
            
        except requests.exceptions.RequestException as e:
            logging.error(f"获取历史天气失败: {e}")
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            logging.error(f"解析历史天气数据失败: {e}")
            return {
                "success": False,
                "error": f"数据解析失败: {str(e)}"
            }
    
    def get_coordinates(self, location: str) -> Dict[str, Any]:
        """获取地理坐标"""
        try:
            url = self.openweather_geo_url
            params = {
                "q": location,
                "limit": 1,
                "appid": self.openweather_api_key
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return {
                    "success": False,
                    "error": "未找到指定位置"
                }
            
            location_data = data[0]
            return {
                "success": True,
                "lat": location_data.get("lat"),
                "lon": location_data.get("lon"),
                "name": location_data.get("name"),
                "country": location_data.get("country"),
                "state": location_data.get("state", "")
            }
            
        except Exception as e:
            logging.error(f"获取坐标失败: {e}")
            return {
                "success": False,
                "error": f"获取坐标失败: {str(e)}"
            }
    
    def get_weather_forecast(self, location: str, days: int = 7) -> Dict[str, Any]:
        """获取天气预报"""
        try:
            # 首先尝试使用5天预报API（更稳定）
            return self._get_forecast_5day(location)

        except Exception as e:
            logging.error(f"5天预报API失败，尝试OneCall API: {e}")
            # 备用：尝试OneCall API
            return self._get_forecast_onecall(location, days)

    def _get_forecast_5day(self, location: str) -> Dict[str, Any]:
        """使用5天预报API获取天气预报"""
        try:
            # 首先获取坐标
            coord_result = self.get_coordinates(location)
            if not coord_result["success"]:
                return coord_result

            lat = coord_result["lat"]
            lon = coord_result["lon"]

            # 获取当前天气
            current_url = self.openweather_current_url
            current_params = {
                "lat": lat,
                "lon": lon,
                "appid": self.openweather_api_key,
                "units": "metric",
                "lang": "zh_cn"
            }

            current_response = requests.get(current_url, params=current_params, timeout=self.timeout)
            current_response.raise_for_status()
            current_data = current_response.json()

            # 获取5天预报
            forecast_url = self.openweather_forecast_url
            forecast_params = {
                "lat": lat,
                "lon": lon,
                "appid": self.openweather_api_key,
                "units": "metric",
                "lang": "zh_cn"
            }

            forecast_response = requests.get(forecast_url, params=forecast_params, timeout=self.timeout)
            forecast_response.raise_for_status()
            forecast_data = forecast_response.json()

            # 解析当前天气
            current_weather = current_data.get("main", {})
            current_wind = current_data.get("wind", {})
            current_sys = current_data.get("sys", {})
            current_weather_desc = current_data.get("weather", [{}])[0]

            # 解析预报数据
            forecast_list = forecast_data.get("list", [])

            # 按天分组预报数据
            daily_forecasts = []
            current_date = None
            daily_data = []

            for item in forecast_list[:40]:  # 5天 * 8次/天 = 40个数据点
                item_date = datetime.fromtimestamp(item["dt"]).date()

                if current_date != item_date:
                    if daily_data:
                        # 处理前一天的数据
                        daily_forecasts.append(self._process_daily_data(daily_data))
                    daily_data = [item]
                    current_date = item_date
                else:
                    daily_data.append(item)

            # 处理最后一天的数据
            if daily_data:
                daily_forecasts.append(self._process_daily_data(daily_data))

            weather_info = {
                "success": True,
                "location": {
                    "name": coord_result["name"],
                    "country": coord_result["country"],
                    "state": coord_result.get("state", ""),
                    "lat": lat,
                    "lon": lon
                },
                "current": {
                    "temperature": current_weather.get("temp", 0),
                    "feels_like": current_weather.get("feels_like", 0),
                    "humidity": current_weather.get("humidity", 0),
                    "pressure": current_weather.get("pressure", 0),
                    "visibility": current_data.get("visibility", 0) / 1000,  # 转换为km
                    "uv_index": 0,  # 5天预报API不提供UV指数
                    "wind_speed": current_wind.get("speed", 0),
                    "wind_direction": current_wind.get("deg", 0),
                    "weather": current_weather_desc,
                    "sunrise": current_sys.get("sunrise", 0),
                    "sunset": current_sys.get("sunset", 0)
                },
                "daily_forecast": daily_forecasts[:5],  # 限制为5天
                "hourly_forecast": forecast_list[:24],  # 24小时预报
                "timezone": forecast_data.get("city", {}).get("timezone", 0),
                "data_source": "OpenWeatherMap (5-day)"
            }

            logging.info(f"获取5天天气预报成功: {location}")
            return weather_info

        except requests.exceptions.RequestException as e:
            logging.error(f"获取5天天气预报失败: {e}")
            raise
        except Exception as e:
            logging.error(f"解析5天预报数据失败: {e}")
            raise

    def _process_daily_data(self, daily_data: list) -> Dict[str, Any]:
        """处理每日预报数据"""
        if not daily_data:
            return {}

        # 计算当天的平均值和极值
        temps = [item["main"]["temp"] for item in daily_data]
        humidities = [item["main"]["humidity"] for item in daily_data]

        # 获取最常见的天气描述
        weather_descriptions = [item["weather"][0] for item in daily_data]
        main_weather = weather_descriptions[len(weather_descriptions)//2]  # 取中间时段的天气

        return {
            "dt": daily_data[0]["dt"],
            "temp": {
                "day": sum(temps) / len(temps),
                "night": min(temps),
                "max": max(temps),
                "min": min(temps)
            },
            "humidity": sum(humidities) / len(humidities),
            "weather": [main_weather]
        }

    def _get_forecast_onecall(self, location: str, days: int = 7) -> Dict[str, Any]:
        """使用OneCall API获取天气预报（备用方法）"""
        try:
            # 首先获取坐标
            coord_result = self.get_coordinates(location)
            if not coord_result["success"]:
                return coord_result

            lat = coord_result["lat"]
            lon = coord_result["lon"]

            url = self.openweather_base_url
            params = {
                "lat": lat,
                "lon": lon,
                "exclude": "minutely,alerts",
                "appid": self.openweather_api_key,
                "units": "metric",  # 使用摄氏度
                "lang": "zh_cn"     # 中文描述
            }

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 解析预报数据
            current = data.get("current", {})
            daily = data.get("daily", [])[:days]  # 限制天数
            hourly = data.get("hourly", [])[:24]  # 24小时预报

            weather_info = {
                "success": True,
                "location": {
                    "name": coord_result["name"],
                    "country": coord_result["country"],
                    "state": coord_result.get("state", ""),
                    "lat": lat,
                    "lon": lon
                },
                "current": {
                    "temperature": current.get("temp", 0),
                    "feels_like": current.get("feels_like", 0),
                    "humidity": current.get("humidity", 0),
                    "pressure": current.get("pressure", 0),
                    "visibility": current.get("visibility", 0),
                    "uv_index": current.get("uvi", 0),
                    "wind_speed": current.get("wind_speed", 0),
                    "wind_direction": current.get("wind_deg", 0),
                    "weather": current.get("weather", [{}])[0],
                    "sunrise": current.get("sunrise", 0),
                    "sunset": current.get("sunset", 0)
                },
                "daily_forecast": daily,
                "hourly_forecast": hourly,
                "timezone": data.get("timezone", ""),
                "data_source": "OpenWeatherMap (OneCall)"
            }

            logging.info(f"获取OneCall天气预报成功: {location}")
            return weather_info

        except requests.exceptions.RequestException as e:
            logging.error(f"获取OneCall天气预报失败: {e}")
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            logging.error(f"解析OneCall预报数据失败: {e}")
            return {
                "success": False,
                "error": f"数据解析失败: {str(e)}"
            }

    def format_weather_response(self, weather_data: Dict[str, Any], query_type: str = "current") -> str:
        """格式化天气响应"""
        if not weather_data.get("success"):
            return f"❌ 天气查询失败: {weather_data.get('error', '未知错误')}"
        
        try:
            if query_type == "current":
                return self._format_current_weather(weather_data)
            elif query_type == "historical":
                return self._format_historical_weather(weather_data)
            elif query_type == "forecast":
                return self._format_forecast_weather(weather_data)
            else:
                return "❌ 不支持的查询类型"
                
        except Exception as e:
            logging.error(f"格式化天气响应失败: {e}")
            return f"❌ 格式化天气信息失败: {str(e)}"
    
    def _format_current_weather(self, data: Dict[str, Any]) -> str:
        """格式化当前天气"""
        location = data["location"]
        current = data["current"]
        
        location_str = f"{location['name']}"
        if location.get("region"):
            location_str += f", {location['region']}"
        location_str += f", {location['country']}"
        
        weather_desc = ", ".join(current.get("weather_descriptions", ["未知"]))
        
        response = f"""🌤️ **{location_str}** 当前天气

🌡️ **温度**: {current['temperature']}°C (体感 {current['feels_like']}°C)
☁️ **天气**: {weather_desc}
💧 **湿度**: {current['humidity']}%
🌬️ **风速**: {current['wind_speed']} km/h ({current['wind_direction']})
📊 **气压**: {current['pressure']} mb
👁️ **能见度**: {current['visibility']} km
☀️ **紫外线指数**: {current['uv_index']}

⏰ **观测时间**: {data['observation_time']}
📍 **坐标**: {location['lat']}, {location['lon']}
🕐 **当地时间**: {location.get('local_time', '未知')}

📡 数据来源: {data['data_source']}"""
        
        return response
    
    def _format_historical_weather(self, data: Dict[str, Any]) -> str:
        """格式化历史天气"""
        location = data["location"]
        date = data["date"]
        
        location_str = f"{location['name']}"
        if location.get("region"):
            location_str += f", {location['region']}"
        location_str += f", {location['country']}"
        
        response = f"""📅 **{location_str}** {date} 历史天气

📡 数据来源: {data['data_source']}

ℹ️ 历史天气详细数据请查看返回的JSON数据"""
        
        return response
    
    def _format_forecast_weather(self, data: Dict[str, Any]) -> str:
        """格式化天气预报"""
        location = data["location"]
        current = data["current"]
        daily = data["daily_forecast"]
        
        location_str = f"{location['name']}"
        if location.get("state"):
            location_str += f", {location['state']}"
        location_str += f", {location['country']}"
        
        # 当前天气
        current_weather = current.get("weather", {})
        response = f"""🌤️ **{location_str}** 天气预报

**🔸 当前天气**
🌡️ 温度: {current['temperature']}°C (体感 {current['feels_like']}°C)
☁️ 天气: {current_weather.get('description', '未知')}
💧 湿度: {current['humidity']}%
🌬️ 风速: {current['wind_speed']} m/s
📊 气压: {current['pressure']} hPa
☀️ 紫外线指数: {current['uv_index']}

**📅 未来几天预报**"""
        
        # 每日预报
        for i, day in enumerate(daily[:5]):  # 显示5天预报
            date = datetime.fromtimestamp(day.get("dt", 0)).strftime("%m月%d日")
            temp_day = day.get("temp", {}).get("day", 0)
            temp_night = day.get("temp", {}).get("night", 0)
            weather_desc = day.get("weather", [{}])[0].get("description", "未知")
            humidity = day.get("humidity", 0)
            
            if i == 0:
                date = "今天"
            elif i == 1:
                date = "明天"
            elif i == 2:
                date = "后天"
            
            response += f"""
**{date}**: {weather_desc} 🌡️{temp_day}°C/{temp_night}°C 💧{humidity}%"""
        
        response += f"""

📍 坐标: {location['lat']}, {location['lon']}
🕐 时区: {data.get('timezone', '未知')}
📡 数据来源: {data['data_source']}"""
        
        return response

# 全局天气服务实例
weather_service = WeatherService()

def get_weather_service() -> WeatherService:
    """获取天气服务实例"""
    return weather_service
