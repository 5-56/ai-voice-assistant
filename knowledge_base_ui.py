#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库管理UI界面
提供知识库搜索、文档管理、标签分类等功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# 知识库相关导入
try:
    from knowledge_base import get_knowledge_base
    from rag_system import get_rag_system
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    logging.warning("知识库模块不可用")

class KnowledgeBaseWindow:
    """知识库管理窗口"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.knowledge_base = None
        self.rag_system = None
        
        if KNOWLEDGE_BASE_AVAILABLE:
            self.knowledge_base = get_knowledge_base()
            self.rag_system = get_rag_system()
        
        # 创建窗口
        self.create_window()
        self.create_widgets()
        self.bind_events()
        
        # 初始化数据
        self.refresh_document_list()
        self.update_statistics()
    
    def create_window(self):
        """创建窗口"""
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("📚 知识库管理")
        self.window.geometry("1000x700")
        self.window.minsize(800, 600)
        
        # 设置图标
        try:
            self.window.iconbitmap("icon.ico")
        except:
            pass
        
        # 居中显示
        self.center_window()
    
    def center_window(self):
        """窗口居中"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部工具栏
        self.create_toolbar(main_frame)
        
        # 主要内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 左侧：文档列表和搜索
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.create_search_section(left_frame)
        self.create_document_list(left_frame)
        
        # 右侧：文档详情和统计
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        self.create_document_details(right_frame)
        self.create_statistics_section(right_frame)
        
        # 底部状态栏
        self.create_status_bar(main_frame)
    
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # 刷新按钮
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_all).pack(side=tk.LEFT, padx=(0, 5))
        
        # 搜索知识库按钮
        ttk.Button(toolbar, text="🔍 搜索知识库", command=self.open_search_dialog).pack(side=tk.LEFT, padx=(0, 5))
        
        # 分隔符
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 重建索引按钮
        ttk.Button(toolbar, text="🔧 重建索引", command=self.rebuild_index).pack(side=tk.LEFT, padx=(0, 5))
        
        # 清理数据库按钮
        ttk.Button(toolbar, text="🧹 清理数据库", command=self.cleanup_database).pack(side=tk.LEFT, padx=(0, 5))
        
        # 右侧状态指示器
        status_frame = ttk.Frame(toolbar)
        status_frame.pack(side=tk.RIGHT)
        
        self.kb_status_label = ttk.Label(status_frame, text="📚 知识库状态: 检查中...", 
                                        font=('Microsoft YaHei', 9))
        self.kb_status_label.pack(side=tk.RIGHT)
    
    def create_search_section(self, parent):
        """创建搜索区域"""
        search_frame = ttk.LabelFrame(parent, text="🔍 搜索文档", padding=10)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 搜索输入框
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_input_frame, textvariable=self.search_var, 
                                     font=('Microsoft YaHei', 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(search_input_frame, text="搜索", command=self.search_documents).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 搜索选项
        options_frame = ttk.Frame(search_frame)
        options_frame.pack(fill=tk.X)
        
        # 搜索类型
        ttk.Label(options_frame, text="类型:").pack(side=tk.LEFT)
        self.search_type_var = tk.StringVar(value="all")
        search_type_combo = ttk.Combobox(options_frame, textvariable=self.search_type_var,
                                        values=["all", "keyword", "vector"], state="readonly", width=10)
        search_type_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        # 分类筛选
        ttk.Label(options_frame, text="分类:").pack(side=tk.LEFT)
        self.category_filter_var = tk.StringVar(value="全部")
        self.category_combo = ttk.Combobox(options_frame, textvariable=self.category_filter_var,
                                          state="readonly", width=12)
        self.category_combo.pack(side=tk.LEFT, padx=(5, 0))
    
    def create_document_list(self, parent):
        """创建文档列表"""
        list_frame = ttk.LabelFrame(parent, text="📄 文档列表", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ("name", "category", "tags", "words", "updated")
        self.doc_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        self.doc_tree.heading("name", text="文档名称")
        self.doc_tree.heading("category", text="分类")
        self.doc_tree.heading("tags", text="标签")
        self.doc_tree.heading("words", text="字数")
        self.doc_tree.heading("updated", text="更新时间")
        
        # 设置列宽
        self.doc_tree.column("name", width=200)
        self.doc_tree.column("category", width=100)
        self.doc_tree.column("tags", width=150)
        self.doc_tree.column("words", width=80)
        self.doc_tree.column("updated", width=120)
        
        # 滚动条
        doc_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.doc_tree.yview)
        self.doc_tree.configure(yscrollcommand=doc_scrollbar.set)
        
        # 布局
        self.doc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        doc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_document_details(self, parent):
        """创建文档详情区域"""
        details_frame = ttk.LabelFrame(parent, text="📋 文档详情", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 文档信息
        info_frame = ttk.Frame(details_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文档名称
        ttk.Label(info_frame, text="名称:", font=('Microsoft YaHei', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.doc_name_label = ttk.Label(info_frame, text="未选择文档", font=('Microsoft YaHei', 9))
        self.doc_name_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 分类
        ttk.Label(info_frame, text="分类:", font=('Microsoft YaHei', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.doc_category_var = tk.StringVar()
        self.doc_category_entry = ttk.Entry(info_frame, textvariable=self.doc_category_var, width=20)
        self.doc_category_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 标签
        ttk.Label(info_frame, text="标签:", font=('Microsoft YaHei', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.doc_tags_var = tk.StringVar()
        self.doc_tags_entry = ttk.Entry(info_frame, textvariable=self.doc_tags_var, width=20)
        self.doc_tags_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # 更新按钮
        ttk.Button(info_frame, text="💾 更新", command=self.update_document_metadata).grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # 文档内容预览
        preview_frame = ttk.Frame(details_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(preview_frame, text="内容预览:", font=('Microsoft YaHei', 9, 'bold')).pack(anchor=tk.W)
        
        # 文本框和滚动条
        text_frame = ttk.Frame(preview_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.content_text = tk.Text(text_frame, wrap=tk.WORD, font=('Microsoft YaHei', 9), 
                                   state=tk.DISABLED, height=10)
        content_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.content_text.yview)
        self.content_text.configure(yscrollcommand=content_scrollbar.set)
        
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_statistics_section(self, parent):
        """创建统计信息区域"""
        stats_frame = ttk.LabelFrame(parent, text="📊 统计信息", padding=10)
        stats_frame.pack(fill=tk.X)
        
        self.stats_text = tk.Text(stats_frame, height=8, font=('Microsoft YaHei', 9), 
                                 state=tk.DISABLED, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.X)
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     font=('Microsoft YaHei', 8))
        self.status_label.pack(side=tk.LEFT)
    
    def bind_events(self):
        """绑定事件"""
        # 文档选择事件
        self.doc_tree.bind("<<TreeviewSelect>>", self.on_document_select)
        
        # 搜索框回车事件
        self.search_entry.bind("<Return>", lambda e: self.search_documents())
        
        # 分类筛选变化事件
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_documents())
        
        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    def refresh_all(self):
        """刷新所有数据"""
        self.refresh_document_list()
        self.update_statistics()
        self.update_category_filter()
        self.status_var.set("数据已刷新")

    def refresh_document_list(self):
        """刷新文档列表"""
        if not KNOWLEDGE_BASE_AVAILABLE or not self.knowledge_base:
            return

        try:
            # 清空现有项目
            for item in self.doc_tree.get_children():
                self.doc_tree.delete(item)

            # 获取所有文档
            documents = self.knowledge_base.documents

            for doc in documents:
                # 格式化数据
                name = doc["file_name"]
                category = doc["category"] or "未分类"
                tags = ", ".join(doc["tags"]) if doc["tags"] else "无标签"
                words = doc["metadata"].get("word_count", 0)
                updated = doc["updated_time"][:19] if doc["updated_time"] else "未知"

                # 插入到树形视图
                self.doc_tree.insert("", tk.END, values=(name, category, tags, words, updated))

            self.status_var.set(f"已加载 {len(documents)} 个文档")

        except Exception as e:
            logging.error(f"刷新文档列表失败: {e}")
            messagebox.showerror("错误", f"刷新文档列表失败: {e}")

    def update_statistics(self):
        """更新统计信息"""
        if not KNOWLEDGE_BASE_AVAILABLE or not self.knowledge_base:
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(tk.END, "知识库不可用")
            self.stats_text.config(state=tk.DISABLED)

            self.kb_status_label.config(text="📚 知识库状态: 不可用", foreground="red")
            return

        try:
            stats = self.knowledge_base.get_statistics()

            # 更新统计文本
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)

            stats_info = f"""📊 知识库统计信息

📄 文档总数: {stats['total_documents']}
📝 总字数: {stats['total_words']:,}
🔤 总字符数: {stats['total_characters']:,}

📂 分类统计:
"""

            for category, count in stats['categories'].items():
                stats_info += f"  • {category}: {count} 个文档\n"

            stats_info += f"\n📋 格式统计:\n"
            for format_type, count in stats['formats'].items():
                stats_info += f"  • {format_type}: {count} 个文档\n"

            stats_info += f"\n🔍 向量索引: {'✅ 可用' if stats['vector_index_available'] else '❌ 不可用'}"

            self.stats_text.insert(tk.END, stats_info)
            self.stats_text.config(state=tk.DISABLED)

            # 更新状态标签
            if stats['total_documents'] > 0:
                self.kb_status_label.config(
                    text=f"📚 知识库状态: {stats['total_documents']}个文档",
                    foreground="green"
                )
            else:
                self.kb_status_label.config(
                    text="📚 知识库状态: 空",
                    foreground="orange"
                )

        except Exception as e:
            logging.error(f"更新统计信息失败: {e}")
            self.kb_status_label.config(text="📚 知识库状态: 错误", foreground="red")

    def update_category_filter(self):
        """更新分类筛选器"""
        if not KNOWLEDGE_BASE_AVAILABLE or not self.knowledge_base:
            return

        try:
            stats = self.knowledge_base.get_statistics()
            categories = ["全部"] + list(stats['categories'].keys())

            self.category_combo['values'] = categories
            if self.category_filter_var.get() not in categories:
                self.category_filter_var.set("全部")

        except Exception as e:
            logging.error(f"更新分类筛选器失败: {e}")

    def search_documents(self):
        """搜索文档"""
        if not KNOWLEDGE_BASE_AVAILABLE or not self.knowledge_base:
            messagebox.showwarning("警告", "知识库不可用")
            return

        query = self.search_var.get().strip()
        if not query:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return

        try:
            self.status_var.set("搜索中...")

            # 执行搜索
            results = self.knowledge_base.search_documents(query, limit=10)

            # 清空现有项目
            for item in self.doc_tree.get_children():
                self.doc_tree.delete(item)

            # 显示搜索结果
            for result in results:
                name = result["file_name"]
                category = result.get("category", "未分类") or "未分类"
                tags = ", ".join(result.get("tags", [])) if result.get("tags") else "无标签"
                words = result["metadata"].get("word_count", 0)
                score = result.get("relevance_score", 0)

                # 添加相关性分数到名称
                display_name = f"{name} (相关性: {score:.2f})"

                self.doc_tree.insert("", tk.END, values=(display_name, category, tags, words, "搜索结果"))

            self.status_var.set(f"找到 {len(results)} 个相关文档")

        except Exception as e:
            logging.error(f"搜索文档失败: {e}")
            messagebox.showerror("错误", f"搜索失败: {e}")
            self.status_var.set("搜索失败")

    def filter_documents(self):
        """按分类筛选文档"""
        category = self.category_filter_var.get()

        if category == "全部":
            self.refresh_document_list()
        else:
            # 实现分类筛选逻辑
            if not KNOWLEDGE_BASE_AVAILABLE or not self.knowledge_base:
                return

            try:
                # 清空现有项目
                for item in self.doc_tree.get_children():
                    self.doc_tree.delete(item)

                # 获取指定分类的文档
                documents = [doc for doc in self.knowledge_base.documents
                           if doc["category"] == category]

                for doc in documents:
                    name = doc["file_name"]
                    category_name = doc["category"] or "未分类"
                    tags = ", ".join(doc["tags"]) if doc["tags"] else "无标签"
                    words = doc["metadata"].get("word_count", 0)
                    updated = doc["updated_time"][:19] if doc["updated_time"] else "未知"

                    self.doc_tree.insert("", tk.END, values=(name, category_name, tags, words, updated))

                self.status_var.set(f"分类 '{category}' 包含 {len(documents)} 个文档")

            except Exception as e:
                logging.error(f"筛选文档失败: {e}")
                messagebox.showerror("错误", f"筛选失败: {e}")

    def on_document_select(self, event):
        """文档选择事件"""
        selection = self.doc_tree.selection()
        if not selection:
            return

        try:
            # 获取选中的文档信息
            item = self.doc_tree.item(selection[0])
            doc_name = item['values'][0]

            # 移除相关性分数（如果有）
            if " (相关性:" in doc_name:
                doc_name = doc_name.split(" (相关性:")[0]

            # 查找对应的文档
            doc = None
            for d in self.knowledge_base.documents:
                if d["file_name"] == doc_name:
                    doc = d
                    break

            if doc:
                # 更新文档详情
                self.doc_name_label.config(text=doc["file_name"])
                self.doc_category_var.set(doc["category"] or "")
                self.doc_tags_var.set(", ".join(doc["tags"]) if doc["tags"] else "")

                # 更新内容预览
                self.content_text.config(state=tk.NORMAL)
                self.content_text.delete(1.0, tk.END)

                content = doc["content"]
                if len(content) > 1000:
                    content = content[:1000] + "\n\n... (内容已截断，显示前1000字符)"

                self.content_text.insert(tk.END, content)
                self.content_text.config(state=tk.DISABLED)

                # 保存当前选中的文档ID
                self.selected_doc_id = doc["file_id"]

        except Exception as e:
            logging.error(f"选择文档失败: {e}")

    def update_document_metadata(self):
        """更新文档元数据"""
        if not hasattr(self, 'selected_doc_id'):
            messagebox.showwarning("警告", "请先选择一个文档")
            return

        try:
            # 获取新的元数据
            new_category = self.doc_category_var.get().strip()
            new_tags_str = self.doc_tags_var.get().strip()
            new_tags = [tag.strip() for tag in new_tags_str.split(",") if tag.strip()]

            # 更新元数据
            if self.rag_system:
                result = self.rag_system.update_document_metadata(
                    self.selected_doc_id,
                    tags=new_tags,
                    category=new_category
                )

                if result["success"]:
                    messagebox.showinfo("成功", "文档元数据已更新")
                    self.refresh_document_list()
                    self.update_statistics()
                    self.update_category_filter()
                else:
                    messagebox.showerror("错误", f"更新失败: {result['error']}")
            else:
                messagebox.showerror("错误", "RAG系统不可用")

        except Exception as e:
            logging.error(f"更新文档元数据失败: {e}")
            messagebox.showerror("错误", f"更新失败: {e}")

    def open_search_dialog(self):
        """打开搜索对话框"""
        dialog = SearchDialog(self.window, self.knowledge_base)
        self.window.wait_window(dialog.dialog)

    def rebuild_index(self):
        """重建向量索引"""
        if not KNOWLEDGE_BASE_AVAILABLE or not self.knowledge_base:
            messagebox.showwarning("警告", "知识库不可用")
            return

        result = messagebox.askyesno("确认", "重建索引可能需要一些时间，确定要继续吗？")
        if not result:
            return

        def rebuild_worker():
            try:
                self.window.after(0, lambda: self.status_var.set("正在重建索引..."))
                self.knowledge_base.rebuild_vector_index()
                self.window.after(0, lambda: self.status_var.set("索引重建完成"))
                self.window.after(0, lambda: messagebox.showinfo("成功", "向量索引重建完成"))
                self.window.after(0, self.update_statistics)
            except Exception as e:
                logging.error(f"重建索引失败: {e}")
                self.window.after(0, lambda: messagebox.showerror("错误", f"重建索引失败: {e}"))
                self.window.after(0, lambda: self.status_var.set("重建索引失败"))

        threading.Thread(target=rebuild_worker, daemon=True).start()

    def cleanup_database(self):
        """清理数据库"""
        result = messagebox.askyesno("确认", "这将清理数据库中的无效记录，确定要继续吗？")
        if not result:
            return

        # 这里可以添加数据库清理逻辑
        messagebox.showinfo("提示", "数据库清理功能待实现")

    def on_closing(self):
        """窗口关闭事件"""
        try:
            self.window.destroy()
        except Exception as e:
            logging.error(f"关闭知识库管理窗口失败: {e}")

class SearchDialog:
    """搜索对话框"""

    def __init__(self, parent, knowledge_base):
        self.parent = parent
        self.knowledge_base = knowledge_base
        self.create_dialog()

    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("🔍 知识库搜索")
        self.dialog.geometry("600x400")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # 居中显示
        self.center_dialog()

        # 创建界面
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 搜索输入
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="搜索查询:").pack(anchor=tk.W)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Microsoft YaHei', 10))
        search_entry.pack(fill=tk.X, pady=(5, 0))
        search_entry.bind("<Return>", lambda e: self.perform_search())

        # 搜索按钮
        ttk.Button(search_frame, text="🔍 搜索", command=self.perform_search).pack(pady=(5, 0))

        # 结果显示
        result_frame = ttk.LabelFrame(main_frame, text="搜索结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        # 结果列表
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, font=('Microsoft YaHei', 9))
        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scrollbar.set)

        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 关闭按钮
        ttk.Button(main_frame, text="关闭", command=self.dialog.destroy).pack(pady=(10, 0))

        # 焦点设置
        search_entry.focus_set()

    def center_dialog(self):
        """对话框居中"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

    def perform_search(self):
        """执行搜索"""
        query = self.search_var.get().strip()
        if not query:
            return

        try:
            results = self.knowledge_base.search_documents(query, limit=10)

            self.result_text.delete(1.0, tk.END)

            if not results:
                self.result_text.insert(tk.END, "未找到相关文档。")
                return

            self.result_text.insert(tk.END, f"找到 {len(results)} 个相关文档:\n\n")

            for i, result in enumerate(results, 1):
                self.result_text.insert(tk.END, f"{i}. {result['file_name']}\n")
                self.result_text.insert(tk.END, f"   相关性: {result.get('relevance_score', 0):.2f}\n")
                self.result_text.insert(tk.END, f"   分类: {result.get('category', '未分类')}\n")

                if result.get('snippets'):
                    self.result_text.insert(tk.END, f"   相关片段: {result['snippets'][0][:100]}...\n")

                self.result_text.insert(tk.END, "\n")

        except Exception as e:
            logging.error(f"搜索失败: {e}")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"搜索失败: {e}")

def show_knowledge_base_window(parent=None):
    """显示知识库管理窗口"""
    try:
        window = KnowledgeBaseWindow(parent)
        return window
    except Exception as e:
        logging.error(f"显示知识库管理窗口失败: {e}")
        if parent:
            messagebox.showerror("错误", f"打开知识库管理失败: {e}")
        return None

if __name__ == "__main__":
    # 测试运行
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    app = KnowledgeBaseWindow()
    root.mainloop()
