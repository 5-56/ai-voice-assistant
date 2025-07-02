#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能语音助手主程序
集成DeepSeek大语言模型和Edge TTS的智能对话系统
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import asyncio
import threading
import logging
import sys
import math
from datetime import datetime
from pathlib import Path

# 导入自定义模块
from config_manager import get_config
from conversation_manager import get_conversation_manager
from deepseek_client import get_deepseek_client
from smart_tts_manager import get_smart_tts_manager

# RAG系统集成
try:
    from rag_system import get_rag_system
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG系统不可用")

# 天气查询集成
try:
    from weather_query_handler import get_weather_query_handler
    WEATHER_AVAILABLE = True
except ImportError:
    WEATHER_AVAILABLE = False
    logging.warning("天气查询功能不可用")

# IP查询集成
try:
    from ip_query_handler import get_ip_query_handler
    IP_QUERY_AVAILABLE = True
except ImportError:
    IP_QUERY_AVAILABLE = False
    logging.warning("IP查询功能不可用")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_voice_assistant.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AIVoiceAssistant:
    """智能语音助手主类"""
    
    def __init__(self, root):
        self.root = root
        self.config = get_config()
        self.conversation_manager = get_conversation_manager()
        self.deepseek_client = get_deepseek_client()
        self.tts_manager = get_smart_tts_manager()

        # 实时语音对话管理器
        try:
            from realtime_voice_manager import get_realtime_voice_manager, VoiceMode
            self.voice_manager = get_realtime_voice_manager()
            self.VoiceMode = VoiceMode
        except ImportError as e:
            logging.warning(f"实时语音功能不可用: {e}")
            self.voice_manager = None
            self.VoiceMode = None

        # 语音唤醒检测器
        try:
            from wake_word_detector import get_wake_word_detector
            self.wake_word_detector = get_wake_word_detector()
            self.wake_word_detector.on_wake_word_detected = self.on_wake_word_detected
            self.wake_word_detector.on_detection_error = self.on_wake_word_error
            self.wake_word_enabled = False  # 默认关闭，用户可以手动开启
        except ImportError as e:
            logging.warning(f"语音唤醒功能不可用: {e}")
            self.wake_word_detector = None
            self.wake_word_enabled = False

        # 文件和剪贴板管理器
        try:
            from file_manager import get_file_manager
            from clipboard_manager import get_clipboard_manager
            self.file_manager = get_file_manager()
            self.clipboard_manager = get_clipboard_manager()
        except ImportError as e:
            logging.warning(f"文件管理功能不可用: {e}")
            self.file_manager = None
            self.clipboard_manager = None

        # 模型管理器
        try:
            from model_manager import get_model_manager
            self.model_manager = get_model_manager()
        except ImportError as e:
            logging.warning(f"模型管理功能不可用: {e}")
            self.model_manager = None

        # 状态变量
        self.is_processing = False
        self.auto_read_enabled = True
        self.sidebar_visible = True  # 侧边栏显示状态
        self.voice_mode_enabled = False  # 语音模式状态

        # 屏幕和DPI信息
        self.screen_info = self.get_screen_info()
        self.dpi_scale = self.calculate_dpi_scale()

        # 设置窗口
        self.setup_window()

        # 创建界面
        self.create_widgets()

        # 绑定事件
        self.bind_events()

        # 初始化语音功能
        self.setup_voice_callbacks()

        # 初始化状态
        self.update_status("就绪")
        self.check_configuration()

    def setup_voice_callbacks(self):
        """设置语音功能回调"""
        if self.voice_manager:
            self.voice_manager.set_callbacks(
                on_state_changed=self.on_voice_state_changed,
                on_text_input=self.on_voice_text_input,
                on_text_output=self.on_voice_text_output,
                on_error=self.on_voice_error
            )

    def on_voice_state_changed(self, status: dict):
        """语音状态变化回调"""
        try:
            state = status.get("conversation_state", "idle")
            mode = status.get("voice_mode", "disabled")

            # 更新状态显示
            if state == "listening":
                self.update_status("🎤 正在监听...")
            elif state == "processing":
                self.update_status("🤔 正在思考...")
            elif state == "speaking":
                self.update_status("🔊 正在播放...")
            elif state == "interrupted":
                self.update_status("⏸️ 已打断")
            else:
                self.update_status("就绪")

            # 更新界面元素状态
            self.root.after(0, lambda: self.update_voice_ui_state(status))

        except Exception as e:
            logging.error(f"语音状态变化处理失败: {e}")

    def on_voice_text_input(self, text: str):
        """语音文本输入回调"""
        try:
            # 在对话显示中添加用户消息
            self.root.after(0, lambda: self.add_message_to_display("user", text))
        except Exception as e:
            logging.error(f"语音文本输入处理失败: {e}")

    def on_voice_text_output(self, text: str):
        """语音文本输出回调"""
        try:
            # 在对话显示中添加AI回复
            self.root.after(0, lambda: self.add_message_to_display("assistant", text))
        except Exception as e:
            logging.error(f"语音文本输出处理失败: {e}")

    def on_voice_error(self, error: str):
        """语音错误回调"""
        try:
            self.root.after(0, lambda: self.update_status(f"❌ {error}"))
            self.root.after(0, lambda: messagebox.showerror("语音错误", error))
        except Exception as e:
            logging.error(f"语音错误处理失败: {e}")

    def on_wake_word_detected(self, wake_word: str):
        """语音唤醒词检测回调"""
        try:
            logging.info(f"🎤 检测到唤醒词: {wake_word}")

            # 在主线程中执行UI更新和语音模式切换
            self.root.after(0, lambda: self._handle_wake_word_activation(wake_word))

        except Exception as e:
            logging.error(f"唤醒词处理失败: {e}")

    def _handle_wake_word_activation(self, wake_word: str):
        """处理唤醒词激活（在主线程中执行）"""
        try:
            # 显示唤醒提示
            self.update_status(f"🎤 检测到唤醒词: {wake_word}")

            # 在对话区域显示唤醒信息
            self.add_message_to_display("system", f"🎤 检测到唤醒词: {wake_word}")

            # 自动开启语音模式
            if self.voice_manager and not self.voice_manager.is_active:
                self.toggle_voice_mode()
                self.add_message_to_display("system", "🔊 语音模式已自动开启，请开始对话...")

            # 播放确认音效（可选）
            self._play_wake_confirmation()

        except Exception as e:
            logging.error(f"唤醒词激活处理失败: {e}")

    def _play_wake_confirmation(self):
        """播放唤醒确认音效"""
        try:
            # 播放简短的确认语音
            confirmation_text = "我在，请说"
            if self.tts_manager:
                threading.Thread(
                    target=lambda: asyncio.run(self.tts_manager.speak_text(confirmation_text)),
                    daemon=True
                ).start()
        except Exception as e:
            logging.error(f"播放唤醒确认音效失败: {e}")

    def on_wake_word_error(self, error: str):
        """语音唤醒错误回调"""
        try:
            logging.error(f"语音唤醒错误: {error}")
            # 不在界面显示唤醒错误，避免干扰用户
        except Exception as e:
            logging.error(f"语音唤醒错误处理失败: {e}")

    def update_voice_ui_state(self, status: dict):
        """更新语音相关的UI状态"""
        try:
            # 这里可以根据语音状态更新UI元素
            # 例如改变按钮状态、显示指示器等
            pass
        except Exception as e:
            logging.error(f"更新语音UI状态失败: {e}")

    def get_screen_info(self):
        """获取屏幕信息"""
        # 临时创建一个窗口来获取屏幕信息
        temp_root = tk.Tk()
        temp_root.withdraw()  # 隐藏窗口

        screen_width = temp_root.winfo_screenwidth()
        screen_height = temp_root.winfo_screenheight()

        # 获取DPI信息
        try:
            dpi_x = temp_root.winfo_fpixels('1i')
            dpi_y = temp_root.winfo_fpixels('1i')
        except:
            dpi_x = dpi_y = 96  # 默认DPI

        temp_root.destroy()

        return {
            'width': screen_width,
            'height': screen_height,
            'dpi_x': dpi_x,
            'dpi_y': dpi_y
        }

    def calculate_dpi_scale(self):
        """计算DPI缩放比例"""
        base_dpi = 96  # Windows标准DPI
        current_dpi = self.screen_info['dpi_x']
        scale = current_dpi / base_dpi

        # 限制缩放范围
        scale = max(0.8, min(scale, 3.0))

        return scale

    def scale_size(self, size):
        """根据DPI缩放尺寸"""
        return int(size * self.dpi_scale)

    def get_adaptive_window_size(self):
        """获取自适应窗口大小"""
        screen_width = self.screen_info['width']
        screen_height = self.screen_info['height']

        # 根据屏幕大小计算合适的窗口尺寸（占屏幕的75%）
        target_width = int(screen_width * 0.75)
        target_height = int(screen_height * 0.75)

        # 设置最小和最大尺寸限制
        min_width = self.scale_size(900)
        min_height = self.scale_size(650)
        max_width = int(screen_width * 0.9)
        max_height = int(screen_height * 0.9)

        # 应用限制
        width = max(min_width, min(target_width, max_width))
        height = max(min_height, min(target_height, max_height))

        return width, height

    def get_saved_window_state(self):
        """获取保存的窗口状态"""
        ui_config = self.config.get_ui_config()
        window_state = ui_config.get("window_state", {})

        return {
            'width': window_state.get('width'),
            'height': window_state.get('height'),
            'x': window_state.get('x'),
            'y': window_state.get('y'),
            'maximized': window_state.get('maximized', False)
        }

    def save_window_state(self):
        """保存窗口状态"""
        try:
            # 获取当前窗口状态
            geometry = self.root.geometry()

            # 解析几何字符串 "widthxheight+x+y"
            size_pos = geometry.split('+')
            size = size_pos[0].split('x')

            width = int(size[0])
            height = int(size[1])
            x = int(size_pos[1]) if len(size_pos) > 1 else 0
            y = int(size_pos[2]) if len(size_pos) > 2 else 0

            # 检查是否最大化
            maximized = self.root.state() == 'zoomed'

            # 保存到配置
            window_state = {
                'width': width,
                'height': height,
                'x': x,
                'y': y,
                'maximized': maximized
            }

            self.config.set("ui.window_state", window_state)
            self.config.save_config()

        except Exception as e:
            logging.warning(f"保存窗口状态失败: {e}")

    def setup_window(self):
        """设置主窗口"""
        self.root.title("🤖 智能语音助手 - AI Voice Assistant")

        # 设置高DPI支持
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        # 获取保存的窗口状态
        saved_state = self.get_saved_window_state()

        # 确定窗口大小
        if saved_state['width'] and saved_state['height']:
            # 使用保存的尺寸，但要验证是否合理
            width = saved_state['width']
            height = saved_state['height']

            # 验证尺寸是否在合理范围内
            adaptive_width, adaptive_height = self.get_adaptive_window_size()
            min_width = self.scale_size(800)
            min_height = self.scale_size(600)

            if width < min_width or height < min_height:
                width, height = adaptive_width, adaptive_height
        else:
            # 使用自适应尺寸
            width, height = self.get_adaptive_window_size()

        # 确定窗口位置
        if saved_state['x'] is not None and saved_state['y'] is not None:
            x = saved_state['x']
            y = saved_state['y']

            # 验证位置是否在屏幕范围内
            screen_width = self.screen_info['width']
            screen_height = self.screen_info['height']

            if x < 0 or y < 0 or x + width > screen_width or y + height > screen_height:
                # 重新居中
                x = (screen_width - width) // 2
                y = (screen_height - height) // 2
        else:
            # 居中显示
            x = (self.screen_info['width'] - width) // 2
            y = (self.screen_info['height'] - height) // 2

        # 设置窗口几何
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # 设置最小尺寸（根据DPI缩放）
        min_width = self.scale_size(800)
        min_height = self.scale_size(600)
        self.root.minsize(min_width, min_height)

        # 如果之前是最大化状态，恢复最大化
        if saved_state['maximized']:
            self.root.state('zoomed')

        # 设置窗口图标
        try:
            # self.root.iconbitmap("icon.ico")
            pass
        except:
            pass

        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self.on_window_configure)

    def on_window_configure(self, event):
        """窗口大小变化事件处理"""
        if event.widget == self.root:
            # 更新响应式布局
            self.root.after_idle(self.update_responsive_layout)

    def on_toolbar_mousewheel(self, event):
        """工具栏鼠标滚轮事件"""
        self.toolbar_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_initial_pane_weights(self):
        """设置初始面板权重"""
        try:
            window_width = self.root.winfo_width()

            # 根据窗口宽度调整分割比例
            if window_width < self.scale_size(1000):
                # 小窗口：对话列表占25%
                self.paned_window.sashpos(0, int(window_width * 0.25))
            elif window_width < self.scale_size(1400):
                # 中等窗口：对话列表占30%
                self.paned_window.sashpos(0, int(window_width * 0.30))
            else:
                # 大窗口：对话列表占35%
                self.paned_window.sashpos(0, int(window_width * 0.35))
        except:
            pass

    def update_responsive_layout(self):
        """更新响应式布局"""
        try:
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()

            # 更新工具栏布局
            self.update_toolbar_layout(window_width)

            # 更新输入框高度
            self.update_input_height(window_height)

            # 更新字体大小
            self.update_font_sizes()

        except Exception as e:
            logging.debug(f"更新响应式布局失败: {e}")

    def update_toolbar_layout(self, window_width):
        """更新工具栏布局"""
        try:
            # 检查工具栏是否需要滚动
            self.toolbar_canvas.update_idletasks()
            content_width = self.toolbar_content.winfo_reqwidth()
            canvas_width = self.toolbar_canvas.winfo_width()

            if content_width > canvas_width:
                # 需要滚动，显示滚动条
                if not self.toolbar_scrollbar.winfo_viewable():
                    self.toolbar_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            else:
                # 不需要滚动，隐藏滚动条
                if self.toolbar_scrollbar.winfo_viewable():
                    self.toolbar_scrollbar.pack_forget()

            # 根据窗口宽度调整按钮文本
            if window_width < self.scale_size(900):
                # 小窗口：使用简短文本
                self.new_conv_btn.config(text="🆕")
                self.load_conv_btn.config(text="📁")
                self.save_conv_btn.config(text="💾")
                self.settings_btn.config(text="⚙️")
                self.about_btn.config(text="ℹ️")
                self.auto_read_cb.config(text="🔊")
            elif window_width < self.scale_size(1200):
                # 中等窗口：使用中等文本
                self.new_conv_btn.config(text="🆕 新建")
                self.load_conv_btn.config(text="📁 加载")
                self.save_conv_btn.config(text="💾 保存")
                self.settings_btn.config(text="⚙️ 设置")
                self.about_btn.config(text="ℹ️ 关于")
                self.auto_read_cb.config(text="🔊 朗读")
            else:
                # 大窗口：使用完整文本
                self.new_conv_btn.config(text="🆕 新对话")
                self.load_conv_btn.config(text="📁 加载对话")
                self.save_conv_btn.config(text="💾 保存对话")
                self.settings_btn.config(text="⚙️ 设置")
                self.about_btn.config(text="ℹ️ 关于")
                self.auto_read_cb.config(text="🔊 自动朗读")

        except Exception as e:
            logging.debug(f"更新工具栏布局失败: {e}")

    def update_input_height(self, window_height):
        """更新输入框高度"""
        try:
            # 根据窗口高度调整输入框行数
            if window_height < self.scale_size(600):
                height = 2
            elif window_height < self.scale_size(800):
                height = 3
            elif window_height < self.scale_size(1000):
                height = 4
            else:
                height = 5

            self.input_text.config(height=height)

        except Exception as e:
            logging.debug(f"更新输入框高度失败: {e}")

    def update_font_sizes(self):
        """更新字体大小"""
        try:
            base_font_size = max(8, int(self.config.get("ui.font_size", 12) * self.dpi_scale))

            # 更新对话显示区域字体
            self.chat_display.config(font=('Microsoft YaHei', base_font_size))
            self.configure_chat_tags()

            # 更新输入框字体
            self.input_text.config(font=('Microsoft YaHei', base_font_size))

            # 更新对话列表字体
            self.conversation_listbox.config(font=('Microsoft YaHei', base_font_size))

        except Exception as e:
            logging.debug(f"更新字体大小失败: {e}")

    def create_widgets(self):
        """创建界面组件"""
        try:
            # 计算自适应边距
            padding = self.scale_size(5)

            # 创建主框架
            self.main_frame = ttk.Frame(self.root)
            self.main_frame.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)

            # 创建顶部工具栏（简化版）
            self.create_top_toolbar()

            # 创建主要内容区域（侧边栏 + 聊天界面）
            self.create_main_layout()

            # 创建底部状态栏
            self.create_status_bar()

            # 确保所有组件都已创建
            self.root.update_idletasks()

            # 初始化响应式布局
            self.update_responsive_layout()

            logging.info("界面组件创建完成")

        except Exception as e:
            logging.error(f"创建界面组件失败: {e}")
            messagebox.showerror("界面错误", f"创建界面失败: {e}")
    
    def create_top_toolbar(self):
        """创建顶部工具栏（简化版）"""
        padding_y = self.scale_size(5)
        padding_x = self.scale_size(5)

        self.top_toolbar_frame = ttk.Frame(self.main_frame)
        self.top_toolbar_frame.pack(fill=tk.X, pady=(0, padding_y))

        # 左侧：侧边栏切换按钮
        left_buttons = ttk.Frame(self.top_toolbar_frame)
        left_buttons.pack(side=tk.LEFT)

        # 侧边栏切换按钮
        self.sidebar_toggle_btn = ttk.Button(
            left_buttons,
            text="📋",
            width=3,
            command=self.toggle_sidebar
        )
        self.sidebar_toggle_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        # 标题
        title_label = ttk.Label(left_buttons, text="🤖 智能语音助手",
                               font=('Microsoft YaHei', max(10, self.scale_size(12)), 'bold'))
        title_label.pack(side=tk.LEFT, padx=(padding_x, 0))

        # 右侧：全局功能按钮
        right_buttons = ttk.Frame(self.top_toolbar_frame)
        right_buttons.pack(side=tk.RIGHT)

        # 自动朗读开关
        self.auto_read_var = tk.BooleanVar(value=self.config.get("tts.auto_read", True))
        self.auto_read_cb = ttk.Checkbutton(
            right_buttons,
            text="🔊",
            variable=self.auto_read_var,
            command=self.toggle_auto_read
        )
        self.auto_read_cb.pack(side=tk.LEFT, padx=(0, padding_x))

        # 设置按钮
        self.settings_btn = ttk.Button(
            right_buttons,
            text="⚙️",
            width=3,
            command=self.open_settings
        )
        self.settings_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        # 文件管理按钮
        if self.file_manager:
            self.file_mgmt_btn = ttk.Button(
                right_buttons,
                text="📁",
                width=3,
                command=self.open_file_management
            )
            self.file_mgmt_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        # 模型管理按钮
        if self.model_manager:
            self.model_mgmt_btn = ttk.Button(
                right_buttons,
                text="🤖",
                width=3,
                command=self.open_model_management
            )
            self.model_mgmt_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        # 知识库管理按钮
        if RAG_AVAILABLE:
            self.kb_mgmt_btn = ttk.Button(
                right_buttons,
                text="📚",
                width=3,
                command=self.open_knowledge_base_management
            )
            self.kb_mgmt_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        # 关于按钮
        self.about_btn = ttk.Button(
            right_buttons,
            text="ℹ️",
            width=3,
            command=self.show_about
        )
        self.about_btn.pack(side=tk.LEFT)

    def toggle_sidebar(self):
        """切换侧边栏显示/隐藏"""
        self.sidebar_visible = not self.sidebar_visible

        if self.sidebar_visible:
            self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, before=self.chat_container)
            self.sidebar_toggle_btn.config(text="📋")
        else:
            self.sidebar_frame.pack_forget()
            self.sidebar_toggle_btn.config(text="📂")

        # 更新布局
        self.root.after_idle(self.update_responsive_layout)

    def create_toolbar(self):
        """创建工具栏"""
        padding_y = self.scale_size(10)
        padding_x = self.scale_size(5)

        self.toolbar_frame = ttk.Frame(self.main_frame)
        self.toolbar_frame.pack(fill=tk.X, pady=(0, padding_y))

        # 创建可滚动的工具栏容器
        self.toolbar_canvas = tk.Canvas(self.toolbar_frame, height=self.scale_size(40))
        self.toolbar_scrollbar = ttk.Scrollbar(self.toolbar_frame, orient="horizontal", command=self.toolbar_canvas.xview)
        self.toolbar_content = ttk.Frame(self.toolbar_canvas)

        self.toolbar_content.bind(
            "<Configure>",
            lambda e: self.toolbar_canvas.configure(scrollregion=self.toolbar_canvas.bbox("all"))
        )

        self.toolbar_canvas.create_window((0, 0), window=self.toolbar_content, anchor="nw")
        self.toolbar_canvas.configure(xscrollcommand=self.toolbar_scrollbar.set)

        # 左侧按钮组
        self.left_buttons = ttk.Frame(self.toolbar_content)
        self.left_buttons.pack(side=tk.LEFT)

        # 计算按钮大小
        button_width = max(8, self.scale_size(12))

        self.new_conv_btn = ttk.Button(self.left_buttons, text="🆕 新对话", width=button_width,
                                      command=self.new_conversation)
        self.new_conv_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        self.load_conv_btn = ttk.Button(self.left_buttons, text="📁 加载", width=button_width,
                                       command=self.load_conversation)
        self.load_conv_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        self.save_conv_btn = ttk.Button(self.left_buttons, text="💾 保存", width=button_width,
                                       command=self.save_conversation)
        self.save_conv_btn.pack(side=tk.LEFT, padx=(0, padding_x))

        # 分隔符
        separator = ttk.Separator(self.left_buttons, orient=tk.VERTICAL)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=padding_x)

        # 自动朗读开关
        self.auto_read_var = tk.BooleanVar(value=self.config.get("tts.auto_read", True))
        self.auto_read_cb = ttk.Checkbutton(self.left_buttons, text="🔊 自动朗读",
                                           variable=self.auto_read_var,
                                           command=self.toggle_auto_read)
        self.auto_read_cb.pack(side=tk.LEFT, padx=(0, padding_x))

        # 知识库状态显示
        self.kb_status_frame = ttk.Frame(self.left_buttons)
        self.kb_status_frame.pack(side=tk.LEFT, padx=(padding_x, 0))

        self.kb_status_label = ttk.Label(self.kb_status_frame, text="📚 知识库: 加载中...",
                                        font=('Microsoft YaHei', 8))
        self.kb_status_label.pack(side=tk.LEFT)

        # 天气功能状态显示
        self.weather_status_frame = ttk.Frame(self.left_buttons)
        self.weather_status_frame.pack(side=tk.LEFT, padx=(padding_x, 0))

        weather_status_text = "🌤️ 天气: 可用" if WEATHER_AVAILABLE else "🌤️ 天气: 不可用"
        weather_color = "green" if WEATHER_AVAILABLE else "red"
        self.weather_status_label = ttk.Label(self.weather_status_frame, text=weather_status_text,
                                            font=('Microsoft YaHei', 8), foreground=weather_color)
        self.weather_status_label.pack(side=tk.LEFT)

        # IP查询功能状态显示
        self.ip_status_frame = ttk.Frame(self.left_buttons)
        self.ip_status_frame.pack(side=tk.LEFT, padx=(padding_x, 0))

        ip_status_text = "🌐 IP: 可用" if IP_QUERY_AVAILABLE else "🌐 IP: 不可用"
        ip_color = "green" if IP_QUERY_AVAILABLE else "red"
        self.ip_status_label = ttk.Label(self.ip_status_frame, text=ip_status_text,
                                       font=('Microsoft YaHei', 8), foreground=ip_color)
        self.ip_status_label.pack(side=tk.LEFT)

        # 初始化状态
        self.update_knowledge_base_status()

        # 右侧按钮组
        self.right_buttons = ttk.Frame(self.toolbar_content)
        self.right_buttons.pack(side=tk.RIGHT)

        self.settings_btn = ttk.Button(self.right_buttons, text="⚙️ 设置", width=button_width,
                                      command=self.open_settings)
        self.settings_btn.pack(side=tk.LEFT, padx=(padding_x, 0))

        self.about_btn = ttk.Button(self.right_buttons, text="ℹ️ 关于", width=button_width,
                                   command=self.show_about)
        self.about_btn.pack(side=tk.LEFT, padx=(padding_x, 0))

        # 默认不显示滚动条，只在需要时显示
        self.toolbar_canvas.pack(fill=tk.X)

        # 绑定鼠标滚轮事件
        self.toolbar_canvas.bind("<MouseWheel>", self.on_toolbar_mousewheel)
    
    def create_main_layout(self):
        """创建主布局（侧边栏 + 聊天界面）"""
        # 创建主容器
        self.main_container = ttk.Frame(self.main_frame)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 创建可折叠侧边栏
        self.create_sidebar()

        # 创建聊天界面容器
        self.create_chat_interface()

    def create_sidebar(self):
        """创建可折叠侧边栏"""
        # 侧边栏框架
        self.sidebar_frame = ttk.LabelFrame(self.main_container, text="📚 对话管理", padding=self.scale_size(5))
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, self.scale_size(5)))

        # 设置侧边栏宽度
        sidebar_width = self.scale_size(280)
        self.sidebar_frame.config(width=sidebar_width)
        self.sidebar_frame.pack_propagate(False)  # 防止子组件改变框架大小

        # 对话操作按钮区域
        self.create_conversation_buttons()

        # 对话历史列表
        self.create_conversation_history()

    def create_conversation_buttons(self):
        """创建对话操作按钮"""
        button_frame = ttk.Frame(self.sidebar_frame)
        button_frame.pack(fill=tk.X, pady=(0, self.scale_size(10)))

        # 计算按钮大小
        button_width = max(8, self.scale_size(10))
        padding = self.scale_size(2)

        # 第一行按钮
        row1 = ttk.Frame(button_frame)
        row1.pack(fill=tk.X, pady=(0, padding))

        self.new_conv_btn = ttk.Button(
            row1,
            text="🆕 新对话",
            command=self.new_conversation
        )
        self.new_conv_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, padding))

        self.load_conv_btn = ttk.Button(
            row1,
            text="📁 加载",
            command=self.load_conversation
        )
        self.load_conv_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 第二行按钮
        row2 = ttk.Frame(button_frame)
        row2.pack(fill=tk.X)

        self.save_conv_btn = ttk.Button(
            row2,
            text="💾 保存",
            command=self.save_conversation
        )
        self.save_conv_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, padding))

        self.clear_btn = ttk.Button(
            row2,
            text="🗑️ 清理",
            command=self.clear_conversation_history
        )
        self.clear_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_conversation_history(self):
        """创建对话历史列表"""
        # 历史列表框架
        history_frame = ttk.Frame(self.sidebar_frame)
        history_frame.pack(fill=tk.BOTH, expand=True)

        # 标签
        ttk.Label(history_frame, text="历史对话:",
                 font=('Microsoft YaHei', max(9, self.scale_size(10)))).pack(anchor=tk.W, pady=(0, self.scale_size(5)))

        # 创建列表框和滚动条
        list_container = ttk.Frame(history_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        # 对话列表
        self.conversation_listbox = tk.Listbox(
            list_container,
            font=('Microsoft YaHei', max(9, self.scale_size(10))),
            selectmode=tk.SINGLE,
            activestyle='dotbox'
        )

        # 滚动条
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.conversation_listbox.yview)
        self.conversation_listbox.configure(yscrollcommand=scrollbar.set)

        # 布局
        self.conversation_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定事件
        self.conversation_listbox.bind("<Double-Button-1>", self.on_conversation_select)
        self.conversation_listbox.bind("<Button-3>", self.show_conversation_menu)

        # 创建右键菜单
        self.create_conversation_context_menu()

        # 刷新对话列表
        self.refresh_conversation_list()

    def clear_conversation_history(self):
        """清理对话历史"""
        result = messagebox.askyesno(
            "确认清理",
            "确定要清理所有对话历史吗？\n\n此操作不可撤销。",
            icon="warning"
        )

        if result:
            # 清理对话历史
            self.conversation_manager.clear_all_conversations()
            self.refresh_conversation_list()
            self.refresh_chat_display()
            self.update_status("对话历史已清理")

    def create_chat_interface(self):
        """创建聊天界面"""
        # 聊天界面容器
        self.chat_container = ttk.Frame(self.main_container)
        self.chat_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 创建对话显示区域
        self.create_chat_display_area()

        # 创建输入区域
        self.create_input_area_new()

    def create_chat_display_area(self):
        """创建对话显示区域"""
        # 对话显示框架
        self.chat_display_frame = ttk.LabelFrame(
            self.chat_container,
            text="💬 当前对话",
            padding=self.scale_size(5)
        )
        self.chat_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, self.scale_size(10)))

        # 创建带滚动条的文本框
        font_size = max(10, int(self.config.get("ui.font_size", 12) * self.dpi_scale))

        self.chat_display = scrolledtext.ScrolledText(
            self.chat_display_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=('Microsoft YaHei', font_size),
            bg='#f8f9fa',
            fg='#333333',
            relief=tk.FLAT,
            borderwidth=1,
            height=20  # 确保有足够的高度
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # 配置文本标签样式
        self.configure_chat_tags()

        # 添加欢迎消息
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "🤖 欢迎使用智能语音助手！\n\n")
        self.chat_display.insert(tk.END, "💡 您可以：\n")
        self.chat_display.insert(tk.END, "• 在下方输入框中输入问题\n")
        self.chat_display.insert(tk.END, "• 按 Ctrl+Enter 发送消息\n")
        self.chat_display.insert(tk.END, "• 点击侧边栏按钮管理对话\n\n")
        self.chat_display.config(state=tk.DISABLED)

    def create_input_area_new(self):
        """创建新的输入区域"""
        # 输入框架
        self.input_frame = ttk.LabelFrame(
            self.chat_container,
            text="✏️ 输入消息",
            padding=self.scale_size(5)
        )
        self.input_frame.pack(fill=tk.X)

        # 输入文本框
        font_size = max(10, int(self.config.get("ui.font_size", 12) * self.dpi_scale))

        self.input_text = scrolledtext.ScrolledText(
            self.input_frame,
            height=4,
            wrap=tk.WORD,
            font=('Microsoft YaHei', font_size),
            relief=tk.FLAT,
            borderwidth=1
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(0, self.scale_size(10)))

        # 按钮和状态区域
        bottom_frame = ttk.Frame(self.input_frame)
        bottom_frame.pack(fill=tk.X)

        # 左侧控制按钮
        left_controls = ttk.Frame(bottom_frame)
        left_controls.pack(side=tk.LEFT)

        self.clear_input_btn = ttk.Button(
            left_controls,
            text="🔄 清空",
            command=self.clear_input
        )
        self.clear_input_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

        self.stop_btn = ttk.Button(
            left_controls,
            text="⏹️ 停止",
            command=self.stop_speaking
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

        # 文件和剪贴板功能按钮
        if self.file_manager:
            self.upload_btn = ttk.Button(
                left_controls,
                text="📁 上传",
                command=self.upload_files
            )
            self.upload_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

        if self.clipboard_manager:
            self.paste_btn = ttk.Button(
                left_controls,
                text="📋 粘贴",
                command=self.paste_from_clipboard
            )
            self.paste_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

        # 语音控制按钮
        if self.voice_manager:
            self.voice_btn = ttk.Button(
                left_controls,
                text="🎤 语音",
                command=self.toggle_voice_mode
            )
            self.voice_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

            self.push_to_talk_btn = ttk.Button(
                left_controls,
                text="📢 按键说话",
                command=self.start_push_to_talk
            )
            self.push_to_talk_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

        # 语音唤醒控制按钮
        if self.wake_word_detector:
            self.wake_word_btn = ttk.Button(
                left_controls,
                text="🔊 唤醒词",
                command=self.toggle_wake_word_detection
            )
            self.wake_word_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

        # 中间状态显示
        self.processing_label = ttk.Label(
            bottom_frame,
            text="",
            foreground="#ff6600",
            font=('Microsoft YaHei', max(9, font_size - 1))
        )
        self.processing_label.pack(side=tk.LEFT, padx=(self.scale_size(10), 0))

        # 右侧控制按钮
        right_controls = ttk.Frame(bottom_frame)
        right_controls.pack(side=tk.RIGHT)

        # 设置按钮
        if self.wake_word_detector:
            self.settings_btn = ttk.Button(
                right_controls,
                text="⚙️ 设置",
                command=self.show_wake_word_settings
            )
            self.settings_btn.pack(side=tk.LEFT, padx=(0, self.scale_size(5)))

        # 发送按钮
        self.send_button = ttk.Button(
            right_controls,
            text="📤 发送 (Ctrl+Enter)",
            command=self.send_message
        )
        self.send_button.pack(side=tk.LEFT)

    def create_conversation_list(self, parent):
        """创建对话历史列表"""
        # 计算自适应尺寸
        padding = self.scale_size(5)
        font_size = max(8, int(self.config.get("ui.font_size", 12) * self.dpi_scale))

        # 对话历史框架
        self.history_frame = ttk.LabelFrame(parent, text="📚 对话历史", padding=padding)
        parent.add(self.history_frame, weight=1)

        # 创建滚动条和列表框
        list_frame = ttk.Frame(self.history_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 对话列表
        self.conversation_listbox = tk.Listbox(
            list_frame,
            font=('Microsoft YaHei', font_size),
            selectmode=tk.SINGLE
        )

        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.conversation_listbox.yview)
        self.conversation_listbox.configure(yscrollcommand=v_scrollbar.set)

        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.conversation_listbox.xview)
        self.conversation_listbox.configure(xscrollcommand=h_scrollbar.set)

        # 布局
        self.conversation_listbox.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # 配置网格权重
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # 绑定双击事件
        self.conversation_listbox.bind("<Double-Button-1>", self.on_conversation_select)

        # 右键菜单
        self.create_conversation_context_menu()

        # 刷新对话列表
        self.refresh_conversation_list()
    
    def create_conversation_context_menu(self):
        """创建对话列表右键菜单"""
        self.conversation_menu = tk.Menu(self.root, tearoff=0)
        self.conversation_menu.add_command(label="📖 加载对话", command=self.load_selected_conversation)
        self.conversation_menu.add_command(label="✏️ 重命名", command=self.rename_conversation)
        self.conversation_menu.add_separator()
        self.conversation_menu.add_command(label="📤 导出", command=self.export_conversation)
        self.conversation_menu.add_command(label="🗑️ 删除", command=self.delete_conversation)
        
        # 绑定右键菜单
        self.conversation_listbox.bind("<Button-3>", self.show_conversation_menu)
    

    
    def configure_chat_tags(self):
        """配置对话显示的文本标签样式"""
        base_font_size = max(8, int(self.config.get("ui.font_size", 12) * self.dpi_scale))

        self.chat_display.tag_configure("user",
                                       foreground="#0066cc",
                                       font=('Microsoft YaHei', base_font_size, 'bold'))
        self.chat_display.tag_configure("assistant",
                                       foreground="#009900",
                                       font=('Microsoft YaHei', base_font_size))
        self.chat_display.tag_configure("system",
                                       foreground="#666666",
                                       font=('Microsoft YaHei', max(8, base_font_size - 1), 'italic'))
        self.chat_display.tag_configure("timestamp",
                                       foreground="#999999",
                                       font=('Microsoft YaHei', max(8, base_font_size - 2)))
        self.chat_display.tag_configure("status",
                                       foreground="#ff6600",
                                       font=('Microsoft YaHei', max(8, base_font_size - 1)))
    

    
    def create_status_bar(self):
        """创建状态栏"""
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # 配置状态
        self.config_status_var = tk.StringVar()
        self.config_status_label = ttk.Label(status_frame, textvariable=self.config_status_var)
        self.config_status_label.pack(side=tk.RIGHT)
    
    def bind_events(self):
        """绑定事件"""
        try:
            # 绑定Ctrl+Enter发送消息
            if hasattr(self, 'input_text') and self.input_text:
                self.input_text.bind("<Control-Return>", lambda e: self.send_message())
                self.input_text.bind("<KeyRelease>", self.on_input_change)

            # 绑定窗口关闭事件
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        except Exception as e:
            logging.error(f"绑定事件失败: {e}")
    
    def check_configuration(self):
        """检查配置状态"""
        # 检查API配置
        if self.config.is_api_configured():
            api_status = "✅ API已配置"
        else:
            api_status = "❌ API未配置"
        
        # 检查TTS状态
        tts_status = self.tts_manager.get_status()
        if tts_status["windows_tts_available"] or tts_status["edge_tts_available"]:
            tts_info = "✅ TTS可用"
        else:
            tts_info = "❌ TTS不可用"
        
        self.config_status_var.set(f"{api_status} | {tts_info}")
        
        # 如果API未配置，显示提示
        if not self.config.is_api_configured():
            self.show_api_config_prompt()
    
    def show_api_config_prompt(self):
        """显示API配置提示"""
        result = messagebox.askyesno(
            "配置提示",
            "检测到DeepSeek API未配置，是否现在配置？\n\n"
            "没有API密钥将无法使用AI对话功能。",
            icon="question"
        )
        
        if result:
            self.open_settings()
    
    def update_status(self, message: str):
        """更新状态栏"""
        self.status_var.set(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.root.update_idletasks()
    
    def update_processing_status(self, message: str = ""):
        """更新处理状态"""
        self.processing_label.config(text=message)
        self.root.update_idletasks()
    
    # 对话管理方法
    def new_conversation(self):
        """创建新对话"""
        self.conversation_manager.create_new_conversation()
        self.refresh_chat_display()
        self.refresh_conversation_list()
        self.update_status("创建新对话")
    
    def refresh_conversation_list(self):
        """刷新对话历史列表"""
        self.conversation_listbox.delete(0, tk.END)
        
        history = self.conversation_manager.get_conversation_history()
        for conv in history:
            title = conv["title"]
            message_count = conv["message_count"]
            updated_time = conv["updated_at"][:16].replace("T", " ")
            
            display_text = f"{title} ({message_count}条) - {updated_time}"
            self.conversation_listbox.insert(tk.END, display_text)
            
            # 存储对话ID
            self.conversation_listbox.insert(tk.END, conv["id"])
            self.conversation_listbox.delete(tk.END)  # 删除ID行，只保存在内存中
    
    def add_message_to_display(self, role: str, content: str):
        """添加消息到对话显示"""
        try:
            self.chat_display.config(state=tk.NORMAL)

            # 获取当前时间
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 根据角色设置样式
            if role == "user":
                prefix = f"[{timestamp}] 👤 您: "
                tag = "user"
            elif role == "assistant":
                prefix = f"[{timestamp}] 🤖 AI: "
                tag = "assistant"
            elif role == "system":
                prefix = f"[{timestamp}] 📢 系统: "
                tag = "system"
            else:
                prefix = f"[{timestamp}] {role}: "
                tag = "default"

            # 插入消息
            self.chat_display.insert(tk.END, prefix, tag)
            self.chat_display.insert(tk.END, content + "\n\n")

            # 滚动到底部
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)

        except Exception as e:
            logging.error(f"添加消息到显示失败: {e}")

    def refresh_chat_display(self):
        """刷新对话显示"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)

        if self.conversation_manager.current_conversation:
            messages = self.conversation_manager.current_conversation.messages
            
            for message in messages:
                if message.role == "system":
                    continue  # 不显示系统消息
                
                # 添加时间戳
                timestamp = message.timestamp[:16].replace("T", " ")
                self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
                
                # 添加角色标识和内容
                if message.role == "user":
                    self.chat_display.insert(tk.END, "👤 用户: ", "user")
                elif message.role == "assistant":
                    self.chat_display.insert(tk.END, "🤖 助手: ", "assistant")
                
                self.chat_display.insert(tk.END, f"{message.content}\n\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    # 消息处理方法
    def send_message(self):
        """发送消息"""
        if self.is_processing:
            messagebox.showwarning("提示", "正在处理中，请稍候...")
            return

        message = self.input_text.get(1.0, tk.END).strip()
        if not message:
            messagebox.showwarning("提示", "请输入消息内容")
            return

        if not self.config.is_api_configured():
            messagebox.showerror("错误", "请先配置DeepSeek API密钥")
            self.open_settings()
            return

        # 清空输入框
        self.input_text.delete(1.0, tk.END)

        # 如果启用了语音模式，使用语音管理器处理
        if self.voice_manager and self.voice_mode_enabled:
            self.voice_manager.process_text_input(message)
        else:
            # 在新线程中处理消息
            threading.Thread(target=self._process_message, args=(message,), daemon=True).start()

    def _process_message(self, message: str):
        """处理消息（在后台线程中运行）"""
        try:
            self.is_processing = True
            self.root.after(0, lambda: self.update_processing_status("🤔 正在思考..."))
            self.root.after(0, lambda: self.send_button.config(state=tk.DISABLED))

            # 添加用户消息
            self.conversation_manager.add_message("user", message)
            self.root.after(0, self.refresh_chat_display)

            # 获取对话历史
            messages = self.conversation_manager.get_conversation_messages()

            # 调用DeepSeek API
            self.root.after(0, lambda: self.update_processing_status("🌐 正在获取回复..."))

            if self.config.get("conversation.stream_mode", False):
                # 流式模式
                self._process_stream_response(messages)
            else:
                # 非流式模式
                response = self.deepseek_client.chat_completion(messages)

                if response["success"]:
                    assistant_message = response["content"]
                    token_count = response.get("usage", {}).get("total_tokens", 0)

                    # 添加助手消息
                    self.conversation_manager.add_message("assistant", assistant_message, token_count)
                    self.root.after(0, self.refresh_chat_display)

                    # 自动朗读
                    if self.auto_read_var.get():
                        self.root.after(0, lambda: self._speak_message(assistant_message))

                    self.root.after(0, lambda: self.update_status("回复完成"))
                else:
                    error_msg = f"API调用失败: {response['error']}"
                    self.root.after(0, lambda: self.update_status(error_msg))
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))

        except Exception as e:
            error_msg = f"处理消息失败: {e}"
            logging.error(error_msg)
            self.root.after(0, lambda: self.update_status(error_msg))
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))

        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.update_processing_status(""))
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))
            self.root.after(0, self.save_conversation_auto)

    def _process_stream_response(self, messages: list):
        """处理流式响应"""
        try:
            full_response = ""

            def stream_callback(chunk):
                nonlocal full_response
                if chunk["success"] and chunk["content"]:
                    full_response += chunk["content"]
                    # 实时更新显示（这里可以优化为增量更新）
                    self.root.after(0, lambda: self._update_streaming_display(full_response))

            # 异步处理流式响应
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                self.deepseek_client.chat_completion_stream_async(messages, stream_callback)
            )

            if result["success"]:
                # 添加完整的助手消息
                self.conversation_manager.add_message("assistant", full_response)
                self.root.after(0, self.refresh_chat_display)

                # 自动朗读
                if self.auto_read_var.get():
                    self.root.after(0, lambda: self._speak_message(full_response))

                self.root.after(0, lambda: self.update_status("流式回复完成"))
            else:
                error_msg = f"流式API调用失败: {result['error']}"
                self.root.after(0, lambda: self.update_status(error_msg))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))

        except Exception as e:
            error_msg = f"流式处理失败: {e}"
            logging.error(error_msg)
            self.root.after(0, lambda: self.update_status(error_msg))

    def _update_streaming_display(self, content: str):
        """更新流式显示"""
        # 这里可以实现实时更新显示的逻辑
        # 为了简化，暂时使用完整刷新
        pass

    def _speak_message(self, message: str):
        """朗读消息"""
        def tts_callback(status_info):
            status = status_info.get("status", "")
            message_text = status_info.get("message", "")

            if status == "starting":
                self.update_processing_status("🔊 开始朗读...")
            elif status == "synthesizing":
                self.update_processing_status("🎵 正在合成...")
            elif status == "playing":
                self.update_processing_status("🔊 正在播放...")
            elif status == "completed":
                self.update_processing_status("")
                self.update_status("朗读完成")
            elif status == "error":
                self.update_processing_status("")
                self.update_status(f"朗读失败: {message_text}")

        # 异步朗读
        def speak_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                self.tts_manager.speak_text_async(message, tts_callback)
            )

        threading.Thread(target=speak_async, daemon=True).start()

    def stop_speaking(self):
        """停止朗读"""
        self.tts_manager.stop_speaking()

        # 如果有语音管理器，也停止语音交互
        if self.voice_manager:
            self.voice_manager.stop_current_speech()

        self.update_processing_status("")
        self.update_status("朗读已停止")

    def clear_input(self):
        """清空输入框"""
        self.input_text.delete(1.0, tk.END)

    def toggle_auto_read(self):
        """切换自动朗读"""
        self.auto_read_enabled = self.auto_read_var.get()
        self.config.set("tts.auto_read", self.auto_read_enabled)
        self.config.save_config()

        status = "开启" if self.auto_read_enabled else "关闭"
        self.update_status(f"自动朗读已{status}")

    def update_knowledge_base_status(self):
        """更新知识库状态显示"""
        try:
            if not RAG_AVAILABLE:
                self.kb_status_label.config(text="📚 知识库: 不可用")
                return

            rag_system = get_rag_system()
            status = rag_system.get_knowledge_base_status()

            if status["available"]:
                doc_count = status["total_documents"]
                if doc_count > 0:
                    self.kb_status_label.config(
                        text=f"📚 知识库: {doc_count}个文档",
                        foreground="green"
                    )
                else:
                    self.kb_status_label.config(
                        text="📚 知识库: 空",
                        foreground="orange"
                    )
            else:
                self.kb_status_label.config(
                    text="📚 知识库: 错误",
                    foreground="red"
                )

        except Exception as e:
            logging.error(f"更新知识库状态失败: {e}")
            self.kb_status_label.config(
                text="📚 知识库: 错误",
                foreground="red"
            )

    # 对话历史管理
    def on_conversation_select(self, event):
        """对话选择事件"""
        self.load_selected_conversation()

    def load_selected_conversation(self):
        """加载选中的对话"""
        selection = self.conversation_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        history = self.conversation_manager.get_conversation_history()

        if index < len(history):
            conv_id = history[index]["id"]
            if self.conversation_manager.load_conversation(conv_id):
                self.refresh_chat_display()
                self.update_status(f"加载对话: {history[index]['title']}")

    def show_conversation_menu(self, event):
        """显示对话右键菜单"""
        # 选中右键点击的项目
        index = self.conversation_listbox.nearest(event.y)
        self.conversation_listbox.selection_clear(0, tk.END)
        self.conversation_listbox.selection_set(index)

        # 显示菜单
        try:
            self.conversation_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.conversation_menu.grab_release()

    def rename_conversation(self):
        """重命名对话"""
        selection = self.conversation_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        history = self.conversation_manager.get_conversation_history()

        if index < len(history):
            old_title = history[index]["title"]
            new_title = simpledialog.askstring("重命名对话", "请输入新的对话标题:", initialvalue=old_title)

            if new_title and new_title != old_title:
                conv_id = history[index]["id"]
                # 加载对话并重命名
                if self.conversation_manager.load_conversation(conv_id):
                    self.conversation_manager.update_conversation_title(new_title)
                    self.refresh_conversation_list()
                    self.update_status(f"对话已重命名: {new_title}")

    def delete_conversation(self):
        """删除对话"""
        selection = self.conversation_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        history = self.conversation_manager.get_conversation_history()

        if index < len(history):
            title = history[index]["title"]
            result = messagebox.askyesno("确认删除", f"确定要删除对话 '{title}' 吗？\n\n此操作不可撤销。")

            if result:
                conv_id = history[index]["id"]
                if self.conversation_manager.delete_conversation(conv_id):
                    self.refresh_conversation_list()
                    # 如果删除的是当前对话，清空显示
                    if (self.conversation_manager.current_conversation is None or
                        self.conversation_manager.current_conversation.id == conv_id):
                        self.refresh_chat_display()
                    self.update_status(f"对话已删除: {title}")

    def export_conversation(self):
        """导出对话"""
        selection = self.conversation_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        history = self.conversation_manager.get_conversation_history()

        if index < len(history):
            conv_id = history[index]["id"]
            title = history[index]["title"]

            filename = filedialog.asksaveasfilename(
                title="导出对话",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialvalue=f"{title}.json"
            )

            if filename:
                if self.conversation_manager.export_conversation(conv_id, filename):
                    self.update_status(f"对话已导出: {filename}")
                    messagebox.showinfo("成功", f"对话已导出到:\n{filename}")
                else:
                    messagebox.showerror("错误", "导出对话失败")

    def load_conversation(self):
        """加载对话文件"""
        filename = filedialog.askopenfilename(
            title="加载对话",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if filename:
            if self.conversation_manager.import_conversation(filename):
                self.refresh_conversation_list()
                self.update_status(f"对话已导入: {Path(filename).name}")
                messagebox.showinfo("成功", f"对话已从以下文件导入:\n{filename}")
            else:
                messagebox.showerror("错误", "导入对话失败")

    def save_conversation(self):
        """手动保存对话"""
        if self.conversation_manager.save_history():
            self.update_status("对话已保存")
        else:
            messagebox.showerror("错误", "保存对话失败")

    def save_conversation_auto(self):
        """自动保存对话"""
        if self.config.get("conversation.save_history", True):
            self.conversation_manager.save_history()

    # 事件处理
    def on_input_change(self, event):
        """输入框内容变化事件"""
        # 可以在这里添加实时功能，如字数统计等
        pass

    # 语音控制方法
    def toggle_voice_mode(self):
        """切换语音模式"""
        if not self.voice_manager:
            messagebox.showwarning("功能不可用", "语音识别功能不可用，请检查依赖包安装")
            return

        try:
            if not self.voice_mode_enabled:
                # 启用连续语音模式
                self.voice_manager.set_voice_mode(self.VoiceMode.CONTINUOUS)
                self.voice_manager.start_voice_interaction()
                self.voice_mode_enabled = True
                if hasattr(self, 'voice_btn'):
                    self.voice_btn.config(text="🔇 关闭语音")
                self.update_status("🎤 连续语音模式已启用")
            else:
                # 禁用语音模式
                self.voice_manager.set_voice_mode(self.VoiceMode.DISABLED)
                self.voice_manager.stop_voice_interaction()
                self.voice_mode_enabled = False
                if hasattr(self, 'voice_btn'):
                    self.voice_btn.config(text="🎤 语音")
                self.update_status("语音模式已禁用")

        except Exception as e:
            logging.error(f"切换语音模式失败: {e}")
            messagebox.showerror("语音错误", f"切换语音模式失败: {e}")

    def start_push_to_talk(self):
        """开始按键说话"""
        if not self.voice_manager:
            messagebox.showwarning("功能不可用", "语音识别功能不可用，请检查依赖包安装")
            return

        try:
            # 设置为按键说话模式
            self.voice_manager.set_voice_mode(self.VoiceMode.PUSH_TO_TALK)
            self.voice_manager.start_voice_interaction()

            # 开始单次录音
            self.update_status("🎤 请开始说话...")

            # 在新线程中进行录音
            threading.Thread(target=self._record_once_thread, daemon=True).start()

        except Exception as e:
            logging.error(f"按键说话失败: {e}")
            messagebox.showerror("语音错误", f"按键说话失败: {e}")

    def _record_once_thread(self):
        """单次录音线程"""
        try:
            text = self.voice_manager.record_once(timeout=10.0)
            if text:
                self.root.after(0, lambda: self.update_status(f"识别到: {text}"))
            else:
                self.root.after(0, lambda: self.update_status("未识别到语音"))
        except Exception as e:
            logging.error(f"录音线程异常: {e}")
            self.root.after(0, lambda: self.update_status(f"录音失败: {e}"))

    def toggle_wake_word_detection(self):
        """切换语音唤醒词检测"""
        if not self.wake_word_detector:
            messagebox.showwarning("功能不可用", "语音唤醒功能不可用，请检查依赖包安装")
            return

        try:
            if not self.wake_word_enabled:
                # 启用唤醒词检测
                success = self.wake_word_detector.start_detection()
                if success:
                    self.wake_word_enabled = True
                    if hasattr(self, 'wake_word_btn'):
                        self.wake_word_btn.config(text="🔇 关闭唤醒")
                    self.update_status("🎤 语音唤醒已启用 - 说'你好文犀'或'文犀出来'来唤醒")
                    self.add_message_to_display("system", "🎤 语音唤醒已启用，支持的唤醒词：\n• 你好文犀\n• 文犀出来\n• 文犀醒醒\n• 嗨文犀")
                else:
                    messagebox.showerror("启动失败", "无法启动语音唤醒检测")
            else:
                # 禁用唤醒词检测
                self.wake_word_detector.stop_detection()
                self.wake_word_enabled = False
                if hasattr(self, 'wake_word_btn'):
                    self.wake_word_btn.config(text="🔊 唤醒词")
                self.update_status("语音唤醒已禁用")
                self.add_message_to_display("system", "🔇 语音唤醒已禁用")

        except Exception as e:
            logging.error(f"切换语音唤醒失败: {e}")
            messagebox.showerror("唤醒错误", f"切换语音唤醒失败: {e}")

    def show_wake_word_settings(self):
        """显示唤醒词设置窗口"""
        if not self.wake_word_detector:
            messagebox.showwarning("功能不可用", "语音唤醒功能不可用")
            return

        try:
            # 创建设置窗口
            settings_window = tk.Toplevel(self.root)
            settings_window.title("语音唤醒设置")
            settings_window.geometry("400x500")
            settings_window.transient(self.root)
            settings_window.grab_set()

            # 当前状态
            status_frame = ttk.LabelFrame(settings_window, text="当前状态", padding=10)
            status_frame.pack(fill=tk.X, padx=10, pady=5)

            status = self.wake_word_detector.get_status()
            status_text = f"""
检测状态: {'运行中' if status['is_active'] else '已停止'}
检测次数: {status['detection_count']}
唤醒词数量: {status['wake_words_count']}
语音识别: {'可用' if status['speech_recognition_available'] else '不可用'}
"""
            ttk.Label(status_frame, text=status_text).pack(anchor=tk.W)

            # 唤醒词列表
            words_frame = ttk.LabelFrame(settings_window, text="支持的唤醒词", padding=10)
            words_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            # 创建滚动文本框
            text_widget = tk.Text(words_frame, height=15, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(words_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)

            # 显示唤醒词
            wake_words = self.wake_word_detector.get_wake_words()
            for i, word in enumerate(wake_words, 1):
                text_widget.insert(tk.END, f"{i}. {word}\n")

            text_widget.config(state=tk.DISABLED)
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 控制按钮
            button_frame = ttk.Frame(settings_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)

            ttk.Button(
                button_frame,
                text="关闭",
                command=settings_window.destroy
            ).pack(side=tk.RIGHT)

        except Exception as e:
            logging.error(f"显示唤醒词设置失败: {e}")
            messagebox.showerror("设置错误", f"显示唤醒词设置失败: {e}")

    # 文件管理功能
    def open_file_management(self):
        """打开文件管理窗口"""
        try:
            from file_management_ui import show_file_management_window
            show_file_management_window(self.root, callback=self.update_knowledge_base_status)
        except Exception as e:
            logging.error(f"打开文件管理失败: {e}")
            messagebox.showerror("错误", f"打开文件管理失败: {e}")

    def upload_files(self):
        """上传文件"""
        try:
            if not self.file_manager:
                messagebox.showwarning("功能不可用", "文件管理功能不可用")
                return

            # 获取支持的文件类型
            supported_formats = self.file_manager.get_supported_formats()

            # 构建文件类型过滤器
            filetypes = [
                ("所有支持的文件", " ".join([
                    f"*{ext}" for ext in {**supported_formats["documents"], **supported_formats["images"]}.keys()
                ])),
                ("文档文件", " ".join([f"*{ext}" for ext in supported_formats["documents"].keys()])),
                ("图片文件", " ".join([f"*{ext}" for ext in supported_formats["images"].keys()])),
                ("所有文件", "*.*")
            ]

            # 选择文件
            file_paths = filedialog.askopenfilenames(
                title="选择要上传的文件",
                filetypes=filetypes
            )

            if file_paths:
                self.upload_files_async(file_paths)

        except Exception as e:
            logging.error(f"上传文件失败: {e}")
            messagebox.showerror("错误", f"上传文件失败: {e}")

    def upload_files_async(self, file_paths):
        """异步上传文件"""
        def upload_worker():
            try:
                success_count = 0
                total_count = len(file_paths)

                for i, file_path in enumerate(file_paths):
                    # 更新状态
                    self.root.after(0, lambda: self.update_status(f"上传中... ({i+1}/{total_count})"))

                    # 上传文件
                    result = self.file_manager.upload_file(file_path)

                    if result["success"]:
                        success_count += 1
                        # 在对话中显示上传的文件
                        file_info = result["file_info"]
                        self.root.after(0, lambda: self.add_file_to_conversation(file_info))
                    else:
                        logging.error(f"上传文件失败: {result['error']}")

                # 更新状态
                self.root.after(0, lambda: self.update_status(f"上传完成: {success_count}/{total_count} 个文件"))

                if success_count < total_count:
                    self.root.after(0, lambda: messagebox.showwarning(
                        "上传完成", f"成功上传 {success_count}/{total_count} 个文件"
                    ))

            except Exception as e:
                logging.error(f"异步上传文件失败: {e}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"上传失败: {e}"))

        # 在新线程中执行上传
        threading.Thread(target=upload_worker, daemon=True).start()

    def paste_from_clipboard(self):
        """从剪贴板粘贴"""
        try:
            if not self.clipboard_manager:
                messagebox.showwarning("功能不可用", "剪贴板管理功能不可用")
                return

            content_type = self.clipboard_manager.get_clipboard_content_type()

            if content_type == "text":
                text = self.clipboard_manager.get_text_from_clipboard()
                if text:
                    # 粘贴到输入框
                    if hasattr(self, 'input_text') and self.input_text:
                        self.input_text.insert(tk.INSERT, text)
                        self.update_status("文本已粘贴")
                    else:
                        messagebox.showinfo("提示", "输入框不可用")
                else:
                    messagebox.showinfo("提示", "剪贴板中没有文本内容")

            elif content_type == "image":
                image_info = self.clipboard_manager.get_image_from_clipboard()
                if image_info:
                    # 上传剪贴板图片
                    result = self.file_manager.upload_file(image_info["path"], "剪贴板图片")
                    if result["success"]:
                        file_info = result["file_info"]
                        self.add_file_to_conversation(file_info)
                        self.update_status("剪贴板图片已添加")
                    else:
                        messagebox.showerror("错误", f"上传剪贴板图片失败: {result['error']}")
                else:
                    messagebox.showinfo("提示", "剪贴板中没有图片内容")

            else:
                messagebox.showinfo("提示", "剪贴板中没有支持的内容")

        except Exception as e:
            logging.error(f"粘贴剪贴板内容失败: {e}")
            messagebox.showerror("错误", f"粘贴失败: {e}")

    def add_file_to_conversation(self, file_info):
        """在对话中添加文件"""
        try:
            # 在对话显示中添加文件信息
            file_type_icon = "📄" if file_info["file_type"] == "document" else "🖼️"
            file_message = f"{file_type_icon} 已上传文件: {file_info['filename']}"

            self.add_message_to_display("system", file_message)

        except Exception as e:
            logging.error(f"添加文件到对话失败: {e}")

    # 模型管理功能
    def open_model_management(self):
        """打开模型管理窗口"""
        try:
            from model_management_ui import show_model_management_window
            show_model_management_window(self.root)
        except Exception as e:
            logging.error(f"打开模型管理失败: {e}")
            messagebox.showerror("错误", f"打开模型管理失败: {e}")

    def open_knowledge_base_management(self):
        """打开知识库管理窗口"""
        try:
            from knowledge_base_ui import show_knowledge_base_window
            show_knowledge_base_window(self.root)
        except Exception as e:
            logging.error(f"打开知识库管理失败: {e}")
            messagebox.showerror("错误", f"打开知识库管理失败: {e}")

    def on_closing(self):
        """窗口关闭事件"""
        # 停止所有正在进行的操作
        self.stop_speaking()

        # 保存对话
        self.save_conversation_auto()

        # 保存窗口状态
        self.save_window_state()

        # 关闭窗口
        self.root.destroy()

    # 设置和关于对话框
    def open_settings(self):
        """打开设置对话框"""
        SettingsDialog(self.root, self.config, self.on_settings_changed)

    def on_settings_changed(self):
        """设置更改回调"""
        # 重新初始化客户端
        self.deepseek_client.update_config()

        # 更新配置状态
        self.check_configuration()

        # 更新字体大小
        font_size = self.config.get("ui.font_size", 12)
        self.chat_display.config(font=('Microsoft YaHei', font_size))
        self.input_text.config(font=('Microsoft YaHei', font_size))
        self.configure_chat_tags()

        self.update_status("设置已更新")

    def show_about(self):
        """显示关于对话框"""
        AboutDialog(self.root)

class SettingsDialog:
    """设置对话框"""

    def __init__(self, parent, config, callback=None):
        self.config = config
        self.callback = callback
        self.parent = parent

        # 获取父窗口的DPI缩放信息
        if hasattr(parent, 'dpi_scale'):
            self.dpi_scale = parent.dpi_scale
        else:
            self.dpi_scale = 1.0

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("⚙️ 设置")

        # 计算自适应大小
        width, height = self.get_adaptive_dialog_size()
        self.dialog.geometry(f"{width}x{height}")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 设置最小尺寸
        min_width = self.scale_size(500)
        min_height = self.scale_size(400)
        self.dialog.minsize(min_width, min_height)

        # 居中显示
        self.center_window()

        # 创建界面
        self.create_widgets()

        # 加载当前配置
        self.load_current_config()

    def scale_size(self, size):
        """根据DPI缩放尺寸"""
        return int(size * self.dpi_scale)

    def get_adaptive_dialog_size(self):
        """获取自适应对话框大小"""
        # 获取父窗口信息
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        # 计算合适的对话框大小（父窗口的80%）
        width = min(self.scale_size(700), int(parent_width * 0.8))
        height = min(self.scale_size(600), int(parent_height * 0.8))

        # 确保最小尺寸
        width = max(width, self.scale_size(500))
        height = max(height, self.scale_size(400))

        return width, height

    def center_window(self):
        """窗口居中"""
        self.dialog.update_idletasks()

        # 获取对话框和屏幕尺寸
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2

        # 确保窗口在屏幕范围内
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))

        self.dialog.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """创建设置界面组件"""
        # 创建Notebook
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # API设置标签页
        self.create_api_tab(notebook)

        # TTS设置标签页
        self.create_tts_tab(notebook)

        # 界面设置标签页
        self.create_ui_tab(notebook)

        # 对话设置标签页
        self.create_conversation_tab(notebook)

        # 按钮区域
        self.create_buttons()

    def create_api_tab(self, notebook):
        """创建API设置标签页"""
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="🌐 API设置")

        # API密钥
        ttk.Label(api_frame, text="DeepSeek API密钥:").pack(anchor=tk.W, pady=(10, 5))
        self.api_key_var = tk.StringVar()
        api_key_frame = ttk.Frame(api_frame)
        api_key_frame.pack(fill=tk.X, pady=(0, 10))

        self.api_key_entry = ttk.Entry(api_key_frame, textvariable=self.api_key_var, show="*", width=50)
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(api_key_frame, text="👁️", width=3,
                  command=self.toggle_api_key_visibility).pack(side=tk.RIGHT, padx=(5, 0))

        # 基础URL
        ttk.Label(api_frame, text="API基础URL:").pack(anchor=tk.W, pady=(10, 5))
        self.base_url_var = tk.StringVar()
        ttk.Entry(api_frame, textvariable=self.base_url_var, width=50).pack(fill=tk.X, pady=(0, 10))

        # 模型设置
        ttk.Label(api_frame, text="模型:").pack(anchor=tk.W, pady=(10, 5))
        self.model_var = tk.StringVar()
        model_combo = ttk.Combobox(api_frame, textvariable=self.model_var,
                                  values=["deepseek-chat", "deepseek-coder"], state="readonly")
        model_combo.pack(fill=tk.X, pady=(0, 10))

        # 高级设置
        advanced_frame = ttk.LabelFrame(api_frame, text="高级设置", padding=10)
        advanced_frame.pack(fill=tk.X, pady=(10, 0))

        # 最大令牌数
        ttk.Label(advanced_frame, text="最大令牌数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.max_tokens_var = tk.IntVar()
        ttk.Spinbox(advanced_frame, from_=100, to=4000, textvariable=self.max_tokens_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 温度
        ttk.Label(advanced_frame, text="温度 (0.0-2.0):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.temperature_var = tk.DoubleVar()
        ttk.Spinbox(advanced_frame, from_=0.0, to=2.0, increment=0.1, textvariable=self.temperature_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # 超时时间
        ttk.Label(advanced_frame, text="超时时间(秒):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.IntVar()
        ttk.Spinbox(advanced_frame, from_=10, to=120, textvariable=self.timeout_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # 测试连接按钮
        ttk.Button(api_frame, text="🔗 测试连接", command=self.test_api_connection).pack(pady=(20, 0))

    def create_tts_tab(self, notebook):
        """创建TTS设置标签页"""
        tts_frame = ttk.Frame(notebook)
        notebook.add(tts_frame, text="🔊 语音设置")

        # TTS引擎选择
        ttk.Label(tts_frame, text="TTS引擎:").pack(anchor=tk.W, pady=(10, 5))
        self.tts_engine_var = tk.StringVar()
        engine_frame = ttk.Frame(tts_frame)
        engine_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Radiobutton(engine_frame, text="Edge TTS (推荐)", variable=self.tts_engine_var,
                       value="edge").pack(side=tk.LEFT)
        ttk.Radiobutton(engine_frame, text="Windows TTS", variable=self.tts_engine_var,
                       value="windows").pack(side=tk.LEFT, padx=(20, 0))

        # 语音选择
        voice_frame = ttk.LabelFrame(tts_frame, text="语音选择", padding=10)
        voice_frame.pack(fill=tk.X, pady=(10, 0))

        # 中文语音
        ttk.Label(voice_frame, text="中文语音:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.chinese_voice_var = tk.StringVar()
        chinese_voices = ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunyangNeural", "zh-CN-XiaoyiNeural"]
        ttk.Combobox(voice_frame, textvariable=self.chinese_voice_var, values=chinese_voices,
                    state="readonly", width=25).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 英文语音
        ttk.Label(voice_frame, text="英文语音:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.english_voice_var = tk.StringVar()
        english_voices = ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural", "en-GB-SoniaNeural"]
        ttk.Combobox(voice_frame, textvariable=self.english_voice_var, values=english_voices,
                    state="readonly", width=25).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # 语音参数
        params_frame = ttk.LabelFrame(tts_frame, text="语音参数", padding=10)
        params_frame.pack(fill=tk.X, pady=(10, 0))

        # 语速
        ttk.Label(params_frame, text="语速 (0-10):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.rate_var = tk.IntVar()
        ttk.Scale(params_frame, from_=0, to=10, variable=self.rate_var, orient=tk.HORIZONTAL,
                 length=200).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 音量
        ttk.Label(params_frame, text="音量 (0-100):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.volume_var = tk.IntVar()
        ttk.Scale(params_frame, from_=0, to=100, variable=self.volume_var, orient=tk.HORIZONTAL,
                 length=200).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # 自动朗读
        self.auto_read_var = tk.BooleanVar()
        ttk.Checkbutton(tts_frame, text="自动朗读AI回复", variable=self.auto_read_var).pack(anchor=tk.W, pady=(20, 0))

        # 测试语音按钮
        ttk.Button(tts_frame, text="🎵 测试语音", command=self.test_tts).pack(pady=(20, 0))

    def create_ui_tab(self, notebook):
        """创建界面设置标签页"""
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="🎨 界面设置")

        # 字体大小
        ttk.Label(ui_frame, text="字体大小:").pack(anchor=tk.W, pady=(10, 5))
        self.font_size_var = tk.IntVar()
        ttk.Spinbox(ui_frame, from_=8, to=24, textvariable=self.font_size_var, width=10).pack(anchor=tk.W, pady=(0, 10))

        # 自动滚动
        self.auto_scroll_var = tk.BooleanVar()
        ttk.Checkbutton(ui_frame, text="自动滚动到最新消息", variable=self.auto_scroll_var).pack(anchor=tk.W, pady=(10, 0))

    def create_conversation_tab(self, notebook):
        """创建对话设置标签页"""
        conv_frame = ttk.Frame(notebook)
        notebook.add(conv_frame, text="💬 对话设置")

        # 系统提示
        ttk.Label(conv_frame, text="系统提示:").pack(anchor=tk.W, pady=(10, 5))
        self.system_prompt_text = scrolledtext.ScrolledText(conv_frame, height=6, wrap=tk.WORD)
        self.system_prompt_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 对话设置
        settings_frame = ttk.LabelFrame(conv_frame, text="对话设置", padding=10)
        settings_frame.pack(fill=tk.X, pady=(10, 0))

        # 最大历史记录
        ttk.Label(settings_frame, text="最大历史记录数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.max_history_var = tk.IntVar()
        ttk.Spinbox(settings_frame, from_=10, to=1000, textvariable=self.max_history_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 保存历史
        self.save_history_var = tk.BooleanVar()
        ttk.Checkbutton(settings_frame, text="自动保存对话历史", variable=self.save_history_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 流式模式
        self.stream_mode_var = tk.BooleanVar()
        ttk.Checkbutton(settings_frame, text="启用流式对话模式", variable=self.stream_mode_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)

    def create_buttons(self):
        """创建按钮区域"""
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="💾 保存", command=self.save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="❌ 取消", command=self.dialog.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="🔄 重置", command=self.reset_settings).pack(side=tk.LEFT)

    def load_current_config(self):
        """加载当前配置"""
        # API设置
        api_config = self.config.get_api_config()
        self.api_key_var.set(api_config.get("deepseek_api_key", ""))
        self.base_url_var.set(api_config.get("base_url", "https://api.deepseek.com"))
        self.model_var.set(api_config.get("model", "deepseek-chat"))
        self.max_tokens_var.set(api_config.get("max_tokens", 2000))
        self.temperature_var.set(api_config.get("temperature", 0.7))
        self.timeout_var.set(api_config.get("timeout", 30))

        # TTS设置
        tts_config = self.config.get_tts_config()
        self.tts_engine_var.set(tts_config.get("engine", "edge"))
        voice_config = tts_config.get("voice", {})
        self.chinese_voice_var.set(voice_config.get("chinese", "zh-CN-XiaoxiaoNeural"))
        self.english_voice_var.set(voice_config.get("english", "en-US-JennyNeural"))
        self.rate_var.set(tts_config.get("rate", 5))
        self.volume_var.set(tts_config.get("volume", 80))
        self.auto_read_var.set(tts_config.get("auto_read", True))

        # UI设置
        ui_config = self.config.get_ui_config()
        self.font_size_var.set(ui_config.get("font_size", 12))
        self.auto_scroll_var.set(ui_config.get("auto_scroll", True))

        # 对话设置
        conv_config = self.config.get_conversation_config()
        self.system_prompt_text.insert(1.0, conv_config.get("system_prompt", ""))
        self.max_history_var.set(conv_config.get("max_history", 50))
        self.save_history_var.set(conv_config.get("save_history", True))
        self.stream_mode_var.set(conv_config.get("stream_mode", False))

    def save_settings(self):
        """保存设置"""
        try:
            # 保存API设置
            self.config.set("api.deepseek_api_key", self.api_key_var.get())
            self.config.set("api.base_url", self.base_url_var.get())
            self.config.set("api.model", self.model_var.get())
            self.config.set("api.max_tokens", self.max_tokens_var.get())
            self.config.set("api.temperature", self.temperature_var.get())
            self.config.set("api.timeout", self.timeout_var.get())

            # 保存TTS设置
            self.config.set("tts.engine", self.tts_engine_var.get())
            self.config.set("tts.voice.chinese", self.chinese_voice_var.get())
            self.config.set("tts.voice.english", self.english_voice_var.get())
            self.config.set("tts.rate", self.rate_var.get())
            self.config.set("tts.volume", self.volume_var.get())
            self.config.set("tts.auto_read", self.auto_read_var.get())

            # 保存UI设置
            self.config.set("ui.font_size", self.font_size_var.get())
            self.config.set("ui.auto_scroll", self.auto_scroll_var.get())

            # 保存对话设置
            system_prompt = self.system_prompt_text.get(1.0, tk.END).strip()
            self.config.set("conversation.system_prompt", system_prompt)
            self.config.set("conversation.max_history", self.max_history_var.get())
            self.config.set("conversation.save_history", self.save_history_var.get())
            self.config.set("conversation.stream_mode", self.stream_mode_var.get())

            # 保存配置文件
            if self.config.save_config():
                messagebox.showinfo("成功", "设置已保存")
                if self.callback:
                    self.callback()
                self.dialog.destroy()
            else:
                messagebox.showerror("错误", "保存设置失败")

        except Exception as e:
            messagebox.showerror("错误", f"保存设置时发生错误: {e}")

    def reset_settings(self):
        """重置设置"""
        result = messagebox.askyesno("确认重置", "确定要重置所有设置为默认值吗？\n\n注意：API密钥将被保留。")
        if result:
            if self.config.reset_to_default():
                messagebox.showinfo("成功", "设置已重置为默认值")
                self.load_current_config()
            else:
                messagebox.showerror("错误", "重置设置失败")

    def toggle_api_key_visibility(self):
        """切换API密钥可见性"""
        if self.api_key_entry.cget("show") == "*":
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")

    def test_api_connection(self):
        """测试API连接"""
        # 临时更新配置
        old_config = {
            "api_key": self.config.get("api.deepseek_api_key"),
            "base_url": self.config.get("api.base_url"),
            "model": self.config.get("api.model"),
            "timeout": self.config.get("api.timeout")
        }

        # 设置新配置
        self.config.set("api.deepseek_api_key", self.api_key_var.get())
        self.config.set("api.base_url", self.base_url_var.get())
        self.config.set("api.model", self.model_var.get())
        self.config.set("api.timeout", self.timeout_var.get())

        try:
            # 重新初始化客户端
            from deepseek_client import get_deepseek_client
            client = get_deepseek_client()
            client.update_config()

            # 测试连接
            result = client.test_connection()

            if result["success"]:
                messagebox.showinfo("连接成功",
                    f"API连接测试成功！\n\n"
                    f"响应时间: {result['response_time']}秒\n"
                    f"模型: {result['model']}\n"
                    f"使用令牌: {result['tokens_used']}\n\n"
                    f"回复预览: {result['content_preview']}")
            else:
                messagebox.showerror("连接失败",
                    f"API连接测试失败！\n\n"
                    f"错误信息: {result['error']}\n"
                    f"响应时间: {result.get('response_time', 'N/A')}秒")

        except Exception as e:
            messagebox.showerror("测试异常", f"连接测试过程中发生异常:\n{e}")

        finally:
            # 恢复原配置
            self.config.set("api.deepseek_api_key", old_config["api_key"])
            self.config.set("api.base_url", old_config["base_url"])
            self.config.set("api.model", old_config["model"])
            self.config.set("api.timeout", old_config["timeout"])

    def test_tts(self):
        """测试TTS"""
        try:
            from smart_tts_manager import get_smart_tts_manager
            tts_manager = get_smart_tts_manager()

            # 根据选择的语音进行测试
            if self.tts_engine_var.get() == "edge":
                # 测试中文语音
                chinese_voice = self.chinese_voice_var.get()
                result = tts_manager.test_voice(chinese_voice, "edge")

                if result["success"]:
                    messagebox.showinfo("测试成功", f"Edge TTS中文语音测试成功！\n语音: {chinese_voice}")
                else:
                    messagebox.showerror("测试失败", f"Edge TTS测试失败: {result.get('error', '未知错误')}")
            else:
                # 测试Windows TTS
                result = tts_manager.test_voice("", "windows")

                if result["success"]:
                    messagebox.showinfo("测试成功", "Windows TTS语音测试成功！")
                else:
                    messagebox.showerror("测试失败", f"Windows TTS测试失败: {result.get('error', '未知错误')}")

        except Exception as e:
            messagebox.showerror("测试异常", f"TTS测试过程中发生异常:\n{e}")

class AboutDialog:
    """关于对话框"""

    def __init__(self, parent):
        self.parent = parent

        # 获取父窗口的DPI缩放信息
        if hasattr(parent, 'dpi_scale'):
            self.dpi_scale = parent.dpi_scale
        else:
            self.dpi_scale = 1.0

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("ℹ️ 关于")

        # 计算自适应大小
        width = self.scale_size(500)
        height = self.scale_size(450)
        self.dialog.geometry(f"{width}x{height}")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 设置最小尺寸
        min_width = self.scale_size(400)
        min_height = self.scale_size(350)
        self.dialog.minsize(min_width, min_height)

        # 居中显示
        self.center_window()

        # 创建内容
        self.create_content()

    def scale_size(self, size):
        """根据DPI缩放尺寸"""
        return int(size * self.dpi_scale)

    def center_window(self):
        """窗口居中"""
        self.dialog.update_idletasks()

        # 获取对话框和屏幕尺寸
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        # 计算居中位置
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2

        # 确保窗口在屏幕范围内
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))

        self.dialog.geometry(f"+{x}+{y}")

    def create_content(self):
        """创建关于内容"""
        padding = self.scale_size(20)
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)

        # 计算自适应字体大小
        title_font_size = max(12, self.scale_size(16))
        normal_font_size = max(10, self.scale_size(12))
        small_font_size = max(8, self.scale_size(10))

        # 标题
        title_label = ttk.Label(main_frame, text="🤖 智能语音助手",
                               font=('Microsoft YaHei', title_font_size, 'bold'))
        title_label.pack(pady=(0, self.scale_size(10)))

        # 版本信息
        version_label = ttk.Label(main_frame, text="AI Voice Assistant v1.0.0",
                                 font=('Microsoft YaHei', normal_font_size))
        version_label.pack(pady=(0, self.scale_size(20)))

        # 功能介绍
        features_text = """🎯 主要功能:
• 集成DeepSeek大语言模型进行智能对话
• 支持Edge TTS和Windows TTS双引擎语音合成
• 智能语言检测和语音选择
• 对话历史管理和导入导出
• 流式对话和实时语音播放
• 丰富的配置选项和个性化设置

🔧 技术特性:
• 基于OpenAI SDK的API调用
• 异步处理和多线程优化
• 完善的错误处理和重试机制
• 模块化设计，易于扩展

💡 使用建议:
• 配置DeepSeek API密钥以启用AI对话
• 推荐使用Edge TTS获得更好的语音质量
• 开启自动朗读体验完整的语音交互"""

        features_label = ttk.Label(main_frame, text=features_text,
                                  font=('Microsoft YaHei', small_font_size), justify=tk.LEFT)
        features_label.pack(fill=tk.BOTH, expand=True, pady=(0, self.scale_size(20)))

        # 技术信息
        tech_info = """🛠️ 技术栈:
Python 3.7+ | tkinter | OpenAI SDK | Edge TTS | asyncio"""

        tech_label = ttk.Label(main_frame, text=tech_info,
                              font=('Microsoft YaHei', max(8, small_font_size - 1)), foreground="#666666")
        tech_label.pack(pady=(0, self.scale_size(20)))

        # 关闭按钮
        button_width = max(8, self.scale_size(10))
        ttk.Button(main_frame, text="确定", width=button_width, command=self.dialog.destroy).pack()

def main():
    """主函数"""
    # 设置高DPI支持
    try:
        from ctypes import windll
        # 设置DPI感知
        windll.shcore.SetProcessDpiAwareness(1)
        # 设置DPI缩放模式
        windll.user32.SetProcessDPIAware()
    except Exception as e:
        logging.debug(f"设置DPI支持失败: {e}")

    # 创建主窗口
    root = tk.Tk()

    # 设置tkinter的DPI缩放
    try:
        root.tk.call('tk', 'scaling', root.winfo_fpixels('1i') / 72.0)
    except:
        pass

    # 创建应用实例
    app = AIVoiceAssistant(root)

    # 启动主循环
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logging.info("用户中断程序")
        app.on_closing()
    except Exception as e:
        logging.error(f"程序运行异常: {e}")
        app.on_closing()

if __name__ == "__main__":
    main()
