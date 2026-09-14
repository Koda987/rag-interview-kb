"""
文本切块（chunking）—— 纯函数模块，无外部服务依赖。

被两处共用：
- knowledge_base_service.upload_by_str：入库切块
- API /knowledge/preview：前端"分段预览"（Dify 式向导第二步）

设计：与 Dify 的"文本分段与清洗"对齐——
分段标识符模式（段落/行/句子） + 最大分段长度 + 分段重叠 + 文本清洗。
"""
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
import config_data as config

# 分段标识符模式 → 分隔符优先级列表（前者优先，"" 为逐字符保底）
SEPARATOR_MODES = {
    # 段落优先：空行 > 换行 > 中英句末标点 > 空格（现有项目默认策略）
    "paragraph": ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    # 按行：换行 > 空格（适合列表、表格类文本）
    "line": ["\n", " ", ""],
    # 按句子：中英句末标点 > 空行 > 空格
    "sentence": ["。", "！", "？", ".", "!", "?", "\n\n", " ", ""],
}

# 连续空行压成单空行；行内连续空白压成单空格（保留换行）
_BLANK_LINES = re.compile(r'\n\s*\n+')
_INLINE_BLANK = re.compile(r'[^\S\n]+')

MAX_PREVIEW_CHARS = 200  # 预览接口里每段最多展示的字符数


def clean_text(text: str) -> str:
    """文本清洗：合并连续空行与连续空白。"""
    text = _BLANK_LINES.sub('\n\n', text)
    text = _INLINE_BLANK.sub(' ', text)
    return text.strip()


def split_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    mode: str | None = None,
    clean: bool | None = None,
) -> list[str]:
    """
    按参数切块。None 一律落回 config_data 默认值（与线上行为一致）。

    Args:
        text: 原始文本
        chunk_size: 每块最大字符数（默认 300）
        chunk_overlap: 相邻块重叠字符数（默认 50）
        mode: 分段标识符模式 paragraph / line / sentence
        clean: 是否先做文本清洗（默认 True）
    """
    size = chunk_size if chunk_size else config.chunk_size
    overlap = chunk_overlap if chunk_overlap is not None else config.chunk_overlap
    separators = SEPARATOR_MODES.get(mode or "paragraph", SEPARATOR_MODES["paragraph"])
    do_clean = clean if clean is not None else True

    if do_clean:
        text = clean_text(text)
    if not text:
        return []

    # 短文本不切（与原上传逻辑一致：不超过块大小时整篇入库）
    if len(text) <= size:
        return [text]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=separators,
        length_function=len,
    )
    return splitter.split_text(text)


def make_preview(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    mode: str | None = None,
    clean: bool | None = None,
    limit: int = 8,
) -> dict:
    """
    生成前端分段预览数据：总段数 + 前 limit 段（每段截断展示）。
    纯 CPU 操作，不调用任何外部 API。
    """
    chunks = split_text(text, chunk_size, chunk_overlap, mode, clean)
    preview = [
        {
            "idx": i + 1,
            "length": len(c),
            "text": c[:MAX_PREVIEW_CHARS] + ("…" if len(c) > MAX_PREVIEW_CHARS else ""),
        }
        for i, c in enumerate(chunks[:limit])
    ]
    return {
        "total": len(chunks),
        "total_chars": len(text),
        "preview": preview,
        "truncated": len(chunks) > limit,
    }
