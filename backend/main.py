from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
import os

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 前端页面托管 ==========
# 获取前端文件夹的绝对路径
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

# 如果前端文件夹存在，则托管静态文件
if os.path.exists(frontend_path):
    # 挂载静态资源目录
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


    # 根路径直接返回 index.html
    @app.get("/")
    async def root():
        return FileResponse(os.path.join(frontend_path, "index.html"))


    # 其他非API路径也返回 index.html（用于前端路由）
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        # 如果是API请求或文档请求，则不拦截
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith(
                "openapi") or full_path.startswith("redoc"):
            pass
        else:
            file_path = os.path.join(frontend_path, full_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    # 如果前端文件夹不存在，根路径返回API信息
    @app.get("/")
    async def root():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "message": "前端页面未找到，请确保frontend文件夹存在"
        }

# ========== API路由注册 ==========
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["签到"])
app.include_router(records.router, prefix="/api/records", tags=["记录"])


# 健康检查
@app.get("/health", tags=["健康检查"])
async def health():
    """健康检查端点"""
    return {"status": "healthy"}


@app.get("/api/health", tags=["健康检查"])
async def api_health():
    """API健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )