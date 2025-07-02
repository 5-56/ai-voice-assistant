#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时语音对话管理器
整合STT + LLM + TTS，实现完整的实时语音对话功能
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from enum import Enum

class VoiceMode(Enum):
    """语音模式"""
    DISABLED = "disabled"           # 禁用语音
    PUSH_TO_TALK = "push_to_talk"  # 按键说话
    CONTINUOUS = "continuous"       # 连续监听
    MIXED = "mixed"                # 混合模式（文本+语音）

class ConversationState(Enum):
    """对话状态"""
    IDLE = "idle"                  # 空闲
    LISTENING = "listening"        # 监听中
    PROCESSING = "processing"      # 处理中
    SPEAKING = "speaking"          # 播放中
    INTERRUPTED = "interrupted"    # 被打断

class RealtimeVoiceManager:
    """实时语音对话管理器"""
    
    def __init__(self):
        # 组件引用
        self.stt_manager = None
        self.tts_manager = None
        self.vad_detector = None
        self.deepseek_client = None
        self.conversation_manager = None
        
        # 状态管理
        self.voice_mode = VoiceMode.DISABLED
        self.conversation_state = ConversationState.IDLE
        self.is_active = False
        self.is_interruption_enabled = True
        
        # 配置参数
        self.auto_response = True
        self.interrupt_threshold = 0.5  # 打断检测阈值（秒）
        self.response_delay = 0.3       # 响应延迟（秒）
        self.max_silence_time = 3.0     # 最大静音时间（秒）
        
        # 回调函数
        self.on_state_changed = None
        self.on_text_input = None
        self.on_text_output = None
        self.on_error = None
        
        # 内部状态
        self._current_audio_task = None
        self._interrupt_requested = False
        self._last_user_input_time = None
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化组件"""
        try:
            # 导入并初始化组件
            from speech_recognition_manager import get_speech_recognition_manager
            from voice_activity_detector import get_voice_activity_detector
            from smart_tts_manager import get_smart_tts_manager
            from deepseek_client import get_deepseek_client
            from conversation_manager import get_conversation_manager
            
            self.stt_manager = get_speech_recognition_manager()
            self.vad_detector = get_voice_activity_detector()
            self.tts_manager = get_smart_tts_manager()
            self.deepseek_client = get_deepseek_client()
            self.conversation_manager = get_conversation_manager()
            
            # 设置回调
            self._setup_callbacks()
            
            logging.info("实时语音对话管理器初始化成功")
            
        except Exception as e:
            logging.error(f"实时语音对话管理器初始化失败: {e}")
    
    def _setup_callbacks(self):
        """设置组件回调"""
        # STT回调
        self.stt_manager.set_callbacks(
            on_speech_start=self._on_stt_speech_start,
            on_speech_end=self._on_stt_speech_end,
            on_text_recognized=self._on_text_recognized,
            on_error=self._on_stt_error
        )
        
        # VAD回调
        self.vad_detector.set_callbacks(
            on_speech_start=self._on_vad_speech_start,
            on_speech_end=self._on_vad_speech_end,
            on_speech_detected=self._on_vad_speech_detected,
            on_silence_detected=self._on_vad_silence_detected
        )
    
    def set_voice_mode(self, mode: VoiceMode):
        """设置语音模式"""
        old_mode = self.voice_mode
        self.voice_mode = mode
        
        logging.info(f"语音模式切换: {old_mode.value} -> {mode.value}")
        
        # 根据模式调整行为
        if mode == VoiceMode.DISABLED:
            self.stop_voice_interaction()
        elif mode == VoiceMode.CONTINUOUS:
            self.start_continuous_listening()
        elif mode == VoiceMode.PUSH_TO_TALK:
            self.stop_continuous_listening()
        
        self._notify_state_change()
    
    def start_voice_interaction(self):
        """启动语音交互"""
        if self.is_active:
            logging.warning("语音交互已经激活")
            return True
        
        try:
            self.is_active = True
            self._set_conversation_state(ConversationState.IDLE)
            
            # 根据模式启动相应功能
            if self.voice_mode == VoiceMode.CONTINUOUS:
                self.start_continuous_listening()
            
            logging.info("语音交互已启动")
            return True
            
        except Exception as e:
            logging.error(f"启动语音交互失败: {e}")
            self.is_active = False
            return False
    
    def stop_voice_interaction(self):
        """停止语音交互"""
        self.is_active = False
        
        # 停止所有组件
        self.stop_continuous_listening()
        self.stop_current_speech()
        
        self._set_conversation_state(ConversationState.IDLE)
        
        logging.info("语音交互已停止")
    
    def start_continuous_listening(self):
        """开始连续监听"""
        if self.voice_mode not in [VoiceMode.CONTINUOUS, VoiceMode.MIXED]:
            return False

        try:
            # 检查VAD是否已在监控，避免重复启动
            if not self.vad_detector.is_monitoring:
                self.vad_detector.start_monitoring()

            # 检查STT是否已在监听，避免重复启动
            if not self.stt_manager.is_listening:
                self.stt_manager.start_continuous_listening()

            self._set_conversation_state(ConversationState.LISTENING)

            logging.info("连续监听已启动")
            return True

        except Exception as e:
            logging.error(f"启动连续监听失败: {e}")
            return False
    
    def stop_continuous_listening(self):
        """停止连续监听"""
        try:
            self.vad_detector.stop_monitoring()
            self.stt_manager.stop_continuous_listening()
            
            if self.conversation_state == ConversationState.LISTENING:
                self._set_conversation_state(ConversationState.IDLE)
            
            logging.info("连续监听已停止")
            
        except Exception as e:
            logging.error(f"停止连续监听失败: {e}")
    
    def record_once(self, timeout: float = 5.0) -> Optional[str]:
        """单次录音（按键说话模式）"""
        if self.voice_mode != VoiceMode.PUSH_TO_TALK:
            return None
        
        try:
            self._set_conversation_state(ConversationState.LISTENING)
            
            # 单次录音识别
            text = self.stt_manager.record_once(timeout)
            
            if text:
                self._process_user_input(text)
            
            return text
            
        except Exception as e:
            logging.error(f"单次录音失败: {e}")
            return None
        finally:
            if self.conversation_state == ConversationState.LISTENING:
                self._set_conversation_state(ConversationState.IDLE)
    
    def process_text_input(self, text: str):
        """处理文本输入"""
        if not text.strip():
            return
        
        self._process_user_input(text)
    
    def _process_user_input(self, text: str):
        """处理用户输入（文本或语音）"""
        try:
            self._last_user_input_time = time.time()
            
            # 如果正在播放语音，立即停止（打断功能）
            if self.conversation_state == ConversationState.SPEAKING and self.is_interruption_enabled:
                self.interrupt_current_speech()
            
            # 通知文本输入
            if self.on_text_input:
                self.on_text_input(text)
            
            # 设置处理状态
            self._set_conversation_state(ConversationState.PROCESSING)
            
            # 在新线程中处理AI响应
            threading.Thread(target=self._process_ai_response, args=(text,), daemon=True).start()
            
        except Exception as e:
            logging.error(f"处理用户输入失败: {e}")
            if self.on_error:
                self.on_error(f"处理输入失败: {e}")
    
    def _process_ai_response(self, user_text: str):
        """处理AI响应"""
        try:
            # 添加用户消息到对话历史
            self.conversation_manager.add_message("user", user_text)
            
            # 获取对话历史
            messages = self.conversation_manager.get_conversation_messages()
            
            # 调用AI模型
            response = self.deepseek_client.chat_completion(messages)
            
            if response["success"]:
                ai_text = response["content"]
                token_count = response.get("usage", {}).get("total_tokens", 0)
                
                # 添加AI回复到对话历史
                self.conversation_manager.add_message("assistant", ai_text, token_count)
                
                # 通知文本输出
                if self.on_text_output:
                    self.on_text_output(ai_text)
                
                # 如果启用自动响应，播放语音
                if self.auto_response:
                    self._speak_response(ai_text)
                else:
                    self._set_conversation_state(ConversationState.IDLE)
            
            else:
                error_msg = f"AI响应失败: {response['error']}"
                logging.error(error_msg)
                if self.on_error:
                    self.on_error(error_msg)
                self._set_conversation_state(ConversationState.IDLE)
        
        except Exception as e:
            error_msg = f"处理AI响应异常: {e}"
            logging.error(error_msg)
            if self.on_error:
                self.on_error(error_msg)
            self._set_conversation_state(ConversationState.IDLE)
    
    def _speak_response(self, text: str):
        """播放AI响应"""
        try:
            self._set_conversation_state(ConversationState.SPEAKING)
            
            # 异步播放语音
            def speak_callback(status_info):
                status = status_info.get("status", "")
                if status == "completed":
                    self._on_speech_completed()
                elif status == "error":
                    self._on_speech_error(status_info.get("message", ""))
            
            # 启动语音播放任务
            self._current_audio_task = threading.Thread(
                target=self._speak_async,
                args=(text, speak_callback),
                daemon=True
            )
            self._current_audio_task.start()
            
        except Exception as e:
            logging.error(f"播放AI响应失败: {e}")
            self._set_conversation_state(ConversationState.IDLE)
    
    def _speak_async(self, text: str, callback: Callable):
        """异步语音播放"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                self.tts_manager.speak_text_async(text, callback)
            )
        except Exception as e:
            logging.error(f"异步语音播放失败: {e}")
            callback({"status": "error", "message": str(e)})
    
    def interrupt_current_speech(self):
        """打断当前语音播放"""
        if self.conversation_state == ConversationState.SPEAKING:
            self._interrupt_requested = True
            self.tts_manager.stop_speaking()
            self._set_conversation_state(ConversationState.INTERRUPTED)
            logging.info("语音播放被打断")
    
    def stop_current_speech(self):
        """停止当前语音播放"""
        if self.conversation_state in [ConversationState.SPEAKING, ConversationState.INTERRUPTED]:
            self.tts_manager.stop_speaking()
            self._set_conversation_state(ConversationState.IDLE)
    
    def _set_conversation_state(self, state: ConversationState):
        """设置对话状态"""
        old_state = self.conversation_state
        self.conversation_state = state
        
        if old_state != state:
            logging.debug(f"对话状态变化: {old_state.value} -> {state.value}")
            self._notify_state_change()
    
    def _notify_state_change(self):
        """通知状态变化"""
        if self.on_state_changed:
            try:
                self.on_state_changed(self.get_status())
            except Exception as e:
                logging.error(f"状态变化通知失败: {e}")
    
    # VAD回调方法
    def _on_vad_speech_start(self):
        """VAD检测到语音开始"""
        if self.is_interruption_enabled and self.conversation_state == ConversationState.SPEAKING:
            # 检测到用户开始说话，打断AI播放
            self.interrupt_current_speech()
    
    def _on_vad_speech_end(self):
        """VAD检测到语音结束"""
        pass
    
    def _on_vad_speech_detected(self):
        """VAD检测到语音活动"""
        pass
    
    def _on_vad_silence_detected(self):
        """VAD检测到静音"""
        pass
    
    # STT回调方法
    def _on_stt_speech_start(self):
        """STT开始录音"""
        if self.conversation_state == ConversationState.LISTENING:
            logging.debug("开始录音识别")
    
    def _on_stt_speech_end(self):
        """STT录音结束"""
        if self.conversation_state == ConversationState.LISTENING:
            logging.debug("录音识别结束")
    
    def _on_text_recognized(self, text: str):
        """STT识别到文本"""
        if self.is_active and text.strip():
            logging.info(f"识别到语音: {text}")
            self._process_user_input(text)
    
    def _on_stt_error(self, error: str):
        """STT错误"""
        logging.error(f"语音识别错误: {error}")
        if self.on_error:
            self.on_error(f"语音识别错误: {error}")
    
    # TTS回调方法
    def _on_speech_completed(self):
        """语音播放完成"""
        if self.conversation_state in [ConversationState.SPEAKING, ConversationState.INTERRUPTED]:
            self._set_conversation_state(ConversationState.IDLE)
            
            # 如果是连续模式，重新开始监听
            if self.voice_mode == VoiceMode.CONTINUOUS and self.is_active:
                self._set_conversation_state(ConversationState.LISTENING)
    
    def _on_speech_error(self, error: str):
        """语音播放错误"""
        logging.error(f"语音播放错误: {error}")
        self._set_conversation_state(ConversationState.IDLE)
        if self.on_error:
            self.on_error(f"语音播放错误: {error}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "is_active": self.is_active,
            "voice_mode": self.voice_mode.value,
            "conversation_state": self.conversation_state.value,
            "is_interruption_enabled": self.is_interruption_enabled,
            "auto_response": self.auto_response,
            "stt_available": self.stt_manager.get_status()["available"] if self.stt_manager else False,
            "vad_available": self.vad_detector.get_status()["available"] if self.vad_detector else False,
            "tts_available": self.tts_manager.get_status()["edge_tts_available"] if self.tts_manager else False,
            "is_speaking_detected": self.vad_detector.is_speech_active() if self.vad_detector else False
        }
    
    def set_callbacks(self,
                     on_state_changed: Callable = None,
                     on_text_input: Callable[[str], None] = None,
                     on_text_output: Callable[[str], None] = None,
                     on_error: Callable[[str], None] = None):
        """设置回调函数"""
        self.on_state_changed = on_state_changed
        self.on_text_input = on_text_input
        self.on_text_output = on_text_output
        self.on_error = on_error

# 全局实时语音管理器实例
realtime_voice_manager = RealtimeVoiceManager()

def get_realtime_voice_manager() -> RealtimeVoiceManager:
    """获取实时语音管理器实例"""
    return realtime_voice_manager
