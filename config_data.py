"""全局配置 —— 路径、模型、检索参数统一在此管理。

所有运行时路径基于 BASE_DIR（本文件所在目录），
不依赖启动时的工作目录（从其他目录启动也不会找错数据位置）。
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ==================== 运行时数据路径 ====================
md5_path = str(BASE_DIR / "md5.text")               # MD5 去重记录
persist_directory = str(BASE_DIR / "chroma_db")     # Chroma 向量库本地存储
history_directory = str(BASE_DIR / "chat_history")  # 对话历史（按会话分文件）

# ==================== Chroma ====================
collection_name = "rag"

# ==================== 文本分割 ====================
chunk_size = 300             # 每个文本块的最大字符数
chunk_overlap = 50           # 相邻文本块的重叠字符数（防止答案被切在块边界）
separators = ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
max_split_char_number = 300  # 超过此长度才触发分割

# ==================== 检索 ====================
# 每次检索返回相似度最高的 k 个文档块（是数量，不是相似度阈值）
retrieval_top_k = 5

# ==================== 知识库记录 ====================
operator = "admin"  # 上传记录的操作者标识（写入 metadata 与 Django 记录）

# ==================== 模型（经 SiliconFlow API） ====================
address = "https://api.siliconflow.cn/v1"
embedding_model_name = "BAAI/bge-m3"
chat_model_name = "deepseek-ai/DeepSeek-V4-Flash"
