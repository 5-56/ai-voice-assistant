#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话管理模块
管理智能语音助手的对话历史和状态
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from config_manager import get_config

@dataclass
class Message:
    """消息数据类"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str
    token_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建"""
        return cls(**data)

@dataclass
class Conversation:
    """对话数据类"""
    id: str
    title: str
    messages: List[Message]
    created_at: str
    updated_at: str
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_tokens": self.total_tokens
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """从字典创建"""
        messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        return cls(
            id=data["id"],
            title=data["title"],
            messages=messages,
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            total_tokens=data.get("total_tokens", 0)
        )

class ConversationManager:
    """对话管理器"""
    
    def __init__(self, history_file: str = "conversation_history.json"):
        self.history_file = Path(history_file)
        self.conversations: List[Conversation] = []
        self.current_conversation: Optional[Conversation] = None
        self.config = get_config()
        self.load_history()
    
    def load_history(self) -> bool:
        """加载对话历史"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                conversations_data = data.get("conversations", [])
                self.conversations = [
                    Conversation.from_dict(conv) for conv in conversations_data
                ]
                
                logging.info(f"加载了 {len(self.conversations)} 个对话")
                return True
            else:
                # 创建空的历史文件
                self.save_history()
                logging.info("创建新的对话历史文件")
                return True
                
        except Exception as e:
            logging.error(f"加载对话历史失败: {e}")
            self.conversations = []
            return False
    
    def save_history(self) -> bool:
        """保存对话历史"""
        try:
            # 限制保存的对话数量
            max_history = self.config.get("conversation.max_history", 50)
            conversations_to_save = self.conversations[-max_history:]
            
            data = {
                "conversations": [conv.to_dict() for conv in conversations_to_save],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_conversations": len(conversations_to_save),
                    "version": "1.0.0"
                }
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"保存了 {len(conversations_to_save)} 个对话")
            return True
            
        except Exception as e:
            logging.error(f"保存对话历史失败: {e}")
            return False
    
    def create_new_conversation(self, title: str = None) -> Conversation:
        """创建新对话"""
        now = datetime.now().isoformat()
        
        if not title:
            title = f"对话 {len(self.conversations) + 1}"
        
        conversation = Conversation(
            id=f"conv_{int(datetime.now().timestamp())}",
            title=title,
            messages=[],
            created_at=now,
            updated_at=now
        )
        
        # 添加系统提示
        system_prompt = self.config.get("conversation.system_prompt", "")
        if system_prompt:
            system_message = Message(
                role="system",
                content=system_prompt,
                timestamp=now
            )
            conversation.messages.append(system_message)
        
        self.conversations.append(conversation)
        self.current_conversation = conversation
        
        logging.info(f"创建新对话: {conversation.title}")
        return conversation
    
    def add_message(self, role: str, content: str, token_count: int = None) -> Message:
        """添加消息到当前对话"""
        if not self.current_conversation:
            self.create_new_conversation()
        
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            token_count=token_count
        )
        
        self.current_conversation.messages.append(message)
        self.current_conversation.updated_at = datetime.now().isoformat()
        
        if token_count:
            self.current_conversation.total_tokens += token_count
        
        # 自动生成对话标题（基于第一个用户消息）
        if (role == "user" and 
            len([m for m in self.current_conversation.messages if m.role == "user"]) == 1):
            self.update_conversation_title(content[:30] + "..." if len(content) > 30 else content)
        
        logging.info(f"添加消息: {role} - {content[:50]}...")
        return message
    
    def update_conversation_title(self, title: str) -> bool:
        """更新当前对话标题"""
        if self.current_conversation:
            self.current_conversation.title = title
            self.current_conversation.updated_at = datetime.now().isoformat()
            return True
        return False
    
    def get_conversation_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """获取当前对话的消息（OpenAI格式）"""
        if not self.current_conversation:
            return []
        
        messages = []
        for msg in self.current_conversation.messages:
            if not include_system and msg.role == "system":
                continue
            
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史摘要"""
        history = []
        for conv in self.conversations:
            user_messages = [m for m in conv.messages if m.role == "user"]
            assistant_messages = [m for m in conv.messages if m.role == "assistant"]
            
            history.append({
                "id": conv.id,
                "title": conv.title,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "message_count": len(user_messages) + len(assistant_messages),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "total_tokens": conv.total_tokens
            })
        
        return sorted(history, key=lambda x: x["updated_at"], reverse=True)
    
    def load_conversation(self, conversation_id: str) -> bool:
        """加载指定对话"""
        for conv in self.conversations:
            if conv.id == conversation_id:
                self.current_conversation = conv
                logging.info(f"加载对话: {conv.title}")
                return True
        
        logging.warning(f"未找到对话: {conversation_id}")
        return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除指定对话"""
        for i, conv in enumerate(self.conversations):
            if conv.id == conversation_id:
                deleted_conv = self.conversations.pop(i)
                
                # 如果删除的是当前对话，清空当前对话
                if self.current_conversation and self.current_conversation.id == conversation_id:
                    self.current_conversation = None
                
                logging.info(f"删除对话: {deleted_conv.title}")
                return True
        
        return False
    
    def clear_current_conversation(self):
        """清空当前对话"""
        self.current_conversation = None
        logging.info("清空当前对话")
    
    def export_conversation(self, conversation_id: str, export_file: str) -> bool:
        """导出指定对话"""
        try:
            for conv in self.conversations:
                if conv.id == conversation_id:
                    export_path = Path(export_file)
                    
                    with open(export_path, 'w', encoding='utf-8') as f:
                        json.dump(conv.to_dict(), f, indent=2, ensure_ascii=False)
                    
                    logging.info(f"导出对话成功: {export_path}")
                    return True
            
            logging.warning(f"未找到要导出的对话: {conversation_id}")
            return False
            
        except Exception as e:
            logging.error(f"导出对话失败: {e}")
            return False
    
    def import_conversation(self, import_file: str) -> bool:
        """导入对话"""
        try:
            import_path = Path(import_file)
            
            if not import_path.exists():
                logging.error(f"导入文件不存在: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                conv_data = json.load(f)
            
            conversation = Conversation.from_dict(conv_data)
            
            # 检查是否已存在相同ID的对话
            existing_ids = [conv.id for conv in self.conversations]
            if conversation.id in existing_ids:
                # 生成新ID
                conversation.id = f"imported_{int(datetime.now().timestamp())}"
                conversation.title = f"[导入] {conversation.title}"
            
            self.conversations.append(conversation)
            logging.info(f"导入对话成功: {conversation.title}")
            return True
            
        except Exception as e:
            logging.error(f"导入对话失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取对话统计信息"""
        total_conversations = len(self.conversations)
        total_messages = sum(len(conv.messages) for conv in self.conversations)
        total_tokens = sum(conv.total_tokens for conv in self.conversations)
        
        user_messages = sum(
            len([m for m in conv.messages if m.role == "user"]) 
            for conv in self.conversations
        )
        
        assistant_messages = sum(
            len([m for m in conv.messages if m.role == "assistant"]) 
            for conv in self.conversations
        )
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "total_tokens": total_tokens,
            "average_messages_per_conversation": total_messages / max(total_conversations, 1),
            "average_tokens_per_conversation": total_tokens / max(total_conversations, 1)
        }

    def clear_all_conversations(self) -> bool:
        """清理所有对话历史"""
        try:
            self.conversations.clear()
            self.current_conversation = None
            self.save_history()
            logging.info("所有对话历史已清理")
            return True
        except Exception as e:
            logging.error(f"清理对话历史失败: {e}")
            return False

# 全局对话管理器实例
conversation_manager = ConversationManager()

def get_conversation_manager() -> ConversationManager:
    """获取对话管理器实例"""
    return conversation_manager
