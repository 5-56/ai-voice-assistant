#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理界面
提供文件上传、预览、管理的图形界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from PIL import Image, ImageTk

from file_manager import get_file_manager
from clipboard_manager import get_clipboard_manager

class FileManagementWindow:
    """文件管理窗口"""
    
    def __init__(self, parent=None, callback=None):
        self.parent = parent
        self.callback = callback  # 回调函数，用于通知主窗口更新
        self.file_manager = get_file_manager()
        self.clipboard_manager = get_clipboard_manager()
        
        # 创建窗口
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("📁 文件管理")
        self.window.geometry("900x700")
        self.window.minsize(800, 600)
        
        # 设置窗口图标和属性
        self.window.transient(parent)
        if parent:
            self.window.grab_set()
        
        # 创建界面
        self.create_widgets()
        self.refresh_file_list()
        
        # 绑定事件
        self.bind_events()
        
        logging.info("文件管理窗口创建成功")
    
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
        
        # 左侧文件列表
        self.create_file_list(content_frame)
        
        # 右侧预览区域
        self.create_preview_area(content_frame)
        
        # 底部状态栏
        self.create_status_bar(main_frame)
    
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X)
        
        # 左侧按钮
        left_buttons = ttk.Frame(toolbar_frame)
        left_buttons.pack(side=tk.LEFT)
        
        # 上传文件按钮
        self.upload_btn = ttk.Button(
            left_buttons,
            text="📁 上传文件",
            command=self.upload_files
        )
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 粘贴按钮
        self.paste_btn = ttk.Button(
            left_buttons,
            text="📋 粘贴",
            command=self.paste_from_clipboard
        )
        self.paste_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(
            left_buttons,
            text="🔄 刷新",
            command=self.refresh_file_list
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 右侧按钮
        right_buttons = ttk.Frame(toolbar_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        # 清理按钮
        self.cleanup_btn = ttk.Button(
            right_buttons,
            text="🧹 清理",
            command=self.cleanup_files
        )
        self.cleanup_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 文件类型筛选
        ttk.Label(right_buttons, text="类型:").pack(side=tk.LEFT, padx=(10, 5))
        
        self.filter_var = tk.StringVar(value="all")
        self.filter_combo = ttk.Combobox(
            right_buttons,
            textvariable=self.filter_var,
            values=["all", "document", "image"],
            state="readonly",
            width=10
        )
        self.filter_combo.pack(side=tk.LEFT)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_file_list())
    
    def create_file_list(self, parent):
        """创建文件列表"""
        # 左侧框架
        left_frame = ttk.LabelFrame(parent, text="📚 文件列表", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 创建Treeview
        columns = ("name", "type", "size", "date")
        self.file_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("type", text="类型")
        self.file_tree.heading("size", text="大小")
        self.file_tree.heading("date", text="上传时间")
        
        # 设置列宽
        self.file_tree.column("name", width=200)
        self.file_tree.column("type", width=80)
        self.file_tree.column("size", width=80)
        self.file_tree.column("date", width=120)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        self.file_tree.bind("<Double-1>", self.on_file_double_click)
        self.file_tree.bind("<Button-3>", self.show_context_menu)
        
        # 创建右键菜单
        self.create_context_menu()
    
    def create_preview_area(self, parent):
        """创建预览区域"""
        # 右侧框架
        right_frame = ttk.LabelFrame(parent, text="👁️ 文件预览", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 预览内容框架
        self.preview_frame = ttk.Frame(right_frame)
        self.preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # 默认显示
        self.show_default_preview()
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # 存储信息
        self.storage_var = tk.StringVar()
        self.storage_label = ttk.Label(status_frame, textvariable=self.storage_var)
        self.storage_label.pack(side=tk.RIGHT)
        
        self.update_storage_info()
    
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="📖 预览", command=self.preview_selected_file)
        self.context_menu.add_command(label="✏️ 重命名", command=self.rename_selected_file)
        self.context_menu.add_command(label="📝 编辑描述", command=self.edit_file_description)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 复制路径", command=self.copy_file_path)
        self.context_menu.add_command(label="📂 打开位置", command=self.open_file_location)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ 删除", command=self.delete_selected_file)
    
    def bind_events(self):
        """绑定事件"""
        # 拖拽支持（使用tkinterdnd2库，如果可用）
        try:
            import tkinterdnd2
            # 如果有tkinterdnd2库，启用拖拽功能
            self.window.drop_target_register(tkinterdnd2.DND_FILES)
            self.window.dnd_bind('<<Drop>>', self.on_file_drop)
            logging.info("拖拽功能已启用")
        except ImportError:
            # 如果没有tkinterdnd2库，跳过拖拽功能
            logging.info("tkinterdnd2库不可用，跳过拖拽功能")
        except Exception as e:
            logging.warning(f"拖拽功能初始化失败: {e}")

        # 键盘快捷键
        self.window.bind("<Control-o>", lambda e: self.upload_files())
        self.window.bind("<Control-v>", lambda e: self.paste_from_clipboard())
        self.window.bind("<F5>", lambda e: self.refresh_file_list())
        self.window.bind("<Delete>", lambda e: self.delete_selected_file())
    
    def upload_files(self):
        """上传文件"""
        try:
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
            logging.error(f"选择上传文件失败: {e}")
            messagebox.showerror("错误", f"选择文件失败: {e}")
    
    def upload_files_async(self, file_paths):
        """异步上传文件"""
        def upload_worker():
            try:
                success_count = 0
                total_count = len(file_paths)
                
                for i, file_path in enumerate(file_paths):
                    # 更新状态
                    self.window.after(0, lambda: self.status_var.set(f"上传中... ({i+1}/{total_count})"))
                    
                    # 上传文件
                    result = self.file_manager.upload_file(file_path)
                    
                    if result["success"]:
                        success_count += 1
                    else:
                        logging.error(f"上传文件失败: {result['error']}")
                
                # 更新界面
                self.window.after(0, self.refresh_file_list)
                self.window.after(0, lambda: self.status_var.set(f"上传完成: {success_count}/{total_count} 个文件"))

                # 通知主窗口更新知识库状态
                if self.callback and success_count > 0:
                    self.window.after(0, self.callback)
                
                if success_count < total_count:
                    self.window.after(0, lambda: messagebox.showwarning(
                        "上传完成", f"成功上传 {success_count}/{total_count} 个文件"
                    ))
                
            except Exception as e:
                logging.error(f"异步上传文件失败: {e}")
                self.window.after(0, lambda: messagebox.showerror("错误", f"上传失败: {e}"))
        
        # 在新线程中执行上传
        threading.Thread(target=upload_worker, daemon=True).start()
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴"""
        try:
            content_type = self.clipboard_manager.get_clipboard_content_type()
            
            if content_type == "text":
                text = self.clipboard_manager.get_text_from_clipboard()
                if text:
                    # 创建临时文本文件
                    self.create_text_file_from_clipboard(text)
                else:
                    messagebox.showinfo("提示", "剪贴板中没有文本内容")
            
            elif content_type == "image":
                image_info = self.clipboard_manager.get_image_from_clipboard()
                if image_info:
                    # 上传剪贴板图片
                    result = self.file_manager.upload_file(image_info["path"], "剪贴板图片")
                    if result["success"]:
                        self.refresh_file_list()
                        self.status_var.set("剪贴板图片上传成功")
                    else:
                        messagebox.showerror("错误", f"上传剪贴板图片失败: {result['error']}")
                else:
                    messagebox.showinfo("提示", "剪贴板中没有图片内容")
            
            else:
                messagebox.showinfo("提示", "剪贴板中没有支持的内容")
                
        except Exception as e:
            logging.error(f"粘贴剪贴板内容失败: {e}")
            messagebox.showerror("错误", f"粘贴失败: {e}")
    
    def create_text_file_from_clipboard(self, text):
        """从剪贴板文本创建文件"""
        try:
            # 询问文件名
            filename = simpledialog.askstring(
                "保存文本",
                "请输入文件名:",
                initialvalue="剪贴板文本"
            )
            
            if filename:
                # 创建临时文件
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
                temp_file.write(text)
                temp_file.close()
                
                # 上传文件
                result = self.file_manager.upload_file(temp_file.name, filename)
                
                # 删除临时文件
                Path(temp_file.name).unlink()
                
                if result["success"]:
                    self.refresh_file_list()
                    self.status_var.set("文本文件创建成功")
                else:
                    messagebox.showerror("错误", f"创建文本文件失败: {result['error']}")
                    
        except Exception as e:
            logging.error(f"创建文本文件失败: {e}")
            messagebox.showerror("错误", f"创建文件失败: {e}")
    
    def refresh_file_list(self):
        """刷新文件列表"""
        try:
            # 清空列表
            for item in self.file_tree.get_children():
                self.file_tree.delete(item)
            
            # 获取文件列表
            filter_type = self.filter_var.get()
            if filter_type == "all":
                files = self.file_manager.get_file_list()
            else:
                files = self.file_manager.get_file_list(filter_type)
            
            # 添加文件到列表
            for file_info in files:
                # 格式化文件大小
                size = self.format_file_size(file_info["file_size"])
                
                # 格式化日期
                date = file_info["upload_time"][:19].replace("T", " ")
                
                # 显示名称
                display_name = file_info.get("custom_name") or file_info["original_name"]
                
                # 文件类型图标
                type_icon = "📄" if file_info["file_type"] == "document" else "🖼️"
                
                self.file_tree.insert("", tk.END, values=(
                    f"{type_icon} {display_name}",
                    file_info["file_type"],
                    size,
                    date
                ), tags=(file_info["id"],))
            
            # 更新存储信息
            self.update_storage_info()
            self.status_var.set(f"已加载 {len(files)} 个文件")
            
        except Exception as e:
            logging.error(f"刷新文件列表失败: {e}")
            messagebox.showerror("错误", f"刷新失败: {e}")
    
    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def update_storage_info(self):
        """更新存储信息"""
        try:
            storage_info = self.file_manager.get_storage_info()
            total_size = self.format_file_size(storage_info.get("total_size", 0))
            total_files = storage_info.get("total_files", 0)
            
            self.storage_var.set(f"文件: {total_files} 个, 大小: {total_size}")
            
        except Exception as e:
            logging.error(f"更新存储信息失败: {e}")
    
    def on_file_select(self, event):
        """文件选择事件"""
        try:
            selection = self.file_tree.selection()
            if selection:
                item = selection[0]
                file_id = self.file_tree.item(item)["tags"][0]
                self.preview_file(file_id)
                
        except Exception as e:
            logging.error(f"文件选择事件处理失败: {e}")
    
    def preview_file(self, file_id):
        """预览文件"""
        try:
            file_info = self.file_manager.get_file_info(file_id)
            if not file_info:
                return
            
            # 清空预览区域
            for widget in self.preview_frame.winfo_children():
                widget.destroy()
            
            # 创建预览内容
            if file_info["file_type"] == "image":
                self.show_image_preview(file_info)
            else:
                self.show_document_preview(file_info)
                
        except Exception as e:
            logging.error(f"预览文件失败: {e}")
            self.show_error_preview(f"预览失败: {e}")
    
    def show_image_preview(self, file_info):
        """显示图片预览"""
        try:
            # 文件信息
            info_frame = ttk.Frame(self.preview_frame)
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(info_frame, text=f"📷 {file_info['filename']}", 
                     font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"大小: {self.format_file_size(file_info['file_size'])}").pack(anchor=tk.W)
            
            # 图片预览
            image_frame = ttk.Frame(self.preview_frame)
            image_frame.pack(fill=tk.BOTH, expand=True)
            
            # 加载图片
            image = Image.open(file_info["file_path"])
            
            # 计算缩放比例
            max_size = (400, 400)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换为Tkinter格式
            photo = ImageTk.PhotoImage(image)
            
            # 显示图片
            image_label = ttk.Label(image_frame, image=photo)
            image_label.image = photo  # 保持引用
            image_label.pack(pady=10)
            
            # 图片信息
            ttk.Label(image_frame, text=f"尺寸: {image.size[0]} x {image.size[1]}").pack()
            
        except Exception as e:
            logging.error(f"显示图片预览失败: {e}")
            self.show_error_preview(f"图片预览失败: {e}")
    
    def show_document_preview(self, file_info):
        """显示文档预览"""
        try:
            # 文件信息
            info_frame = ttk.Frame(self.preview_frame)
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(info_frame, text=f"📄 {file_info['filename']}", 
                     font=('Microsoft YaHei', 12, 'bold')).pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"类型: {file_info['file_extension']}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"大小: {self.format_file_size(file_info['file_size'])}").pack(anchor=tk.W)
            
            # 文档内容预览（仅支持文本文件）
            if file_info["file_extension"].lower() in ['.txt', '.md']:
                self.show_text_content(file_info)
            else:
                ttk.Label(self.preview_frame, text="此文件类型不支持预览", 
                         foreground="gray").pack(pady=20)
                
        except Exception as e:
            logging.error(f"显示文档预览失败: {e}")
            self.show_error_preview(f"文档预览失败: {e}")
    
    def show_text_content(self, file_info):
        """显示文本内容"""
        try:
            content_frame = ttk.LabelFrame(self.preview_frame, text="文件内容", padding=5)
            content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            
            # 创建文本框
            text_widget = tk.Text(content_frame, wrap=tk.WORD, height=15, 
                                 font=('Consolas', 10))
            scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            # 读取文件内容
            with open(file_info["file_path"], 'r', encoding='utf-8') as f:
                content = f.read()
                text_widget.insert(tk.END, content)
            
            text_widget.config(state=tk.DISABLED)
            
            # 布局
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
        except Exception as e:
            logging.error(f"显示文本内容失败: {e}")
            ttk.Label(self.preview_frame, text=f"读取文件失败: {e}", 
                     foreground="red").pack(pady=20)
    
    def show_default_preview(self):
        """显示默认预览"""
        ttk.Label(self.preview_frame, text="请选择文件进行预览", 
                 foreground="gray", font=('Microsoft YaHei', 12)).pack(expand=True)
    
    def show_error_preview(self, error_msg):
        """显示错误预览"""
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.preview_frame, text=error_msg, 
                 foreground="red", font=('Microsoft YaHei', 10)).pack(expand=True)
    
    def on_file_double_click(self, event):
        """文件双击事件"""
        try:
            selection = self.file_tree.selection()
            if selection:
                item = selection[0]
                file_id = self.file_tree.item(item)["tags"][0]
                file_info = self.file_manager.get_file_info(file_id)

                if file_info:
                    # 打开文件
                    import os
                    os.startfile(file_info["file_path"])

        except Exception as e:
            logging.error(f"打开文件失败: {e}")
            messagebox.showerror("错误", f"打开文件失败: {e}")

    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            # 选择点击的项目
            item = self.file_tree.identify_row(event.y)
            if item:
                self.file_tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)

        except Exception as e:
            logging.error(f"显示右键菜单失败: {e}")

    def preview_selected_file(self):
        """预览选中的文件"""
        try:
            selection = self.file_tree.selection()
            if selection:
                item = selection[0]
                file_id = self.file_tree.item(item)["tags"][0]
                self.preview_file(file_id)

        except Exception as e:
            logging.error(f"预览选中文件失败: {e}")

    def rename_selected_file(self):
        """重命名选中的文件"""
        try:
            selection = self.file_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要重命名的文件")
                return

            item = selection[0]
            file_id = self.file_tree.item(item)["tags"][0]
            file_info = self.file_manager.get_file_info(file_id)

            if file_info:
                current_name = file_info.get("custom_name") or file_info["original_name"]
                new_name = simpledialog.askstring(
                    "重命名文件",
                    "请输入新的文件名:",
                    initialvalue=current_name
                )

                if new_name and new_name != current_name:
                    result = self.file_manager.rename_file(file_id, new_name)
                    if result["success"]:
                        self.refresh_file_list()
                        self.status_var.set(result["message"])
                    else:
                        messagebox.showerror("错误", result["error"])

        except Exception as e:
            logging.error(f"重命名文件失败: {e}")
            messagebox.showerror("错误", f"重命名失败: {e}")

    def edit_file_description(self):
        """编辑文件描述"""
        try:
            selection = self.file_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要编辑的文件")
                return

            item = selection[0]
            file_id = self.file_tree.item(item)["tags"][0]
            file_info = self.file_manager.get_file_info(file_id)

            if file_info:
                current_desc = file_info.get("description", "")

                # 创建描述编辑对话框
                desc_window = tk.Toplevel(self.window)
                desc_window.title("编辑文件描述")
                desc_window.geometry("400x300")
                desc_window.transient(self.window)
                desc_window.grab_set()

                ttk.Label(desc_window, text=f"文件: {file_info['filename']}").pack(pady=10)

                text_frame = ttk.Frame(desc_window)
                text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

                desc_text = tk.Text(text_frame, wrap=tk.WORD, height=10)
                desc_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=desc_text.yview)
                desc_text.configure(yscrollcommand=desc_scrollbar.set)

                desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                desc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                desc_text.insert(tk.END, current_desc)

                # 按钮
                button_frame = ttk.Frame(desc_window)
                button_frame.pack(fill=tk.X, padx=10, pady=10)

                def save_description():
                    new_desc = desc_text.get(1.0, tk.END).strip()
                    result = self.file_manager.update_file_description(file_id, new_desc)
                    if result["success"]:
                        desc_window.destroy()
                        self.status_var.set("文件描述已更新")
                    else:
                        messagebox.showerror("错误", result["error"])

                ttk.Button(button_frame, text="保存", command=save_description).pack(side=tk.RIGHT, padx=(5, 0))
                ttk.Button(button_frame, text="取消", command=desc_window.destroy).pack(side=tk.RIGHT)

        except Exception as e:
            logging.error(f"编辑文件描述失败: {e}")
            messagebox.showerror("错误", f"编辑描述失败: {e}")

    def copy_file_path(self):
        """复制文件路径"""
        try:
            selection = self.file_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择文件")
                return

            item = selection[0]
            file_id = self.file_tree.item(item)["tags"][0]
            file_info = self.file_manager.get_file_info(file_id)

            if file_info:
                self.clipboard_manager.set_text_to_clipboard(file_info["file_path"])
                self.status_var.set("文件路径已复制到剪贴板")

        except Exception as e:
            logging.error(f"复制文件路径失败: {e}")
            messagebox.showerror("错误", f"复制路径失败: {e}")

    def open_file_location(self):
        """打开文件位置"""
        try:
            selection = self.file_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择文件")
                return

            item = selection[0]
            file_id = self.file_tree.item(item)["tags"][0]
            file_info = self.file_manager.get_file_info(file_id)

            if file_info:
                import os
                import subprocess
                file_path = Path(file_info["file_path"])

                # 在文件管理器中选中文件
                if os.name == 'nt':  # Windows
                    subprocess.run(['explorer', '/select,', str(file_path)])
                else:  # Linux/Mac
                    subprocess.run(['xdg-open', str(file_path.parent)])

        except Exception as e:
            logging.error(f"打开文件位置失败: {e}")
            messagebox.showerror("错误", f"打开位置失败: {e}")

    def delete_selected_file(self):
        """删除选中的文件"""
        try:
            selection = self.file_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择要删除的文件")
                return

            item = selection[0]
            file_id = self.file_tree.item(item)["tags"][0]
            file_info = self.file_manager.get_file_info(file_id)

            if file_info:
                # 确认删除
                result = messagebox.askyesno(
                    "确认删除",
                    f"确定要删除文件 '{file_info['filename']}' 吗？\n\n此操作不可撤销。",
                    icon="warning"
                )

                if result:
                    delete_result = self.file_manager.delete_file(file_id)
                    if delete_result["success"]:
                        self.refresh_file_list()
                        self.show_default_preview()
                        self.status_var.set(delete_result["message"])

                        # 通知主窗口更新知识库状态
                        if self.callback:
                            self.callback()
                    else:
                        messagebox.showerror("错误", delete_result["error"])

        except Exception as e:
            logging.error(f"删除文件失败: {e}")
            messagebox.showerror("错误", f"删除失败: {e}")

    def cleanup_files(self):
        """清理文件"""
        try:
            result = messagebox.askyesno(
                "清理文件",
                "确定要清理孤立文件吗？\n\n这将删除数据库中不存在的文件和目录中的孤立文件。",
                icon="question"
            )

            if result:
                cleanup_result = self.file_manager.cleanup_orphaned_files()
                if cleanup_result["success"]:
                    self.refresh_file_list()
                    messagebox.showinfo("清理完成", cleanup_result["message"])
                else:
                    messagebox.showerror("错误", cleanup_result["error"])

        except Exception as e:
            logging.error(f"清理文件失败: {e}")
            messagebox.showerror("错误", f"清理失败: {e}")

    def on_file_drop(self, event):
        """文件拖拽事件"""
        try:
            files = self.window.tk.splitlist(event.data)
            if files:
                self.upload_files_async(files)

        except Exception as e:
            logging.error(f"处理拖拽文件失败: {e}")

    def close_window(self):
        """关闭窗口"""
        try:
            self.window.destroy()
        except Exception as e:
            logging.error(f"关闭文件管理窗口失败: {e}")

def show_file_management_window(parent=None, callback=None):
    """显示文件管理窗口"""
    try:
        window = FileManagementWindow(parent, callback)
        return window
    except Exception as e:
        logging.error(f"显示文件管理窗口失败: {e}")
        if parent:
            messagebox.showerror("错误", f"打开文件管理失败: {e}")
        return None
