import json
import os
import re
from datetime import datetime
from typing import Sequence

import config_data as config
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict

# 会话 ID 直接拼进文件路径，只允许安全字符，防止路径穿越（如 ../xx 写到目录外）
SESSION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def get_history(session_id):
    return FileChatMessageHistory(session_id, config.history_directory)


def list_sessions() -> list[dict]:
    """扫描历史目录，返回全部会话的摘要（按最后活跃时间倒序）。

    每个摘要：{session_id, title, message_count, updated_at}
    标题取首条用户消息（截断 24 字）；空会话与损坏文件跳过。
    """
    sessions = []
    if not os.path.isdir(config.history_directory):
        return sessions

    for name in os.listdir(config.history_directory):
        path = os.path.join(config.history_directory, name)
        if not os.path.isfile(path) or not SESSION_ID_PATTERN.fullmatch(name):
            continue
        try:
            history = FileChatMessageHistory(name, config.history_directory)
            messages = history.messages
            if not messages:
                continue  # 空会话不展示

            first_user = next(
                (m.content for m in messages if m.type == 'human'), ''
            )
            title = first_user if len(first_user) <= 24 else first_user[:24] + '…'
            sessions.append({
                'session_id': name,
                'title': title or '（未提问）',
                'message_count': len(messages),
                'updated_at': datetime.fromtimestamp(
                    os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M'),
            })
        except Exception:
            continue  # 单个文件损坏不影响整体列表

    sessions.sort(key=lambda s: s['updated_at'], reverse=True)
    return sessions


class FileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id, storage_path):
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            raise ValueError(
                f"非法会话 ID: {session_id!r}（仅允许字母/数字/下划线/连字符，长度 1-64）"
            )

        self.session_id = session_id        # 会话id
        self.storage_path = storage_path    # 不同会话id的存储文件，所在的文件夹路径
        # 完整的文件路径
        self.file_path = os.path.join(self.storage_path, session_id)

        # 确保文件夹是存在的
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        # Sequence序列 类似list、tuple
        all_messages = list(self.messages)      # 已有的消息列表
        all_messages.extend(messages)           # 新的和已有的融合成一个list

        # 将BaseMessage消息对象转为字典，再以json字符串写入文件
        new_messages = [message_to_dict(message) for message in all_messages]
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(new_messages, f)

    @property       # @property装饰器将messages方法变成成员属性用
    def messages(self) -> list[BaseMessage]:
        # 当前文件内： list[字典]
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                messages_data = json.load(f)    # 返回值就是：list[字典]
                return messages_from_dict(messages_data)
        except FileNotFoundError:
            return []

    def clear(self) -> None:
        """删除该会话的历史文件（会话列表中该行随之消失）"""
        try:
            os.remove(self.file_path)
        except FileNotFoundError:
            pass
