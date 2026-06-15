import os
from dotenv import load_dotenv
from functools import lru_cache
from typing import Optional

# 加载 .env 文件（如果存在）
load_dotenv()


class Settings:
    """应用配置类"""

    # 基础配置
    APP_NAME: str = "Facial Recognition Attendance System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 数据库配置（修改为你之前创建的用户和数据库）
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:123456@localhost:3306/face_sign_db"
    )

    # Redis配置（添加密码）
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", "YourRedisPassword123")  # 加上密码

    # JWT配置
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "your-secret-key-change-this-in-production"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", 24))

    # 华为云配置（⚠️ 建议从环境变量读取，不要硬编码）
    HWC_AK: str = os.getenv("HWC_AK", "HPUAGWLRYKUWDDDHEQ4K")  # 你填的AK
    HWC_SK: str = os.getenv("HWC_SK", "KgMl8gBJ82nLL7kdhTTlQmcXxiVP5kbb3xUlIrd4")  # 你填的SK
    HWC_PROJECT_ID: str = os.getenv("HWC_PROJECT_ID", "")  # 这个需要填你的项目ID
    HWC_REGION_NAME: str = os.getenv("HWC_REGION_NAME", "cn-north-4")

    # FRS服务配置
    FRS_FACE_SET_NAME: str = os.getenv(
        "FRS_FACE_SET_NAME",
        "attendance_system_faces"
    )
    FRS_SIMILARITY_THRESHOLD: float = float(
        os.getenv("FRS_SIMILARITY_THRESHOLD", 0.8)
    )
    FRS_MAX_FACES_RETURNED: int = int(
        os.getenv("FRS_MAX_FACES_RETURNED", 1)
    )

    # 限流配置
    RATE_LIMIT_PER_USER_5SEC: int = int(
        os.getenv("RATE_LIMIT_PER_USER_5SEC", 1)
    )
    RATE_LIMIT_SIGN_IN_PER_DAY: int = int(
        os.getenv("RATE_LIMIT_SIGN_IN_PER_DAY", 100)
    )

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = int(
        os.getenv("MAX_UPLOAD_SIZE", 10485760)  # 10MB
    )
    ALLOWED_IMAGE_TYPES: list = [
        "image/jpeg",
        "image/png"
    ]
    IMAGE_UPLOAD_DIR: str = os.getenv(
        "IMAGE_UPLOAD_DIR",
        "/var/uploads/attendance"
    )

    @property
    def redis_url(self) -> str:
        """构造Redis连接URL"""
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()