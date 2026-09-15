"""
题库与句子切分自测 —— 全量打印每题的碎片分布，人工过目阈值效果。

用法（项目根目录）：
    python experiments/test_question_bank.py
"""
import importlib.util
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 直按路径加载 question_bank 模块：它只依赖 config_data，
# 绕开 services 包的 __init__（那里会实例化嵌入器，导入期即要求 API key）
_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE))  # question_bank 内部 import config_data
_spec = importlib.util.spec_from_file_location(
    "question_bank", _BASE / "apps" / "core" / "services" / "question_bank.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
question_bank = _mod.question_bank

total_q = total_s = short = long_ = bad = 0
for t in question_bank.topics():
    print(f"\n== {t['name']}（{t['question_count']} 题）==")
    for item in question_bank.questions(t["name"]):
        total_q += 1
        pieces = [s["text"] for s in item["sentences"]]
        total_s += len(pieces)
        flags = []
        if len(pieces) < 2:
            flags.append("仅1片!")
        if len(pieces) > 8:
            flags.append(">8片!")
        for p in pieces:
            if len(p.rstrip('。！？；，')) < 8:
                short += 1
                flags.append(f"短片<{p}>")
            if len(p) > 80:
                long_ += 1
                flags.append("长片")
        if flags:
            bad += 1
        print(f"  [{item['qid']}] {len(pieces)} 片 {' '.join(flags)}")
        for i, p in enumerate(pieces):
            print(f"      {i}: {p}")

print(f"\n合计 {total_q} 题 / {total_s} 片；异常题 {bad}；过短片 {short}；超长片 {long_}")
