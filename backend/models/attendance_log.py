from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class AttendanceLog(Base):
    """签到记录模型"""
    __tablename__ = "attendance_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sign_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    similarity = Column(Numeric(5, 4), nullable=False)
    sign_image_url = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<AttendanceLog(id={self.id}, user_id={self.user_id}, similarity={self.similarity})>"
