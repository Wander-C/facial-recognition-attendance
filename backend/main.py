from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from config import get_settings
from routes import auth, users, attendance, records
from utils.database import init_db
from utils.cache import init_redis

settings = get_settings()

# 配置日志
logger.remove()
logger.add(
    "logs/app.log",
    level=settings.LOG_LEVEL,
    rotation="500 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)
logger.add(sys.stderr, level=settings.LOG_LEVEL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info("应用启动中...")
    try:
        init_db()
        await init_redis()
        logger.info("应用启动完成")
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")
        raise
    
    yield
    
    # 关闭
    logger.info("应用关闭中...")
    logger.info("应用关闭完成")

app = FastAPI(
    title=settings.APP_NAME,
    description="基于华为云FRS的人脸签到系统API",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["签到"])
app.include_router(records.router, prefix="/api/records", tags=["记录"])

@app.get("/", tags=["健康检查"])
async def root():
    """健康检查端点"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@app.get("/health", tags=["健康检查"])
async def health():
    """健康检查端点"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
