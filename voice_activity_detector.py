#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音活动检测器（VAD - Voice Activity Detection）
实现实时语音活动检测，支持对话打断功能
"""

import asyncio
import logging
import threading
import time
import queue
import numpy as np
from typing import Optional, Callable, Dict, Any
import struct

# 音频处理相关导入
try:
    import pyaudio
    import webrtcvad
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    logging.warning("音频处理模块不可用，请安装: pip install pyaudio webrtcvad")

class VoiceActivityDetector:
    """语音活动检测器"""
    
    def __init__(self):
        self.is_monitoring = False
        self.is_speaking_detected = False
        self.audio_stream = None
        self.vad = None
        
        # 音频参数
        self.sample_rate = 16000  # WebRTC VAD 支持的采样率
        self.channels = 1
        self.chunk_duration = 0.03  # 30ms chunks (WebRTC VAD 要求)
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.format = pyaudio.paInt16
        
        # VAD参数
        self.vad_mode = 2  # 0-3, 3最敏感
        self.speech_threshold = 0.6  # 语音检测阈值
        self.silence_threshold = 1.0  # 静音阈值（秒）
        self.min_speech_duration = 0.3  # 最小语音持续时间（秒）
        
        # 状态跟踪
        self.speech_frames = []
        self.silence_frames = 0
        self.speech_start_time = None
        self.last_speech_time = None
        
        # 回调函数
        self.on_speech_start = None
        self.on_speech_end = None
        self.on_speech_detected = None
        self.on_silence_detected = None
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化VAD组件"""
        if not AUDIO_AVAILABLE:
            logging.error("音频处理功能不可用")
            return False
        
        try:
            # 初始化WebRTC VAD
            self.vad = webrtcvad.Vad(self.vad_mode)
            
            # 初始化PyAudio
            self.audio = pyaudio.PyAudio()
            
            logging.info("VAD组件初始化成功")
            return True
            
        except Exception as e:
            logging.error(f"VAD组件初始化失败: {e}")
            return False
    
    def set_callbacks(self,
                     on_speech_start: Callable = None,
                     on_speech_end: Callable = None,
                     on_speech_detected: Callable = None,
                     on_silence_detected: Callable = None):
        """设置回调函数"""
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_speech_detected = on_speech_detected
        self.on_silence_detected = on_silence_detected
    
    def start_monitoring(self):
        """开始语音活动监控"""
        if not AUDIO_AVAILABLE:
            logging.error("音频处理功能不可用")
            return False
        
        if self.is_monitoring:
            logging.warning("VAD已在监控中")
            return True
        
        try:
            # 打开音频流
            self.audio_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.is_monitoring = True
            self.audio_stream.start_stream()
            
            logging.info("VAD监控已启动")
            return True
            
        except Exception as e:
            logging.error(f"启动VAD监控失败: {e}")
            return False
    
    def stop_monitoring(self):
        """停止语音活动监控"""
        self.is_monitoring = False
        
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            except Exception as e:
                logging.error(f"停止音频流失败: {e}")
        
        # 重置状态
        self.is_speaking_detected = False
        self.speech_frames.clear()
        self.silence_frames = 0
        self.speech_start_time = None
        self.last_speech_time = None
        
        logging.info("VAD监控已停止")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频流回调函数"""
        if not self.is_monitoring:
            return (None, pyaudio.paComplete)
        
        try:
            # 处理音频数据
            self._process_audio_chunk(in_data)
        except Exception as e:
            logging.error(f"音频回调处理失败: {e}")
        
        return (None, pyaudio.paContinue)
    
    def _process_audio_chunk(self, audio_data):
        """处理音频块"""
        try:
            # 确保音频数据长度正确
            if len(audio_data) != self.chunk_size * 2:  # 16-bit = 2 bytes per sample
                return
            
            # 使用WebRTC VAD检测语音
            is_speech = self.vad.is_speech(audio_data, self.sample_rate)
            
            current_time = time.time()
            
            if is_speech:
                # 检测到语音
                self._handle_speech_detected(current_time)
            else:
                # 检测到静音
                self._handle_silence_detected(current_time)
        
        except Exception as e:
            logging.debug(f"音频块处理失败: {e}")
    
    def _handle_speech_detected(self, current_time):
        """处理检测到语音"""
        self.silence_frames = 0
        self.last_speech_time = current_time
        
        if not self.is_speaking_detected:
            # 语音开始
            self.is_speaking_detected = True
            self.speech_start_time = current_time
            
            logging.debug("检测到语音开始")
            
            if self.on_speech_start:
                threading.Thread(target=self.on_speech_start, daemon=True).start()
        
        # 持续语音检测回调
        if self.on_speech_detected:
            threading.Thread(target=self.on_speech_detected, daemon=True).start()
    
    def _handle_silence_detected(self, current_time):
        """处理检测到静音"""
        self.silence_frames += 1
        
        # 计算静音持续时间
        silence_duration = self.silence_frames * self.chunk_duration
        
        if self.is_speaking_detected and silence_duration >= self.silence_threshold:
            # 语音结束
            speech_duration = current_time - self.speech_start_time if self.speech_start_time else 0
            
            if speech_duration >= self.min_speech_duration:
                # 有效语音结束
                self.is_speaking_detected = False
                
                logging.debug(f"检测到语音结束，持续时间: {speech_duration:.2f}秒")
                
                if self.on_speech_end:
                    threading.Thread(target=self.on_speech_end, daemon=True).start()
            else:
                # 语音太短，忽略
                self.is_speaking_detected = False
                logging.debug(f"语音太短被忽略: {speech_duration:.2f}秒")
        
        # 持续静音检测回调
        if not self.is_speaking_detected and self.on_silence_detected:
            threading.Thread(target=self.on_silence_detected, daemon=True).start()
    
    def is_speech_active(self) -> bool:
        """检查当前是否有语音活动"""
        return self.is_speaking_detected
    
    def get_speech_duration(self) -> float:
        """获取当前语音持续时间"""
        if self.is_speaking_detected and self.speech_start_time:
            return time.time() - self.speech_start_time
        return 0.0
    
    def get_silence_duration(self) -> float:
        """获取当前静音持续时间"""
        if self.last_speech_time:
            return time.time() - self.last_speech_time
        return 0.0
    
    def set_sensitivity(self, mode: int):
        """设置VAD敏感度
        
        Args:
            mode: 0-3, 0最不敏感，3最敏感
        """
        if 0 <= mode <= 3:
            self.vad_mode = mode
            if self.vad:
                self.vad = webrtcvad.Vad(self.vad_mode)
            logging.info(f"VAD敏感度设置为: {mode}")
        else:
            logging.warning(f"无效的VAD敏感度: {mode}")
    
    def set_thresholds(self, 
                      speech_threshold: float = None,
                      silence_threshold: float = None,
                      min_speech_duration: float = None):
        """设置检测阈值"""
        if speech_threshold is not None:
            self.speech_threshold = speech_threshold
        
        if silence_threshold is not None:
            self.silence_threshold = silence_threshold
        
        if min_speech_duration is not None:
            self.min_speech_duration = min_speech_duration
        
        logging.info(f"VAD阈值更新: speech={self.speech_threshold}, "
                    f"silence={self.silence_threshold}, min_duration={self.min_speech_duration}")
    
    def test_microphone(self) -> Dict[str, Any]:
        """测试麦克风和VAD功能"""
        result = {
            "microphone_available": False,
            "vad_available": False,
            "test_duration": 5.0,
            "speech_detected": False,
            "speech_count": 0,
            "error": None
        }
        
        if not AUDIO_AVAILABLE:
            result["error"] = "音频处理模块不可用"
            return result
        
        try:
            # 测试麦克风访问
            test_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            result["microphone_available"] = True
            
            # 测试VAD
            if self.vad:
                result["vad_available"] = True
                
                # 进行5秒测试
                test_start = time.time()
                speech_count = 0
                
                while time.time() - test_start < result["test_duration"]:
                    try:
                        audio_data = test_stream.read(self.chunk_size, exception_on_overflow=False)
                        
                        if len(audio_data) == self.chunk_size * 2:
                            is_speech = self.vad.is_speech(audio_data, self.sample_rate)
                            if is_speech:
                                speech_count += 1
                                result["speech_detected"] = True
                    
                    except Exception as e:
                        logging.debug(f"VAD测试中的音频处理错误: {e}")
                        continue
                
                result["speech_count"] = speech_count
            
            test_stream.stop_stream()
            test_stream.close()
        
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """获取VAD状态"""
        return {
            "available": AUDIO_AVAILABLE,
            "is_monitoring": self.is_monitoring,
            "is_speaking_detected": self.is_speaking_detected,
            "vad_mode": self.vad_mode,
            "sample_rate": self.sample_rate,
            "chunk_duration": self.chunk_duration,
            "speech_threshold": self.speech_threshold,
            "silence_threshold": self.silence_threshold,
            "min_speech_duration": self.min_speech_duration,
            "current_speech_duration": self.get_speech_duration(),
            "current_silence_duration": self.get_silence_duration()
        }
    
    def __del__(self):
        """析构函数"""
        self.stop_monitoring()
        if hasattr(self, 'audio'):
            try:
                self.audio.terminate()
            except:
                pass

# 全局VAD实例
voice_activity_detector = VoiceActivityDetector()

def get_voice_activity_detector() -> VoiceActivityDetector:
    """获取语音活动检测器实例"""
    return voice_activity_detector
