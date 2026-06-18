#!/usr/bin/env python
"""数据库初始化脚本 - 使用SQLAlchemy"""

import sys
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from config import get_settings
from utils.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_database():
    """创建数据库（如果不存在）"""
    settings = get_settings()

    # 从 DATABASE_URL 中提取数据库名
    # mysql+pymysql://root:123456@localhost:3306/face_sign_db
    db_url = settings.DATABASE_URL

    # 提取数据库名
    database_name = db_url.split('/')[-1]
    # 提取基础连接字符串（不含数据库名）
    base_url = db_url.rsplit('/', 1)[0]

    logger.info(f"数据库名: {database_name}")
    logger.info(f"基础连接URL: {base_url}")

    try:
        # 连接到MySQL服务器（不指定数据库）
        from sqlalchemy import create_engine
        temp_engine = create_engine(base_url, echo=False)

        with temp_engine.connect() as conn:
            # 检查数据库是否存在
            result = conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{database_name}'")
            )
            exists = result.fetchone()

            if not exists:
                logger.info(f"数据库 '{database_name}' 不存在，正在创建...")
                conn.execute(text(f"CREATE DATABASE `{database_name}` DEFAULT CHARACTER SET utf8mb4"))
                conn.commit()
                logger.info(f"数据库 '{database_name}' 创建成功")
            else:
                logger.info(f"数据库 '{database_name}' 已存在")

        return True

    except OperationalError as e:
        logger.error(f"数据库连接失败: {str(e)}")
        logger.error("请检查:")
        logger.error("  1. MySQL服务是否运行")
        logger.error("  2. 用户名/密码是否正确")
        logger.error("  3. 端口是否正确（默认3306）")
        return False
    except Exception as e:
        logger.error(f"创建数据库失败: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("开始初始化数据库...")
    logger.info("=" * 50)

    # 创建数据库
    if not create_database():
        logger.error("数据库创建失败，请检查配置")
        sys.exit(1)

    # 创建表
    try:
        init_db()
        logger.info("=" * 50)
        logger.info("✅ 数据库初始化完成！")
        logger.info("=" * 50)
    except Exception as e:
        logger.error(f"❌ 数据库表创建失败: {str(e)}")
        sys.exit(1)