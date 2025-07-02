#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频播放器模块
提供跨平台的音频播放功能
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

class AudioPlayer:
    """音频播放器类"""
    
    def __init__(self):
        self.current_process = None
        self.is_playing = False
    
    def play_with_winsound(self, filename):
        """使用winsound播放WAV文件"""
        try:
            import winsound
            if filename.lower().endswith('.wav'):
                winsound.PlaySound(filename, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return True
            else:
                return False
        except ImportError:
            return False
        except Exception as e:
            print(f"winsound播放失败: {e}")
            return False
    
    def play_with_pygame(self, filename):
        """使用pygame播放音频"""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                if not self.is_playing:  # 如果被停止
                    pygame.mixer.music.stop()
                    break
            
            pygame.mixer.quit()
            return True
            
        except ImportError:
            return False
        except Exception as e:
            print(f"pygame播放失败: {e}")
            return False
    
    def play_with_playsound(self, filename):
        """使用playsound播放音频"""
        try:
            import playsound
            playsound.playsound(filename)
            return True
            
        except ImportError:
            return False
        except Exception as e:
            print(f"playsound播放失败: {e}")
            return False
    
    def play_with_system(self, filename):
        """使用系统默认播放器"""
        try:
            if sys.platform.startswith('win'):
                # Windows
                os.startfile(filename)
                return True
            elif sys.platform.startswith('darwin'):
                # macOS
                subprocess.run(['open', filename])
                return True
            else:
                # Linux
                subprocess.run(['xdg-open', filename])
                return True
                
        except Exception as e:
            print(f"系统播放器失败: {e}")
            return False
    
    def play_with_powershell(self, filename):
        """使用PowerShell播放音频"""
        try:
            # 使用PowerShell的媒体播放功能
            ps_script = f'''
            Add-Type -AssemblyName presentationCore
            $mediaPlayer = New-Object system.windows.media.mediaplayer
            $mediaPlayer.open([uri]"{Path(filename).absolute()}")
            $mediaPlayer.Play()
            Start-Sleep -Seconds 1
            while($mediaPlayer.NaturalDuration.HasTimeSpan -eq $false) {{
                Start-Sleep -Milliseconds 100
            }}
            $duration = $mediaPlayer.NaturalDuration.TimeSpan.TotalSeconds
            Start-Sleep -Seconds $duration
            $mediaPlayer.Stop()
            $mediaPlayer.Close()
            '''
            
            result = subprocess.run(['powershell', '-Command', ps_script], 
                                  capture_output=True, text=True, timeout=30)
            return result.returncode == 0
            
        except Exception as e:
            print(f"PowerShell播放失败: {e}")
            return False
    
    def play_audio(self, filename, method='auto'):
        """播放音频文件"""
        if not Path(filename).exists():
            print(f"音频文件不存在: {filename}")
            return False
        
        self.is_playing = True
        
        # 根据方法选择播放方式
        if method == 'auto':
            # 自动选择最佳方法
            methods = [
                ('winsound', self.play_with_winsound),
                ('pygame', self.play_with_pygame),
                ('playsound', self.play_with_playsound),
                ('powershell', self.play_with_powershell),
                ('system', self.play_with_system),
            ]
            
            for method_name, play_func in methods:
                try:
                    if play_func(filename):
                        print(f"使用 {method_name} 播放: {filename}")
                        return True
                except Exception as e:
                    print(f"{method_name} 方法失败: {e}")
                    continue
            
            print("所有播放方法都失败了")
            return False
            
        else:
            # 使用指定方法
            method_map = {
                'winsound': self.play_with_winsound,
                'pygame': self.play_with_pygame,
                'playsound': self.play_with_playsound,
                'powershell': self.play_with_powershell,
                'system': self.play_with_system,
            }
            
            if method in method_map:
                return method_map[method](filename)
            else:
                print(f"未知的播放方法: {method}")
                return False
    
    def play_audio_async(self, filename, method='auto', callback=None):
        """异步播放音频"""
        def play_thread():
            try:
                success = self.play_audio(filename, method)
                if callback:
                    callback(success)
            finally:
                self.is_playing = False
        
        thread = threading.Thread(target=play_thread, daemon=True)
        thread.start()
        return thread
    
    def stop_audio(self):
        """停止音频播放"""
        self.is_playing = False
        
        # 尝试停止pygame
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except:
            pass
    
    def test_audio_methods(self):
        """测试所有音频播放方法"""
        print("🔊 测试音频播放方法...")
        
        # 创建测试音频文件
        test_file = "audio_test.wav"
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            file_stream = win32com.client.Dispatch("SAPI.SpFileStream")
            file_stream.Open(test_file, 3)
            speaker.AudioOutputStream = file_stream
            speaker.Speak("音频播放测试")
            file_stream.Close()
            speaker.AudioOutputStream = None
            
            if Path(test_file).exists():
                print(f"✅ 测试文件创建成功: {test_file}")
                
                # 测试各种方法
                methods = ['winsound', 'pygame', 'playsound', 'powershell', 'system']
                working_methods = []
                
                for method in methods:
                    print(f"  测试 {method}...")
                    if self.play_audio(test_file, method):
                        working_methods.append(method)
                        print(f"  ✅ {method} 可用")
                        time.sleep(1)  # 等待播放完成
                    else:
                        print(f"  ❌ {method} 不可用")
                
                # 清理测试文件
                os.remove(test_file)
                
                print(f"\n📊 可用方法: {working_methods}")
                return working_methods
            else:
                print("❌ 测试文件创建失败")
                return []
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return []

# 全局音频播放器实例
audio_player = AudioPlayer()

def play_audio_file(filename, method='auto', async_play=True, callback=None):
    """便捷的音频播放函数"""
    if async_play:
        return audio_player.play_audio_async(filename, method, callback)
    else:
        return audio_player.play_audio(filename, method)

def stop_audio():
    """停止音频播放"""
    audio_player.stop_audio()

def test_audio_system():
    """测试音频系统"""
    return audio_player.test_audio_methods()

if __name__ == "__main__":
    # 测试音频播放器
    test_audio_system()
