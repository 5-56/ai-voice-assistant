#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音识别管理器
实现STT（Speech to Text）功能，支持实时语音输入
"""

import asyncio
import logging
import threading
import time
import queue
import numpy as np
from typing import Optional, Callable, Dict, Any
from pathlib import Path

# 语音识别相关导入
try:
    import speech_recognition as sr
    import pyaudio
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logging.warning("语音识别模块不可用，请安装: pip install SpeechRecognition pyaudio")

# 语音活动检测
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    logging.warning("VAD模块不可用，请安装: pip install webrtcvad")

class SpeechRecognitionManager:
    """语音识别管理器"""
    
    def __init__(self):
        self.is_listening = False
        self.is_recording = False
        self.recognizer = None
        self.microphone = None
        self.audio_queue = queue.Queue()
        self.vad = None
        
        # 配置参数（优化速度）
        self.sample_rate = 16000
        self.chunk_duration = 0.03  # 30ms chunks
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.silence_threshold = 0.3  # 静音阈值（秒）- 减少等待时间
        self.max_recording_time = 10  # 最大录音时间（秒）- 减少超时时间
        self.listen_timeout = 0.5     # 监听超时时间（秒）- 提高响应速度
        
        # 回调函数
        self.on_speech_start = None
        self.on_speech_end = None
        self.on_text_recognized = None
        self.on_error = None
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化语音识别组件"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logging.error("语音识别功能不可用")
            return False
        
        try:
            # 初始化语音识别器
            self.recognizer = sr.Recognizer()
            
            # 调整识别器参数（优化速度）
            self.recognizer.energy_threshold = 400  # 提高阈值，减少误触发
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.5   # 减少暂停时间，提高响应速度
            self.recognizer.phrase_threshold = 0.2  # 减少短语阈值，更快开始识别
            self.recognizer.non_speaking_duration = 0.3  # 减少非说话检测时间
            
            # 初始化麦克风
            self.microphone = sr.Microphone(sample_rate=self.sample_rate)
            
            # 初始化VAD
            if VAD_AVAILABLE:
                self.vad = webrtcvad.Vad(2)  # 中等敏感度
            
            # 校准环境噪音
            self._calibrate_noise()
            
            logging.info("语音识别组件初始化成功")
            return True
            
        except Exception as e:
            logging.error(f"语音识别组件初始化失败: {e}")
            return False
    
    def _calibrate_noise(self):
        """校准环境噪音"""
        try:
            with self.microphone as source:
                logging.info("正在校准环境噪音，请保持安静...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logging.info(f"环境噪音校准完成，阈值: {self.recognizer.energy_threshold}")
        except Exception as e:
            logging.error(f"环境噪音校准失败: {e}")
    
    def set_callbacks(self, 
                     on_speech_start: Callable = None,
                     on_speech_end: Callable = None,
                     on_text_recognized: Callable[[str], None] = None,
                     on_error: Callable[[str], None] = None):
        """设置回调函数"""
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_text_recognized = on_text_recognized
        self.on_error = on_error
    
    def start_continuous_listening(self):
        """开始连续监听模式"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            if self.on_error:
                self.on_error("语音识别功能不可用")
            return False
        
        if self.is_listening:
            logging.warning("已经在监听中")
            return True
        
        self.is_listening = True
        
        # 在新线程中开始监听
        threading.Thread(target=self._continuous_listen_thread, daemon=True).start()
        
        logging.info("开始连续语音监听")
        return True
    
    def stop_continuous_listening(self):
        """停止连续监听"""
        self.is_listening = False
        self.is_recording = False
        logging.info("停止连续语音监听")
    
    def _continuous_listen_thread(self):
        """连续监听线程"""
        try:
            with self.microphone as source:
                while self.is_listening:
                    try:
                        # 监听语音（优化超时设置）
                        audio = self.recognizer.listen(
                            source,
                            timeout=self.listen_timeout,  # 使用更短的超时时间
                            phrase_time_limit=self.max_recording_time
                        )
                        
                        if self.is_listening:  # 确保还在监听状态
                            # 在新线程中处理识别
                            threading.Thread(
                                target=self._process_audio, 
                                args=(audio,), 
                                daemon=True
                            ).start()
                    
                    except sr.WaitTimeoutError:
                        # 超时是正常的，继续监听
                        continue
                    except Exception as e:
                        logging.error(f"监听过程中出错: {e}")
                        if self.on_error:
                            self.on_error(f"监听错误: {e}")
                        break
        
        except Exception as e:
            logging.error(f"连续监听线程异常: {e}")
            if self.on_error:
                self.on_error(f"监听线程异常: {e}")
    
    def _process_audio(self, audio):
        """处理音频数据"""
        try:
            # 通知开始语音处理
            if self.on_speech_start:
                self.on_speech_start()
            
            # 使用Google语音识别
            text = self._recognize_with_google(audio)
            
            if text:
                logging.info(f"识别到文本: {text}")
                if self.on_text_recognized:
                    self.on_text_recognized(text)
            
            # 通知语音处理结束
            if self.on_speech_end:
                self.on_speech_end()
        
        except Exception as e:
            logging.error(f"音频处理失败: {e}")
            if self.on_error:
                self.on_error(f"识别失败: {e}")
            
            if self.on_speech_end:
                self.on_speech_end()
    
    def _recognize_with_google(self, audio) -> Optional[str]:
        """使用Google语音识别"""
        try:
            # 尝试中文识别
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            return text
        except sr.UnknownValueError:
            # 尝试英文识别
            try:
                text = self.recognizer.recognize_google(audio, language='en-US')
                return text
            except sr.UnknownValueError:
                logging.debug("无法识别语音内容")
                return None
        except sr.RequestError as e:
            logging.error(f"Google语音识别服务错误: {e}")
            # 尝试离线识别
            return self._recognize_offline(audio)
        except Exception as e:
            logging.error(f"语音识别异常: {e}")
            return None
    
    def _recognize_offline(self, audio) -> Optional[str]:
        """离线语音识别（备用方案）"""
        try:
            # 使用Windows语音识别
            text = self.recognizer.recognize_sphinx(audio)
            return text
        except Exception as e:
            logging.debug(f"离线识别失败: {e}")
            return None
    
    def record_once(self, timeout: float = 5.0) -> Optional[str]:
        """单次录音识别"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return None
        
        try:
            with self.microphone as source:
                logging.info("请开始说话...")
                if self.on_speech_start:
                    self.on_speech_start()
                
                # 录音
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=self.max_recording_time)
                
                logging.info("录音完成，正在识别...")
                
                # 识别
                text = self._recognize_with_google(audio)
                
                if self.on_speech_end:
                    self.on_speech_end()
                
                return text
        
        except sr.WaitTimeoutError:
            logging.warning("录音超时")
            if self.on_error:
                self.on_error("录音超时，请重试")
            return None
        except Exception as e:
            logging.error(f"单次录音识别失败: {e}")
            if self.on_error:
                self.on_error(f"录音失败: {e}")
            return None
    
    def is_microphone_available(self) -> bool:
        """检查麦克风是否可用"""
        try:
            if not SPEECH_RECOGNITION_AVAILABLE:
                return False
            
            # 尝试访问麦克风
            with sr.Microphone() as source:
                pass
            return True
        except Exception as e:
            logging.error(f"麦克风不可用: {e}")
            return False
    
    def get_microphone_list(self) -> list:
        """获取可用麦克风列表"""
        try:
            if not SPEECH_RECOGNITION_AVAILABLE:
                return []
            
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            logging.error(f"获取麦克风列表失败: {e}")
            return []
    
    def test_microphone(self) -> Dict[str, Any]:
        """测试麦克风功能"""
        result = {
            "available": False,
            "microphone_count": 0,
            "test_recording": False,
            "recognition_test": False,
            "error": None
        }
        
        try:
            # 检查语音识别可用性
            if not SPEECH_RECOGNITION_AVAILABLE:
                result["error"] = "语音识别模块不可用"
                return result
            
            # 获取麦克风列表
            microphones = self.get_microphone_list()
            result["microphone_count"] = len(microphones)
            
            if len(microphones) == 0:
                result["error"] = "未找到可用麦克风"
                return result
            
            # 测试麦克风访问
            with sr.Microphone() as source:
                result["available"] = True
                
                # 测试录音
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                result["test_recording"] = True
                
                # 简单识别测试
                logging.info("麦克风测试：请说 '测试'")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=2)
                
                try:
                    text = self.recognizer.recognize_google(audio, language='zh-CN')
                    result["recognition_test"] = True
                    result["test_text"] = text
                except:
                    result["recognition_test"] = False
                    result["test_text"] = "识别失败"
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """获取语音识别状态"""
        return {
            "available": SPEECH_RECOGNITION_AVAILABLE,
            "vad_available": VAD_AVAILABLE,
            "is_listening": self.is_listening,
            "is_recording": self.is_recording,
            "microphone_available": self.is_microphone_available(),
            "sample_rate": self.sample_rate,
            "energy_threshold": self.recognizer.energy_threshold if self.recognizer else None
        }

# 全局语音识别管理器实例
speech_recognition_manager = SpeechRecognitionManager()

def get_speech_recognition_manager() -> SpeechRecognitionManager:
    """获取语音识别管理器实例"""
    return speech_recognition_manager
