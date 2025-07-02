#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能TTS管理器
复用现有TTS系统，支持智能语音朗读
"""

import asyncio
import logging
import re
import threading
import time
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import win32com.client
import edge_tts
from config_manager import get_config

# 导入现有的音频播放器
try:
    from audio_player import play_audio_file, stop_audio
    AUDIO_PLAYER_AVAILABLE = True
except ImportError:
    AUDIO_PLAYER_AVAILABLE = False
    logging.warning("音频播放器模块不可用")

class SmartTTSManager:
    """智能TTS管理器"""
    
    def __init__(self):
        self.config = get_config()
        self.is_speaking = False
        self.current_task = None
        self.speaker = None  # Windows TTS speaker
        self.edge_voices = []
        self._initialize_windows_tts()
        self._load_edge_voices_async()
    
    def _initialize_windows_tts(self) -> bool:
        """初始化Windows TTS"""
        try:
            self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voices = self.speaker.GetVoices()
            logging.info(f"Windows TTS初始化成功，找到 {voices.Count} 个语音")
            return True
        except Exception as e:
            logging.error(f"Windows TTS初始化失败: {e}")
            self.speaker = None
            return False
    
    def _load_edge_voices_async(self):
        """异步加载Edge TTS语音列表"""
        def load_voices():
            try:
                # 使用默认语音列表（避免网络请求延迟）
                self.edge_voices = [
                    {'Name': 'zh-CN-XiaoxiaoNeural', 'DisplayName': '晓晓', 'Gender': 'Female', 'Locale': 'zh-CN'},
                    {'Name': 'zh-CN-YunxiNeural', 'DisplayName': '云希', 'Gender': 'Male', 'Locale': 'zh-CN'},
                    {'Name': 'zh-CN-YunyangNeural', 'DisplayName': '云扬', 'Gender': 'Male', 'Locale': 'zh-CN'},
                    {'Name': 'zh-CN-XiaoyiNeural', 'DisplayName': '晓伊', 'Gender': 'Female', 'Locale': 'zh-CN'},
                    {'Name': 'en-US-JennyNeural', 'DisplayName': 'Jenny', 'Gender': 'Female', 'Locale': 'en-US'},
                    {'Name': 'en-US-GuyNeural', 'DisplayName': 'Guy', 'Gender': 'Male', 'Locale': 'en-US'},
                    {'Name': 'en-US-AriaNeural', 'DisplayName': 'Aria', 'Gender': 'Female', 'Locale': 'en-US'},
                    {'Name': 'en-GB-SoniaNeural', 'DisplayName': 'Sonia', 'Gender': 'Female', 'Locale': 'en-GB'},
                ]
                logging.info(f"加载了 {len(self.edge_voices)} 个Edge TTS语音")
            except Exception as e:
                logging.error(f"加载Edge TTS语音失败: {e}")
        
        threading.Thread(target=load_voices, daemon=True).start()
    
    def detect_language(self, text: str) -> str:
        """检测文本主要语言"""
        # 简单的语言检测：统计中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.sub(r'\s+', '', text))
        
        if total_chars == 0:
            return "en"
        
        chinese_ratio = chinese_chars / total_chars
        
        # 如果中文字符超过30%，认为是中文
        return "zh" if chinese_ratio > 0.3 else "en"
    
    def get_optimal_voice(self, text: str, engine: str = None) -> Dict[str, str]:
        """获取最适合的语音"""
        if engine is None:
            engine = self.config.get("tts.engine", "edge")
        
        language = self.detect_language(text)
        
        if engine == "edge":
            voice_config = self.config.get("tts.voice", {})
            if language == "zh":
                voice_name = voice_config.get("chinese", "zh-CN-XiaoxiaoNeural")
            else:
                voice_name = voice_config.get("english", "en-US-JennyNeural")
            
            return {
                "engine": "edge",
                "voice": voice_name,
                "language": language
            }
        else:
            # Windows TTS - 选择合适的语音
            if self.speaker:
                voices = self.speaker.GetVoices()
                for i in range(voices.Count):
                    voice = voices.Item(i)
                    desc = voice.GetDescription()
                    
                    if language == "zh" and "Chinese" in desc:
                        return {
                            "engine": "windows",
                            "voice": desc,
                            "voice_index": i,
                            "language": language
                        }
                    elif language == "en" and "English" in desc:
                        return {
                            "engine": "windows", 
                            "voice": desc,
                            "voice_index": i,
                            "language": language
                        }
                
                # 默认使用第一个语音
                return {
                    "engine": "windows",
                    "voice": voices.Item(0).GetDescription(),
                    "voice_index": 0,
                    "language": language
                }
            
            return {"engine": "windows", "voice": None, "language": language}
    
    async def speak_text_async(self, 
                              text: str, 
                              callback: Callable[[Dict[str, Any]], None] = None,
                              engine: str = None) -> Dict[str, Any]:
        """异步语音合成和播放"""
        if self.is_speaking:
            self.stop_speaking()
            await asyncio.sleep(0.5)  # 等待停止完成
        
        self.is_speaking = True

        # 清理文本，移除表情符号和特殊符号
        try:
            from simple_text_cleaner import clean_text_for_tts
            original_length = len(text)
            cleaned_text = clean_text_for_tts(text)
            if not cleaned_text.strip():
                if callback:
                    callback({"status": "completed", "message": "文本清理后为空，跳过朗读"})
                self.is_speaking = False
                return {"success": True, "message": "文本清理后为空，跳过朗读"}
            text = cleaned_text
            logging.info(f"文本清理完成，原长度: {original_length}, 清理后长度: {len(cleaned_text)}")
        except ImportError:
            logging.warning("文本清理模块不可用，使用原始文本")
        except Exception as e:
            logging.error(f"文本清理失败: {e}")
            # 继续使用原始文本

        try:
            voice_info = self.get_optimal_voice(text, engine)
            
            if callback:
                callback({
                    "status": "starting",
                    "message": f"开始合成语音 ({voice_info['engine']})",
                    "voice_info": voice_info
                })
            
            if voice_info["engine"] == "edge":
                result = await self._speak_with_edge_tts(text, voice_info, callback)
            else:
                result = await self._speak_with_windows_tts(text, voice_info, callback)
            
            return result
            
        except Exception as e:
            logging.error(f"语音合成失败: {e}")
            if callback:
                callback({
                    "status": "error",
                    "message": f"语音合成失败: {e}",
                    "error": str(e)
                })
            
            return {
                "success": False,
                "error": str(e),
                "engine": voice_info.get("engine", "unknown")
            }
        finally:
            self.is_speaking = False
    
    async def _speak_with_edge_tts(self, 
                                  text: str, 
                                  voice_info: Dict[str, str],
                                  callback: Callable[[Dict[str, Any]], None] = None) -> Dict[str, Any]:
        """使用Edge TTS进行语音合成"""
        try:
            if callback:
                callback({
                    "status": "synthesizing",
                    "message": "正在生成Edge TTS音频...",
                    "progress": 0.3
                })
            
            # 生成临时文件名
            temp_file = f"temp_ai_speech_{int(time.time())}.mp3"
            
            # 异步生成音频
            communicate = edge_tts.Communicate(text, voice_info["voice"])
            await communicate.save(temp_file)
            
            if not Path(temp_file).exists():
                raise Exception("音频文件生成失败")
            
            file_size = Path(temp_file).stat().st_size
            
            if callback:
                callback({
                    "status": "playing",
                    "message": "正在播放音频...",
                    "progress": 0.7,
                    "file_info": {"name": temp_file, "size": file_size}
                })
            
            # 播放音频
            if AUDIO_PLAYER_AVAILABLE:
                def play_callback(success):
                    try:
                        if Path(temp_file).exists():
                            Path(temp_file).unlink()
                    except:
                        pass
                    
                    if callback:
                        callback({
                            "status": "completed" if success else "play_failed",
                            "message": "播放完成" if success else "播放失败",
                            "progress": 1.0
                        })
                
                # 异步播放
                play_thread = play_audio_file(temp_file, callback=play_callback)
                
                return {
                    "success": True,
                    "engine": "edge",
                    "voice": voice_info["voice"],
                    "file_size": file_size,
                    "play_thread": play_thread
                }
            else:
                # 使用系统默认播放器
                import os
                os.startfile(temp_file)
                
                if callback:
                    callback({
                        "status": "completed",
                        "message": "已使用系统播放器打开",
                        "progress": 1.0
                    })
                
                return {
                    "success": True,
                    "engine": "edge",
                    "voice": voice_info["voice"],
                    "file_size": file_size,
                    "method": "system_player"
                }
                
        except Exception as e:
            # 清理临时文件
            try:
                if 'temp_file' in locals() and Path(temp_file).exists():
                    Path(temp_file).unlink()
            except:
                pass
            
            raise e
    
    async def _speak_with_windows_tts(self, 
                                     text: str, 
                                     voice_info: Dict[str, str],
                                     callback: Callable[[Dict[str, Any]], None] = None) -> Dict[str, Any]:
        """使用Windows TTS进行语音合成"""
        if not self.speaker:
            raise Exception("Windows TTS不可用")
        
        def speak_sync():
            try:
                # 设置语音
                if "voice_index" in voice_info:
                    voices = self.speaker.GetVoices()
                    self.speaker.Voice = voices.Item(voice_info["voice_index"])
                
                # 设置参数
                tts_config = self.config.get_tts_config()
                self.speaker.Rate = tts_config.get("rate", 5)
                self.speaker.Volume = tts_config.get("volume", 80)
                
                if callback:
                    callback({
                        "status": "playing",
                        "message": "正在播放Windows TTS音频...",
                        "progress": 0.5
                    })
                
                # 同步播放
                self.speaker.Speak(text)
                
                if callback:
                    callback({
                        "status": "completed",
                        "message": "Windows TTS播放完成",
                        "progress": 1.0
                    })
                
                return {
                    "success": True,
                    "engine": "windows",
                    "voice": voice_info["voice"]
                }
                
            except Exception as e:
                if callback:
                    callback({
                        "status": "error",
                        "message": f"Windows TTS播放失败: {e}",
                        "error": str(e)
                    })
                raise e
        
        # 在线程池中运行同步函数
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, speak_sync)
    
    def speak_text_sync(self, text: str, engine: str = None) -> Dict[str, Any]:
        """同步语音合成和播放"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.speak_text_async(text, engine=engine))
            loop.close()
            return result
        except Exception as e:
            logging.error(f"同步语音合成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_speaking(self):
        """停止当前语音播放"""
        try:
            # 立即设置停止标志
            self.is_speaking = False

            # 停止Windows TTS（立即停止）
            if self.speaker:
                try:
                    self.speaker.Speak("", 1)  # SVSFPurgeBeforeSpeak + 立即停止
                    logging.info("Windows TTS已停止")
                except:
                    pass

            # 停止音频播放器
            if AUDIO_PLAYER_AVAILABLE:
                try:
                    stop_audio()
                    logging.info("音频播放器已停止")
                except:
                    pass

            # 强制停止pygame（如果正在使用）
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                    logging.info("pygame已停止")
            except:
                pass

            # 清理临时文件
            try:
                self._cleanup_temp_files()
            except:
                pass

            logging.info("语音播放已强制停止")

        except Exception as e:
            logging.error(f"停止语音播放失败: {e}")
            # 确保停止标志被设置
            self.is_speaking = False
    
    def get_available_voices(self, engine: str = None) -> Dict[str, list]:
        """获取可用语音列表"""
        if engine is None:
            engine = self.config.get("tts.engine", "edge")
        
        voices = {"chinese": [], "english": [], "other": []}
        
        if engine == "edge":
            for voice in self.edge_voices:
                locale = voice.get("Locale", "")
                voice_info = {
                    "name": voice.get("Name", ""),
                    "display_name": voice.get("DisplayName", ""),
                    "gender": voice.get("Gender", ""),
                    "locale": locale
                }
                
                if locale.startswith("zh"):
                    voices["chinese"].append(voice_info)
                elif locale.startswith("en"):
                    voices["english"].append(voice_info)
                else:
                    voices["other"].append(voice_info)
        
        elif engine == "windows" and self.speaker:
            windows_voices = self.speaker.GetVoices()
            for i in range(windows_voices.Count):
                voice = windows_voices.Item(i)
                desc = voice.GetDescription()
                
                voice_info = {
                    "name": desc,
                    "display_name": desc,
                    "index": i,
                    "locale": "unknown"
                }
                
                if "Chinese" in desc:
                    voices["chinese"].append(voice_info)
                elif "English" in desc:
                    voices["english"].append(voice_info)
                else:
                    voices["other"].append(voice_info)
        
        return voices
    
    def test_voice(self, voice_name: str, engine: str = None) -> Dict[str, Any]:
        """测试指定语音"""
        test_texts = {
            "zh": "你好，这是语音测试。",
            "en": "Hello, this is a voice test."
        }
        
        # 根据语音名称判断语言
        if any(lang in voice_name.lower() for lang in ["zh", "chinese", "中文"]):
            test_text = test_texts["zh"]
        else:
            test_text = test_texts["en"]
        
        return self.speak_text_sync(test_text, engine)
    
    def get_status(self) -> Dict[str, Any]:
        """获取TTS状态"""
        return {
            "is_speaking": self.is_speaking,
            "windows_tts_available": self.speaker is not None,
            "edge_tts_available": len(self.edge_voices) > 0,
            "audio_player_available": AUDIO_PLAYER_AVAILABLE,
            "current_engine": self.config.get("tts.engine", "edge"),
            "voice_count": {
                "edge": len(self.edge_voices),
                "windows": self.speaker.GetVoices().Count if self.speaker else 0
            }
        }

    def speak_text(self, text: str, engine: str = "auto") -> Dict[str, Any]:
        """同步语音合成和播放"""
        try:
            # 清理文本，移除表情符号和特殊符号
            try:
                from simple_text_cleaner import clean_text_for_tts
                original_length = len(text)
                cleaned_text = clean_text_for_tts(text)
                if not cleaned_text.strip():
                    return {"success": True, "message": "文本清理后为空，跳过朗读"}
                text = cleaned_text
                logging.info(f"文本清理完成，原长度: {original_length}, 清理后长度: {len(cleaned_text)}")
            except ImportError:
                logging.warning("文本清理模块不可用，使用原始文本")
            except Exception as e:
                logging.error(f"文本清理失败: {e}")
                # 继续使用原始文本

            # 使用异步方法的同步版本
            import asyncio

            def sync_callback(status_info):
                pass  # 同步模式不需要回调

            # 创建事件循环并运行异步方法
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 运行异步语音合成
            result = loop.run_until_complete(self.speak_text_async(text, sync_callback))

            return {"success": True, "message": "语音播放完成"}

        except Exception as e:
            logging.error(f"同步语音合成失败: {e}")
            return {"success": False, "error": str(e)}

# 全局智能TTS管理器实例
smart_tts_manager = SmartTTSManager()

def get_smart_tts_manager() -> SmartTTSManager:
    """获取智能TTS管理器实例"""
    return smart_tts_manager
