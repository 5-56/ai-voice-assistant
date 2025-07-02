#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的文本清理模块
专门用于清理TTS朗读文本中的表情符号和特殊符号
"""

import re
import logging

def clean_text_for_tts(text: str) -> str:
    """清理文本用于TTS朗读"""
    if not text or not text.strip():
        return ""
    
    try:
        original_text = text
        
        # 1. 移除常见表情符号（直接字符替换）
        emoji_chars = [
            '😀', '😁', '😂', '🤣', '😃', '😄', '😅', '😆', '😉', '😊', '😋', '😎', '😍', '😘', '🥰', '😗', '😙', '😚', '☺️', '🙂', '🤗', '🤩', '🤔', '🤨', '😐', '😑', '😶', '🙄', '😏', '😣', '😥', '😮', '🤐', '😯', '😪', '😫', '😴', '😌', '😛', '😜', '😝', '🤤', '😒', '😓', '😔', '😕', '🙃', '🤑', '😲', '☹️', '🙁', '😖', '😞', '😟', '😤', '😢', '😭', '😦', '😧', '😨', '😩', '🤯', '😬', '😰', '😱', '🥵', '🥶', '😳', '🤪', '😵', '😡', '😠', '🤬', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '😇', '🥳', '🥺', '🤠', '🤡', '🤥', '🤫', '🤭', '🧐',
            '👍', '👎', '👌', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '👇', '☝️', '✋', '🤚', '🖐', '🖖', '👋', '🤏', '💪', '🦾', '🖕', '✍️', '🙏',
            '🎉', '💰', '❤️', '💯', '🔥', '💕', '💖', '💗', '💘', '💝', '💞', '💟', '💢', '💤', '💥', '💦', '💨', '💫', '💬', '💭', '🗯', '💮'
        ]
        
        for char in emoji_chars:
            text = text.replace(char, '')
        
        # 2. 移除装饰性符号
        decorative_chars = [
            '🌟', '🌸', '✨', '⭐', '💫', '⚡', '🌈', '🎈', '🎊', '🎁', '🎀', '🌺', '🌻', '🌷', '🌹', '🌼', '🌙', '☀️', '⛅', '🌠', '🌌'
        ]
        
        for char in decorative_chars:
            text = text.replace(char, '')
        
        # 3. 移除特殊符号
        special_chars = [
            '～', '〜', '∼', '≈', '≋', '≅', '≃', '≂', '≡', '≢', '≣', '≤', '≥',
            '★', '☆', '✦', '✧', '✩', '✪', '✫', '✬', '✭', '✮', '✯', '✰', '✱', '✲', '✳', '✴', '✵', '✶', '✷', '✸', '✹', '✺', '✻', '✼', '✽', '✾', '✿',
            '←', '↑', '→', '↓', '↔', '↕', '↖', '↗', '↘', '↙'
        ]
        
        for char in special_chars:
            text = text.replace(char, '')
        
        # 4. 处理货币和数学符号（替换为文字）
        replacements = {
            '$': '美元',
            '€': '欧元', 
            '£': '英镑',
            '¥': '人民币',
            '±': '正负',
            '×': '乘以',
            '÷': '除以',
            '≠': '不等于',
            '∞': '无穷大',
            '√': '根号',
            '²': '平方',
            '³': '立方',
            '%': '百分之',
            '‰': '千分之'
        }
        
        for symbol, replacement in replacements.items():
            text = text.replace(symbol, replacement)
        
        # 5. 移除代码块
        text = re.sub(r'```[\s\S]*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`\n]+`', '', text)
        
        # 6. 处理Markdown链接，保留链接文本
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # 7. 移除网址
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # 8. 移除邮箱
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # 9. 清理多余的空格
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # 10. 如果清理后文本为空或过短，返回原文本（可能是正常文本）
        if not text.strip() or len(text.strip()) < 3:
            # 检查原文本是否主要是中文或英文
            if re.search(r'[\u4e00-\u9fff\w]', original_text):
                return original_text.strip()
        
        return text
        
    except Exception as e:
        logging.error(f"文本清理失败: {e}")
        return original_text

def clean_text_for_display(text: str) -> str:
    """清理文本用于显示（保留更多格式）"""
    if not text:
        return ""
    
    try:
        # 只进行基本清理，保留大部分格式
        # 移除零宽字符
        for char in ['\u200B', '\u200C', '\u200D', '\u2060', '\uFEFF']:
            text = text.replace(char, '')
        
        # 标准化空格
        text = re.sub(r'[\u00A0\u2000-\u200A]', ' ', text)
        
        # 清理多余的空格
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        return text
        
    except Exception as e:
        logging.error(f"显示文本清理失败: {e}")
        return text

# 测试函数
def test_cleaner():
    """测试文本清理功能"""
    test_cases = [
        "你好😀我很开心😂今天天气不错👍",
        "🌟 这是一个测试 🌸✨",
        "～ 😉 特殊符号测试",
        "这是正常文本，应该保持不变。",
        "价格是$100，约合¥700人民币",
        "计算结果：2×3=6，约等于≈6.0"
    ]
    
    print("🧹 文本清理测试:")
    for i, text in enumerate(test_cases, 1):
        cleaned = clean_text_for_tts(text)
        print(f"{i}. 原文: {text}")
        print(f"   结果: {cleaned}")
        print(f"   长度: {len(text)} -> {len(cleaned)}")
        print()

if __name__ == "__main__":
    test_cleaner()
