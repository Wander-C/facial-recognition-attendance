from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime
from models.base import Base


class AttendanceLog(Base):
    """签到记录模型"""
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    sign_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="签到时间")

    def __repr__(self):
        return f"<AttendanceLog(id={self.id}, user_id={self.user_id}, sign_time={self.sign_time})>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sign_time": self.sign_time.isoformat() if self.sign_time else None
        }