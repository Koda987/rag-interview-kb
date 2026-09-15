"""
面试官服务 —— 生成面试台词（开场白 / 逐题点评 / 场次报告）。

与 RAG 链完全独立：不需要检索，标准答案由调用方直接放进 prompt；
不触碰向量库与嵌入（interview 模式零嵌入成本）。
"""
import threading

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

import config_data as config

_OPENING = ChatPromptTemplate.from_messages([
    ("system",
     "你是一位资深而友善的技术面试官，正在面试一位准备 LLM 应用开发岗位的候选人。"
     "请用两三句话开场：打招呼、点出今天考察的主题与题数、让候选人放松。"
     "语气自然口语化，不要列表格式，全文不超过 80 字。"),
    ("user",
     "主题：{topic}\n本场题数：{count} 题\n本场形式：{mode_desc}\n"
     "请生成开场白，结尾用一句预告马上开始第一题。"),
])

_REVIEW = ChatPromptTemplate.from_messages([
    ("system",
     "你是一位资深而友善的技术面试官，正在点评候选人刚完成的一道面试题。规则：\n"
     "1. 称呼候选人用「你」，点评要具体、专业、鼓励但不吹捧；\n"
     "2. 只点评表现（拼图完成度、自由作答的要点覆盖情况），"
     "禁止复述或剧透标准答案原文；\n"
     "3. 全文不超过 120 字，不要列表；\n"
     "4. 结尾用一句自然的过渡收场（如「好，我们继续。」），不要自己出下一题。"),
    ("user",
     "题目：{question}\n"
     "标准答案要点（仅供你参考，禁止复述）：\n{points}\n"
     "拼图结果：{puzzle_desc}\n"
     "候选人自由作答（可能为空或跳过）：\n{user_answer}\n"
     "请给出点评。"),
])

_REPORT = ChatPromptTemplate.from_messages([
    ("system",
     "你是一位资深而友善的技术面试官，本场面试刚结束，请做收尾总结：\n"
     "1. 一两句总体评价（结合总分）；\n"
     "2. 点名完成得好的题；\n"
     "3. 指出薄弱的题，并各给一条针对性复习建议；\n"
     "4. 礼貌收尾。全文不超过 220 字，用自然段，不要列表。"),
    ("user",
     "主题：{topic}\n模式：{mode_desc}\n总分：{score_desc}\n"
     "逐题结果：\n{items}\n请生成本场总结。"),
])


class InterviewerService:
    """面试官台词生成（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.model = ChatOpenAI(
            base_url=config.address,
            model=config.chat_model_name,
            temperature=0.8,  # 台词类生成，稍高温度更自然
        )
        self._prompts = {
            "opening": _OPENING,
            "review": _REVIEW,
            "report": _REPORT,
        }

    def stream(self, kind: str, variables: dict):
        """按台词类型流式生成，逐 token yield。

        Args:
            kind: opening / review / report
            variables: 对应模板的填充变量
        """
        chain = self._prompts[kind] | self.model | StrOutputParser()
        for chunk in chain.stream(variables):
            yield chunk


# 全局单例
interviewer_service = InterviewerService()
