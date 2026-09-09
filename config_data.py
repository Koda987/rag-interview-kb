
md5_path = "./md5.text"


# Chroma
collection_name = "rag"
persist_directory = "./chroma_db"


# spliter
chunk_size = 300
chunk_overlap = 50
separators = ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
max_split_char_number = 300        # 文本分割的阈值

#
similarity_threshold = 5            # 检索返回匹配的文档数量

address="https://api.siliconflow.cn/v1"
embedding_model_name = "BAAI/bge-m3"
chat_model_name = "deepseek-ai/DeepSeek-V4-Flash"

session_config = {
        "configurable": {
            "session_id": "user_001",
        }
    }
