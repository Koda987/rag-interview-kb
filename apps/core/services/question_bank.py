"""
题库服务 —— 把 data/ 下的八股语料解析为面试题库。

语料格式：`Q: 问题` 换行 `A: 答案`，QA 之间空行分隔。
本题库直接读源文件而非 Chroma：向量库按块存取会合并相邻 QA，
而题库需要精确的问答边界与原文顺序。
"""
import re
import threading

import config_data as config

# 句末边界：中文句号/叹号/问号/分号。刻意不含英文 "."——
# 语料中英文点仅出现于小数与版本号（1.2、V4），按句切会把它们腰斩
_SENT_BOUNDARY = re.compile(r'(?<=[。！？；])')
_QA_BLOCK = re.compile(r'^Q[:：]\s*(.+?)\s*\nA[:：]\s*(.+?)\s*$', re.S)

MIN_PIECE = 8   # 碎片最短长度（去尾部标点），短于此并入相邻片
MAX_PIECE = 80  # 碎片最长长度，超长在中文逗号处二次切分


def split_sentences(answer: str) -> list[str]:
    """把标准答案切成拼图碎片（保持原序）。

    - 按中文句末标点切句，标点留在片尾
    - 过短碎片（如"等等。"）并入前一片；首片过短并入后一片
    - 过长碎片在逗号处二次切分，切出的过短尾片并回前片
    """
    text = re.sub(r'\s+', ' ', answer.strip())
    parts = [p.strip() for p in _SENT_BOUNDARY.split(text) if p.strip()]

    # —— 句间合并：短碎片归邻 ——
    merged: list[str] = []
    for piece in parts:
        if merged and len(piece.rstrip('。！？；')) < MIN_PIECE:
            merged[-1] += piece
        else:
            merged.append(piece)
    if len(merged) > 1 and len(merged[0].rstrip('。！？；')) < MIN_PIECE:
        merged[1] = merged[0] + merged[1]
        merged.pop(0)

    # —— 超长片在逗号处二次切分 ——
    final: list[str] = []
    for piece in merged:
        chunks: list[str] = []
        rest = piece
        while len(rest) > MAX_PIECE:
            cut = rest.rfind('，', MIN_PIECE - 1, MAX_PIECE)
            if cut == -1:
                break  # 前段没有可用逗号，保留长片
            chunks.append(rest[:cut + 1])
            rest = rest[cut + 1:]
        chunks.append(rest)
        if len(chunks) > 1 and len(chunks[-1].rstrip('。！？；，')) < MIN_PIECE:
            chunks[-2] += chunks[-1]
            chunks.pop()
        final.extend(chunks)
    return final


class QuestionBank:
    """题库（懒解析 + 进程内缓存；data/ 变更后重启服务生效）"""

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
        self._by_topic: dict[str, list[dict]] = {}
        self._by_qid: dict[str, dict] = {}
        self._load()

    def _load(self):
        import pathlib
        data_dir: pathlib.Path = config.BASE_DIR / "data"
        for path in sorted(data_dir.glob("*.txt")):
            topic = path.stem
            items: list[dict] = []
            text = path.read_text(encoding="utf-8")
            blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
            seq = 0
            for block in blocks:
                m = _QA_BLOCK.match(block)
                if not m:
                    continue  # 容错：不符合 Q:/A: 格式的段落直接跳过
                seq += 1
                answer = m.group(2).strip()
                item = {
                    "qid": f"{topic}#{seq}",
                    "topic": topic,
                    "question": m.group(1).strip(),
                    "answer": answer,
                    "sentences": [
                        {"idx": i, "text": s}
                        for i, s in enumerate(split_sentences(answer))
                    ],
                }
                items.append(item)
                self._by_qid[item["qid"]] = item
            if items:
                self._by_topic[topic] = items

    def topics(self) -> list[dict]:
        """[{name, question_count}]，按文件名排序"""
        return [
            {"name": name, "question_count": len(items)}
            for name, items in self._by_topic.items()
        ]

    def questions(self, topic: str) -> list[dict]:
        return self._by_topic.get(topic, [])

    def get(self, qid: str):
        return self._by_qid.get(qid)


# 全局单例
question_bank = QuestionBank()
