#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型管理界面
提供AI模型配置、管理和切换的图形界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import asyncio
from typing import Optional, Dict, Any
import logging

from model_manager import get_model_manager, ModelConfig

class ModelManagementWindow:
    """模型管理窗口"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.model_manager = get_model_manager()
        
        # 创建窗口
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("🤖 模型管理")
        self.window.geometry("1000x700")
        self.window.minsize(900, 600)
        
        # 设置窗口属性
        self.window.transient(parent)
        if parent:
            self.window.grab_set()
        
        # 创建界面
        self.create_widgets()
        self.refresh_model_list()
        
        logging.info("模型管理窗口创建成功")
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部工具栏
        self.create_toolbar(main_frame)
        
        # 主内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 左侧模型列表
        self.create_model_list(content_frame)
        
        # 右侧配置区域
        self.create_config_area(content_frame)
        
        # 底部状态栏
        self.create_status_bar(main_frame)
    
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X)
        
        # 左侧按钮
        left_buttons = ttk.Frame(toolbar_frame)
        left_buttons.pack(side=tk.LEFT)
        
        # 添加模型按钮
        self.add_btn = ttk.Button(
            left_buttons,
            text="➕ 添加模型",
            command=self.add_model
        )
        self.add_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 编辑模型按钮
        self.edit_btn = ttk.Button(
            left_buttons,
            text="✏️ 编辑",
            command=self.edit_selected_model,
            state=tk.DISABLED
        )
        self.edit_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 删除模型按钮
        self.delete_btn = ttk.Button(
            left_buttons,
            text="🗑️ 删除",
            command=self.delete_selected_model,
            state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 测试连接按钮
        self.test_btn = ttk.Button(
            left_buttons,
            text="🔗 测试连接",
            command=self.test_selected_model,
            state=tk.DISABLED
        )
        self.test_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 右侧按钮
        right_buttons = ttk.Frame(toolbar_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(
            right_buttons,
            text="🔄 刷新",
            command=self.refresh_model_list
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 当前模型显示
        current_frame = ttk.Frame(right_buttons)
        current_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(current_frame, text="当前模型:").pack(side=tk.LEFT)
        self.current_model_var = tk.StringVar()
        self.current_model_label = ttk.Label(
            current_frame, 
            textvariable=self.current_model_var,
            foreground="blue",
            font=('Microsoft YaHei', 9, 'bold')
        )
        self.current_model_label.pack(side=tk.LEFT, padx=(5, 0))
    
    def create_model_list(self, parent):
        """创建模型列表"""
        # 左侧框架
        left_frame = ttk.LabelFrame(parent, text="🤖 模型列表", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 创建Treeview
        columns = ("name", "provider", "model", "status")
        self.model_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        self.model_tree.heading("name", text="显示名称")
        self.model_tree.heading("provider", text="提供商")
        self.model_tree.heading("model", text="模型标识")
        self.model_tree.heading("status", text="状态")
        
        # 设置列宽
        self.model_tree.column("name", width=200)
        self.model_tree.column("provider", width=100)
        self.model_tree.column("model", width=150)
        self.model_tree.column("status", width=80)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.model_tree.yview)
        self.model_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.model_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.model_tree.bind("<<TreeviewSelect>>", self.on_model_select)
        self.model_tree.bind("<Double-1>", self.on_model_double_click)
        self.model_tree.bind("<Button-3>", self.show_context_menu)
        
        # 创建右键菜单
        self.create_context_menu()
    
    def create_config_area(self, parent):
        """创建配置区域"""
        # 右侧框架
        right_frame = ttk.LabelFrame(parent, text="⚙️ 模型配置", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 配置表单
        self.config_frame = ttk.Frame(right_frame)
        self.config_frame.pack(fill=tk.BOTH, expand=True)
        
        # 显示默认配置
        self.show_default_config()
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # 模型统计信息
        self.stats_var = tk.StringVar()
        self.stats_label = ttk.Label(status_frame, textvariable=self.stats_var)
        self.stats_label.pack(side=tk.RIGHT)
        
        self.update_stats()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="🎯 设为当前模型", command=self.set_as_current_model)
        self.context_menu.add_command(label="✏️ 编辑配置", command=self.edit_selected_model)
        self.context_menu.add_command(label="🔗 测试连接", command=self.test_selected_model)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 复制配置", command=self.copy_model_config)
        self.context_menu.add_command(label="🗑️ 删除模型", command=self.delete_selected_model)
    
    def refresh_model_list(self):
        """刷新模型列表"""
        try:
            # 清空列表
            for item in self.model_tree.get_children():
                self.model_tree.delete(item)
            
            # 获取模型列表
            models = self.model_manager.get_all_models()
            current_model = self.model_manager.get_current_model()
            
            # 添加模型到列表
            for model in models:
                # 状态图标
                status_icon = "✅" if model.is_active else "❌"
                if current_model and model.id == current_model.id:
                    status_icon = "🎯"
                
                # 提供商图标
                provider_icons = {
                    "openai": "🤖",
                    "deepseek": "🧠",
                    "anthropic": "🎭",
                    "google": "🔍",
                    "custom": "⚙️"
                }
                provider_icon = provider_icons.get(model.provider, "❓")
                
                self.model_tree.insert("", tk.END, values=(
                    f"{provider_icon} {model.display_name}",
                    model.provider.title(),
                    model.model_identifier,
                    status_icon
                ), tags=(model.id,))
            
            # 更新当前模型显示
            if current_model:
                self.current_model_var.set(current_model.display_name)
            else:
                self.current_model_var.set("未设置")
            
            # 更新统计信息
            self.update_stats()
            self.status_var.set(f"已加载 {len(models)} 个模型")
            
        except Exception as e:
            logging.error(f"刷新模型列表失败: {e}")
            messagebox.showerror("错误", f"刷新失败: {e}")
    
    def update_stats(self):
        """更新统计信息"""
        try:
            status = self.model_manager.get_status()
            total_models = status["total_models"]
            providers = len(set(model.provider for model in self.model_manager.get_all_models()))
            
            self.stats_var.set(f"模型: {total_models} 个, 提供商: {providers} 个")
            
        except Exception as e:
            logging.error(f"更新统计信息失败: {e}")
    
    def on_model_select(self, event):
        """模型选择事件"""
        try:
            selection = self.model_tree.selection()
            if selection:
                item = selection[0]
                model_id = self.model_tree.item(item)["tags"][0]
                self.show_model_config(model_id)
                
                # 启用按钮
                self.edit_btn.config(state=tk.NORMAL)
                self.delete_btn.config(state=tk.NORMAL)
                self.test_btn.config(state=tk.NORMAL)
            else:
                # 禁用按钮
                self.edit_btn.config(state=tk.DISABLED)
                self.delete_btn.config(state=tk.DISABLED)
                self.test_btn.config(state=tk.DISABLED)
                
        except Exception as e:
            logging.error(f"模型选择事件处理失败: {e}")
    
    def show_model_config(self, model_id):
        """显示模型配置"""
        try:
            model = self.model_manager.get_model(model_id)
            if not model:
                return
            
            # 清空配置区域
            for widget in self.config_frame.winfo_children():
                widget.destroy()
            
            # 创建配置显示
            config_scroll = ttk.Frame(self.config_frame)
            config_scroll.pack(fill=tk.BOTH, expand=True)
            
            # 基本信息
            basic_frame = ttk.LabelFrame(config_scroll, text="基本信息", padding=10)
            basic_frame.pack(fill=tk.X, pady=(0, 10))
            
            info_items = [
                ("显示名称", model.display_name),
                ("提供商", model.provider.title()),
                ("模型标识", model.model_identifier),
                ("API地址", model.api_base_url),
                ("状态", "激活" if model.is_active else "禁用"),
                ("创建时间", model.created_at[:19].replace("T", " ")),
                ("更新时间", model.updated_at[:19].replace("T", " "))
            ]
            
            for i, (label, value) in enumerate(info_items):
                row_frame = ttk.Frame(basic_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(row_frame, text=f"{label}:", width=12, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=value, foreground="blue").pack(side=tk.LEFT, padx=(10, 0))
            
            # 参数配置
            params_frame = ttk.LabelFrame(config_scroll, text="参数配置", padding=10)
            params_frame.pack(fill=tk.X, pady=(0, 10))
            
            param_items = [
                ("最大令牌数", str(model.max_tokens)),
                ("温度参数", str(model.temperature)),
                ("超时时间", f"{model.timeout} 秒")
            ]
            
            for label, value in param_items:
                row_frame = ttk.Frame(params_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(row_frame, text=f"{label}:", width=12, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=value, foreground="green").pack(side=tk.LEFT, padx=(10, 0))
            
            # 描述
            if model.description:
                desc_frame = ttk.LabelFrame(config_scroll, text="描述", padding=10)
                desc_frame.pack(fill=tk.X, pady=(0, 10))
                
                desc_text = tk.Text(desc_frame, height=4, wrap=tk.WORD, state=tk.DISABLED)
                desc_text.pack(fill=tk.X)
                
                desc_text.config(state=tk.NORMAL)
                desc_text.insert(tk.END, model.description)
                desc_text.config(state=tk.DISABLED)
            
            # 操作按钮
            action_frame = ttk.Frame(config_scroll)
            action_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Button(
                action_frame,
                text="🎯 设为当前模型",
                command=lambda: self.set_model_as_current(model_id)
            ).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(
                action_frame,
                text="✏️ 编辑配置",
                command=lambda: self.edit_model_config(model_id)
            ).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(
                action_frame,
                text="🔗 测试连接",
                command=lambda: self.test_model_connection(model_id)
            ).pack(side=tk.LEFT)
            
        except Exception as e:
            logging.error(f"显示模型配置失败: {e}")
            self.show_error_config(f"显示配置失败: {e}")
    
    def show_default_config(self):
        """显示默认配置"""
        ttk.Label(self.config_frame, text="请选择模型查看配置", 
                 foreground="gray", font=('Microsoft YaHei', 12)).pack(expand=True)
    
    def show_error_config(self, error_msg):
        """显示错误配置"""
        for widget in self.config_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.config_frame, text=error_msg,
                 foreground="red", font=('Microsoft YaHei', 10)).pack(expand=True)

    def add_model(self):
        """添加新模型"""
        try:
            dialog = ModelConfigDialog(self.window, "添加模型")
            if dialog.result:
                config = dialog.result
                result = self.model_manager.add_model(**config)

                if result["success"]:
                    self.refresh_model_list()
                    self.status_var.set(result["message"])
                    messagebox.showinfo("成功", result["message"])
                else:
                    messagebox.showerror("错误", result["error"])

        except Exception as e:
            logging.error(f"添加模型失败: {e}")
            messagebox.showerror("错误", f"添加模型失败: {e}")

    def edit_selected_model(self):
        """编辑选中的模型"""
        try:
            selection = self.model_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要编辑的模型")
                return

            item = selection[0]
            model_id = self.model_tree.item(item)["tags"][0]
            model = self.model_manager.get_model(model_id)

            if model:
                dialog = ModelConfigDialog(self.window, "编辑模型", model)
                if dialog.result:
                    config = dialog.result
                    result = self.model_manager.update_model(model_id, **config)

                    if result["success"]:
                        self.refresh_model_list()
                        self.show_model_config(model_id)
                        self.status_var.set(result["message"])
                    else:
                        messagebox.showerror("错误", result["error"])

        except Exception as e:
            logging.error(f"编辑模型失败: {e}")
            messagebox.showerror("错误", f"编辑模型失败: {e}")

    def delete_selected_model(self):
        """删除选中的模型"""
        try:
            selection = self.model_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要删除的模型")
                return

            item = selection[0]
            model_id = self.model_tree.item(item)["tags"][0]
            model = self.model_manager.get_model(model_id)

            if model:
                # 确认删除
                result = messagebox.askyesno(
                    "确认删除",
                    f"确定要删除模型 '{model.display_name}' 吗？\n\n此操作不可撤销。",
                    icon="warning"
                )

                if result:
                    delete_result = self.model_manager.delete_model(model_id)
                    if delete_result["success"]:
                        self.refresh_model_list()
                        self.show_default_config()
                        self.status_var.set(delete_result["message"])
                    else:
                        messagebox.showerror("错误", delete_result["error"])

        except Exception as e:
            logging.error(f"删除模型失败: {e}")
            messagebox.showerror("错误", f"删除模型失败: {e}")

    def test_selected_model(self):
        """测试选中的模型连接"""
        try:
            selection = self.model_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要测试的模型")
                return

            item = selection[0]
            model_id = self.model_tree.item(item)["tags"][0]

            self.test_model_connection(model_id)

        except Exception as e:
            logging.error(f"测试模型连接失败: {e}")
            messagebox.showerror("错误", f"测试连接失败: {e}")

    def test_model_connection(self, model_id):
        """测试模型连接"""
        def test_worker():
            try:
                # 更新状态
                self.window.after(0, lambda: self.status_var.set("正在测试连接..."))

                # 创建事件循环并测试连接
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.model_manager.test_model_connection(model_id))
                loop.close()

                # 更新界面
                if result["success"]:
                    message = f"连接测试成功\n响应时间: {result.get('response_time', 0):.2f} 秒"
                    self.window.after(0, lambda: messagebox.showinfo("测试成功", message))
                    self.window.after(0, lambda: self.status_var.set("连接测试成功"))
                else:
                    error_msg = result["error"]
                    if "details" in result:
                        error_msg += f"\n\n详细信息:\n{result['details']}"
                    self.window.after(0, lambda: messagebox.showerror("测试失败", error_msg))
                    self.window.after(0, lambda: self.status_var.set("连接测试失败"))

            except Exception as e:
                logging.error(f"测试模型连接异常: {e}")
                self.window.after(0, lambda: messagebox.showerror("错误", f"测试异常: {e}"))
                self.window.after(0, lambda: self.status_var.set("测试异常"))

        # 在新线程中执行测试
        threading.Thread(target=test_worker, daemon=True).start()

    def set_model_as_current(self, model_id):
        """设置模型为当前模型"""
        try:
            result = self.model_manager.set_current_model(model_id)
            if result["success"]:
                self.refresh_model_list()
                self.status_var.set(result["message"])
            else:
                messagebox.showerror("错误", result["error"])

        except Exception as e:
            logging.error(f"设置当前模型失败: {e}")
            messagebox.showerror("错误", f"设置失败: {e}")

    def set_as_current_model(self):
        """设为当前模型（右键菜单）"""
        try:
            selection = self.model_tree.selection()
            if selection:
                item = selection[0]
                model_id = self.model_tree.item(item)["tags"][0]
                self.set_model_as_current(model_id)

        except Exception as e:
            logging.error(f"设为当前模型失败: {e}")

    def copy_model_config(self):
        """复制模型配置"""
        try:
            selection = self.model_tree.selection()
            if not selection:
                return

            item = selection[0]
            model_id = self.model_tree.item(item)["tags"][0]
            model = self.model_manager.get_model(model_id)

            if model:
                # 创建配置文本
                config_text = f"""模型配置:
显示名称: {model.display_name}
提供商: {model.provider}
模型标识: {model.model_identifier}
API地址: {model.api_base_url}
最大令牌: {model.max_tokens}
温度参数: {model.temperature}
超时时间: {model.timeout}
描述: {model.description}"""

                # 复制到剪贴板
                from clipboard_manager import get_clipboard_manager
                clipboard_manager = get_clipboard_manager()
                clipboard_manager.set_text_to_clipboard(config_text)

                self.status_var.set("模型配置已复制到剪贴板")

        except Exception as e:
            logging.error(f"复制模型配置失败: {e}")

    def on_model_double_click(self, event):
        """模型双击事件"""
        try:
            selection = self.model_tree.selection()
            if selection:
                item = selection[0]
                model_id = self.model_tree.item(item)["tags"][0]
                self.set_model_as_current(model_id)

        except Exception as e:
            logging.error(f"模型双击事件处理失败: {e}")

    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            # 选择点击的项目
            item = self.model_tree.identify_row(event.y)
            if item:
                self.model_tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)

        except Exception as e:
            logging.error(f"显示右键菜单失败: {e}")

    def edit_model_config(self, model_id):
        """编辑模型配置（内联方法）"""
        model = self.model_manager.get_model(model_id)
        if model:
            dialog = ModelConfigDialog(self.window, "编辑模型", model)
            if dialog.result:
                config = dialog.result
                result = self.model_manager.update_model(model_id, **config)

                if result["success"]:
                    self.refresh_model_list()
                    self.show_model_config(model_id)
                    self.status_var.set(result["message"])
                else:
                    messagebox.showerror("错误", result["error"])

    def close_window(self):
        """关闭窗口"""
        try:
            self.window.destroy()
        except Exception as e:
            logging.error(f"关闭模型管理窗口失败: {e}")

class ModelConfigDialog:
    """模型配置对话框"""

    def __init__(self, parent, title, model=None):
        self.parent = parent
        self.model = model
        self.result = None

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        # 创建界面
        self.create_dialog_widgets()

        # 如果是编辑模式，填充现有数据
        if model:
            self.fill_existing_data()

        # 等待对话框关闭
        self.dialog.wait_window()

    def create_dialog_widgets(self):
        """创建对话框组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 创建滚动区域
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 基本信息
        basic_frame = ttk.LabelFrame(scrollable_frame, text="基本信息", padding=10)
        basic_frame.pack(fill=tk.X, pady=(0, 10))

        # 显示名称
        ttk.Label(basic_frame, text="显示名称 *:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 提供商
        ttk.Label(basic_frame, text="提供商 *:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.provider_var = tk.StringVar()

        # 创建提供商选择框架
        provider_frame = ttk.Frame(basic_frame)
        provider_frame.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # 提供商下拉框（可编辑）
        provider_values = list(get_model_manager().get_providers().keys())
        self.provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.provider_var,
            values=provider_values,
            state="normal",  # 改为可编辑
            width=30
        )
        self.provider_combo.pack(side=tk.LEFT)
        self.provider_combo.bind("<<ComboboxSelected>>", self.on_provider_change)
        self.provider_combo.bind("<KeyRelease>", self.on_provider_change)

        # 添加提示标签
        ttk.Label(provider_frame, text="(可自定义)", foreground="gray", font=('Microsoft YaHei', 8)).pack(side=tk.LEFT, padx=(5, 0))

        # API地址
        ttk.Label(basic_frame, text="API地址 *:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.api_url_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.api_url_var, width=40).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # API密钥
        ttk.Label(basic_frame, text="API密钥 *:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        ttk.Entry(basic_frame, textvariable=self.api_key_var, width=40, show="*").grid(row=3, column=1, sticky=tk.W, padx=(10, 0))

        # 模型标识
        ttk.Label(basic_frame, text="模型标识 *:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.model_id_var = tk.StringVar()
        model_entry = ttk.Entry(basic_frame, textvariable=self.model_id_var, width=40)
        model_entry.grid(row=4, column=1, sticky=tk.W, padx=(10, 0))

        # 参数配置
        params_frame = ttk.LabelFrame(scrollable_frame, text="参数配置", padding=10)
        params_frame.pack(fill=tk.X, pady=(0, 10))

        # 最大令牌数
        ttk.Label(params_frame, text="最大令牌数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.max_tokens_var = tk.IntVar(value=4000)
        ttk.Entry(params_frame, textvariable=self.max_tokens_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # 温度参数
        ttk.Label(params_frame, text="温度参数:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.temperature_var = tk.DoubleVar(value=0.7)
        ttk.Entry(params_frame, textvariable=self.temperature_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # 超时时间
        ttk.Label(params_frame, text="超时时间(秒):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.IntVar(value=30)
        ttk.Entry(params_frame, textvariable=self.timeout_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # 描述
        desc_frame = ttk.LabelFrame(scrollable_frame, text="描述", padding=10)
        desc_frame.pack(fill=tk.X, pady=(0, 10))

        self.description_text = tk.Text(desc_frame, height=4, width=50)
        self.description_text.pack(fill=tk.X)

        # 按钮
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="保存", command=self.save_config).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT)

        # 布局滚动区域
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def on_provider_change(self, event):
        """提供商变化事件"""
        try:
            provider = self.provider_var.get().strip()
            providers = get_model_manager().get_providers()

            if provider in providers:
                provider_info = providers[provider]
                # 自动填充默认API地址
                if provider_info["default_base_url"]:
                    self.api_url_var.set(provider_info["default_base_url"])
            else:
                # 自定义提供商，清空API地址让用户填写
                if provider and provider not in providers:
                    self.api_url_var.set("")

        except Exception as e:
            logging.error(f"处理提供商变化失败: {e}")

    def fill_existing_data(self):
        """填充现有数据"""
        try:
            if self.model:
                self.name_var.set(self.model.display_name)
                self.provider_var.set(self.model.provider)
                self.api_url_var.set(self.model.api_base_url)
                self.api_key_var.set(self.model.api_key)
                self.model_id_var.set(self.model.model_identifier)
                self.max_tokens_var.set(self.model.max_tokens)
                self.temperature_var.set(self.model.temperature)
                self.timeout_var.set(self.model.timeout)
                self.description_text.insert(tk.END, self.model.description)

        except Exception as e:
            logging.error(f"填充现有数据失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            # 验证必填字段
            required_fields = [
                (self.name_var.get().strip(), "显示名称"),
                (self.provider_var.get().strip(), "提供商"),
                (self.api_url_var.get().strip(), "API地址"),
                (self.api_key_var.get().strip(), "API密钥"),
                (self.model_id_var.get().strip(), "模型标识")
            ]

            for value, field_name in required_fields:
                if not value:
                    messagebox.showerror("错误", f"请填写{field_name}")
                    return

            # 构建配置
            self.result = {
                "display_name": self.name_var.get().strip(),
                "provider": self.provider_var.get().strip(),
                "api_base_url": self.api_url_var.get().strip(),
                "api_key": self.api_key_var.get().strip(),
                "model_identifier": self.model_id_var.get().strip(),
                "max_tokens": self.max_tokens_var.get(),
                "temperature": self.temperature_var.get(),
                "timeout": self.timeout_var.get(),
                "description": self.description_text.get(1.0, tk.END).strip()
            }

            self.dialog.destroy()

        except Exception as e:
            logging.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存失败: {e}")

    def cancel(self):
        """取消"""
        self.result = None
        self.dialog.destroy()

def show_model_management_window(parent=None):
    """显示模型管理窗口"""
    try:
        window = ModelManagementWindow(parent)
        return window
    except Exception as e:
        logging.error(f"显示模型管理窗口失败: {e}")
        if parent:
            messagebox.showerror("错误", f"打开模型管理失败: {e}")
        return None
