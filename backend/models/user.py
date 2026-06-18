from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from datetime import datetime
from models.base import Base
import enum


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(20), unique=True, index=True, nullable=False, comment="工号/学号")
    password_hash = Column(String(255), nullable=False, comment="密码哈希值")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    face_image_base64 = Column(Text, nullable=True, comment="人脸照片Base64")
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False, comment="用户角色")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, real_name={self.real_name}, role={self.role})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "real_name": self.real_name,
            "has_face": self.face_image_base64 is not None,
            "role": self.role.value if self.role else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }