from pathlib import Path
import os

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
UPLOADS_DIR = DATA_DIR / "uploads"
VECTORS_DIR = DATA_DIR / "vectors"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
CACHE_DIR = DATA_DIR / "cache"
SPLITTER_CACHE_DIR = CACHE_DIR / "splitter"
EXPORTS_DIR = DATA_DIR / "exports"
RESULTS_DIR = DATA_DIR / "processed" / "results"

# 数据库目录
DB_DIR = DATA_DIR / "db"
MONGODB_DIR = DB_DIR / "mongodb"
MILVUS_DIR = DB_DIR / "milvus"
CHROMA_DIR = DB_DIR / "chroma"

# 日志目录
LOGS_DIR = PROJECT_ROOT / "logs"
APP_LOGS_DIR = LOGS_DIR / "app"
API_LOGS_DIR = APP_LOGS_DIR / "api"
WORKER_LOGS_DIR = APP_LOGS_DIR / "worker"
DEBUG_LOGS_DIR = APP_LOGS_DIR / "debug"
TEST_LOGS_DIR = LOGS_DIR / "tests"
SERVICES_LOGS_DIR = LOGS_DIR / "services"

# 确保所有目录存在
for dir_path in [
    RAW_DATA_DIR, PROCESSED_DATA_DIR, UPLOADS_DIR, VECTORS_DIR,
    EMBEDDINGS_DIR, CACHE_DIR, SPLITTER_CACHE_DIR, EXPORTS_DIR,
    RESULTS_DIR, MONGODB_DIR, MILVUS_DIR, CHROMA_DIR,
    API_LOGS_DIR, WORKER_LOGS_DIR, DEBUG_LOGS_DIR, TEST_LOGS_DIR,
    SERVICES_LOGS_DIR
]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 环境变量中的路径
def get_env_path(env_var: str, default_path: Path) -> Path:
    """获取环境变量中的路径，如果不存在则使用默认路径"""
    path_str = os.getenv(env_var)
    return Path(path_str) if path_str else default_path 