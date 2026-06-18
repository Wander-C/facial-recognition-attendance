# reset_db.py
"""重置数据库表"""

from utils.database import engine, init_db
from sqlalchemy import text


def reset_database():
    """删除所有表并重新创建"""
    with engine.connect() as conn:
        # 关闭外键检查
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        # 删除所有表
        conn.execute(text("DROP TABLE IF EXISTS users"))
        conn.execute(text("DROP TABLE IF EXISTS attendance_logs"))

        # 重新开启外键检查
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

        print("✅ 旧表已删除")

    # 重新创建表
    init_db()
    print("✅ 数据库表重建成功！")


if __name__ == "__main__":
    reset_database()