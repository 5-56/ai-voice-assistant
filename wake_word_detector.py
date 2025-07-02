#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音唤醒词检测器
实现"你好文犀"、"文犀出来"等唤醒词的检测功能
"""

import asyncio
import logging
import threading
import time
import queue
import re
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path

# 语音识别相关导入
try:
    import speech_recognition as sr
    import pyaudio
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logging.warning("语音识别模块不可用，请安装: pip install SpeechRecognition pyaudio")

class WakeWordDetector:
    """语音唤醒词检测器"""
    
    def __init__(self):
        self.is_active = False
        self.is_listening = False
        self.recognizer = None
        self.microphone = None
        self.audio_queue = queue.Queue()
        self.detection_thread = None
        
        # 唤醒词配置
        self.wake_words = [
            # 主要唤醒词
            "你好文犀", "文犀你好", "嗨文犀", "文犀",
            "文犀出来", "文犀醒醒", "文犀开始",
            "小文", "文犀助手", "文犀同学",
            
            # 英文唤醒词
            "hey wenxi", "hello wenxi", "wenxi",
            "wake up wenxi", "wenxi come out",
            
            # 变体和容错
            "文西", "文溪", "文希", "文喜",
            "你好文西", "文西出来", "嗨文西"
        ]
        
        # 唤醒词模式（支持模糊匹配）
        self.wake_patterns = [
            r".*你好.*文[犀西溪希喜].*",
            r".*文[犀西溪希喜].*你好.*",
            r".*文[犀西溪希喜].*出来.*",
            r".*文[犀西溪希喜].*醒醒.*",
            r".*文[犀西溪希喜].*开始.*",
            r".*嗨.*文[犀西溪希喜].*",
            r".*小文.*",
            r".*文[犀西溪希喜]助手.*",
            r".*文[犀西溪希喜]同学.*",
            r".*hey.*wenxi.*",
            r".*hello.*wenxi.*",
            r".*wake.*up.*wenxi.*",
            r".*wenxi.*come.*out.*"
        ]
        
        # 配置参数
        self.sample_rate = 16000
        self.chunk_duration = 0.5  # 500ms chunks for wake word detection
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.detection_timeout = 3.0  # 检测超时时间
        self.confidence_threshold = 0.6  # 置信度阈值
        
        # 回调函数
        self.on_wake_word_detected: Optional[Callable[[str], None]] = None
        self.on_detection_error: Optional[Callable[[str], None]] = None
        
        # 统计信息
        self.detection_count = 0
        self.last_detection_time = 0
        self.false_positive_count = 0
        
        # 初始化组件
        self._initialize_components()
        
        logging.info("语音唤醒词检测器初始化完成")
    
    def _initialize_components(self):
        """初始化语音识别组件"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logging.error("语音识别模块不可用")
            return
        
        try:
            # 初始化识别器
            self.recognizer = sr.Recognizer()
            
            # 优化识别器参数
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.5  # 减少暂停检测时间
            self.recognizer.phrase_threshold = 0.2
            self.recognizer.non_speaking_duration = 0.3
            
            # 初始化麦克风
            self.microphone = sr.Microphone(sample_rate=self.sample_rate, chunk_size=self.chunk_size)
            
            # 环境噪音校准
            with self.microphone as source:
                logging.info("正在校准环境噪音...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logging.info(f"环境噪音校准完成，能量阈值: {self.recognizer.energy_threshold}")
            
        except Exception as e:
            logging.error(f"初始化语音识别组件失败: {e}")
    
    def start_detection(self):
        """开始唤醒词检测"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logging.error("语音识别模块不可用，无法启动唤醒词检测")
            return False
        
        if self.is_active:
            logging.warning("唤醒词检测已经在运行")
            return True
        
        try:
            self.is_active = True
            self.is_listening = True
            
            # 启动检测线程
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            
            logging.info("语音唤醒词检测已启动")
            return True
            
        except Exception as e:
            logging.error(f"启动唤醒词检测失败: {e}")
            self.is_active = False
            return False
    
    def stop_detection(self):
        """停止唤醒词检测"""
        if not self.is_active:
            return
        
        self.is_active = False
        self.is_listening = False
        
        # 等待检测线程结束
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=2)
        
        logging.info("语音唤醒词检测已停止")
    
    def _detection_loop(self):
        """检测循环"""
        logging.info("唤醒词检测循环开始")
        
        while self.is_active:
            try:
                # 监听音频
                with self.microphone as source:
                    # 短时间监听，避免阻塞
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # 识别语音
                text = self._recognize_audio(audio)
                
                if text:
                    logging.debug(f"识别到语音: {text}")
                    
                    # 检测唤醒词
                    if self._is_wake_word(text):
                        self._handle_wake_word_detected(text)
                
            except sr.WaitTimeoutError:
                # 超时是正常的，继续监听
                continue
            except sr.UnknownValueError:
                # 无法识别语音，继续监听
                continue
            except Exception as e:
                logging.error(f"唤醒词检测出错: {e}")
                if self.on_detection_error:
                    self.on_detection_error(str(e))
                time.sleep(0.5)  # 短暂休息后继续
        
        logging.info("唤醒词检测循环结束")
    
    def _recognize_audio(self, audio) -> Optional[str]:
        """识别音频为文本"""
        try:
            # 使用Google语音识别（免费）
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            return text.lower().strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logging.error(f"语音识别服务错误: {e}")
            return None
        except Exception as e:
            logging.error(f"语音识别失败: {e}")
            return None
    
    def _is_wake_word(self, text: str) -> bool:
        """检测是否为唤醒词"""
        if not text:
            return False
        
        text = text.lower().strip()
        
        # 精确匹配
        for wake_word in self.wake_words:
            if wake_word.lower() in text:
                logging.info(f"检测到唤醒词（精确匹配）: {wake_word} in '{text}'")
                return True
        
        # 模式匹配
        for pattern in self.wake_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logging.info(f"检测到唤醒词（模式匹配）: {pattern} matches '{text}'")
                return True
        
        return False
    
    def _handle_wake_word_detected(self, text: str):
        """处理检测到唤醒词"""
        current_time = time.time()
        
        # 防止重复触发（2秒内只触发一次）
        if current_time - self.last_detection_time < 2.0:
            logging.debug("忽略重复的唤醒词检测")
            return
        
        self.last_detection_time = current_time
        self.detection_count += 1
        
        logging.info(f"🎤 检测到唤醒词: '{text}' (第{self.detection_count}次)")
        
        # 调用回调函数
        if self.on_wake_word_detected:
            try:
                self.on_wake_word_detected(text)
            except Exception as e:
                logging.error(f"唤醒词回调函数执行失败: {e}")
    
    def add_wake_word(self, word: str):
        """添加自定义唤醒词"""
        if word and word not in self.wake_words:
            self.wake_words.append(word.lower())
            logging.info(f"添加唤醒词: {word}")
    
    def remove_wake_word(self, word: str):
        """移除唤醒词"""
        if word.lower() in self.wake_words:
            self.wake_words.remove(word.lower())
            logging.info(f"移除唤醒词: {word}")
    
    def get_wake_words(self) -> List[str]:
        """获取所有唤醒词"""
        return self.wake_words.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """获取检测器状态"""
        return {
            "is_active": self.is_active,
            "is_listening": self.is_listening,
            "detection_count": self.detection_count,
            "last_detection_time": self.last_detection_time,
            "wake_words_count": len(self.wake_words),
            "speech_recognition_available": SPEECH_RECOGNITION_AVAILABLE
        }

# 全局实例
wake_word_detector = WakeWordDetector()

def get_wake_word_detector() -> WakeWordDetector:
    """获取语音唤醒词检测器实例"""
    return wake_word_detector
