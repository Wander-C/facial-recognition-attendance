#!/usr/bin/env python
"""数据库初始化脚本"""

import sys
import logging

from config import get_settings
from utils.database import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database():
    """创建数据库"""
    settings = get_settings()
    
    # 解析数据库URL
    # Format: mysql+pymysql://user:password@host:port/database
    db_url_parts = settings.DATABASE_URL.split('://')
    if len(db_url_parts) != 2:
        logger.error("数据库URL格式错误")
        return False
    
    protocol_parts = db_url_parts[1].split('@')
    if len(protocol_parts) != 2:
        logger.error("数据库URL格式错误")
        return False
    
    user_pass = protocol_parts[0]
    host_db = protocol_parts[1]
    
    user_pass_parts = user_pass.split(':')
    user = user_pass_parts[0]
    password = user_pass_parts[1] if len(user_pass_parts) > 1 else ""
    
    host_parts = host_db.split('/')
    host_port = host_parts[0]
    database = host_parts[1] if len(host_parts) > 1 else "attendance_system"

    # 分离主机和端口
    if ':' in host_port:
        host, port = host_port.split(':')
        port = int(port)
    else:
        host = host_port
        port = 3306

    
    # 创建临时连接以创建数据库
    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"数据库 {database} 创建/确认成功")
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("开始初始化数据库...")
    
    # 创建数据库
    if not create_database():
        sys.exit(1)
    
    # 创建表
    try:
        init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        sys.exit(1)
