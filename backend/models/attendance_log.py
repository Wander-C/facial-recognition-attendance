from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from datetime import datetime
from models.base import Base


class AttendanceLog(Base):
    """签到记录模型"""
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    sign_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="签到时间")
    similarity = Column(Numeric(5, 4), nullable=False, comment="人脸匹配相似度")
    # 修改这里：允许为 NULL，并提供默认值
    sign_image_url = Column(String(255), nullable=True, default=None, comment="签到图片URL")
    ip_address = Column(String(45), nullable=True, comment="签到IP地址")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="记录创建时间")

    def __repr__(self):
        return f"<AttendanceLog(id={self.id}, user_id={self.user_id}, similarity={self.similarity})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sign_time": self.sign_time.isoformat() if self.sign_time else None,
            "similarity": float(self.similarity) if self.similarity else None,
            "sign_image_url": self.sign_image_url,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }