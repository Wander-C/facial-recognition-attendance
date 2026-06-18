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
    db_url = settings.DATABASE_URL
    database_name = db_url.split('/')[-1]
    base_url = db_url.rsplit('/', 1)[0]

    logger.info(f"数据库名: {database_name}")
    logger.info(f"基础连接URL: {base_url}")

    try:
        from sqlalchemy import create_engine
        temp_engine = create_engine(base_url, echo=False)

        with temp_engine.connect() as conn:
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


def migrate_database():
    """执行数据库迁移"""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL, echo=False)

    try:
        with engine.connect() as conn:
            # 检查 users 表是否存在
            result = conn.execute(
                text(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'")
            )
            table_exists = result.fetchone()

            if not table_exists:
                logger.info("users 表不存在，将由 init_db 创建")
                return True

            # 检查 role 字段是否存在
            result = conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'")
            )
            column_exists = result.fetchone()

            if not column_exists:
                logger.info("正在添加 role 字段...")
                # 添加 role 字段，默认为 'user'
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN role ENUM('user', 'admin') NOT NULL DEFAULT 'user' COMMENT '用户角色' AFTER face_image_base64")
                )
                conn.commit()
                logger.info("✅ role 字段添加成功")
            else:
                logger.info("role 字段已存在，跳过迁移")

            return True

    except Exception as e:
        logger.error(f"数据库迁移失败: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("开始初始化数据库...")
    logger.info("=" * 50)

    # 创建数据库
    if not create_database():
        logger.error("数据库创建失败，请检查配置")
        sys.exit(1)

    # 执行数据库迁移（添加role字段）
    if not migrate_database():
        logger.error("数据库迁移失败")
        sys.exit(1)

    # 创建表（如果表不存在）
    try:
        init_db()
        logger.info("=" * 50)
        logger.info("✅ 数据库初始化完成！")
        logger.info("=" * 50)
    except Exception as e:
        logger.error(f"❌ 数据库表创建失败: {str(e)}")
        sys.exit(1)