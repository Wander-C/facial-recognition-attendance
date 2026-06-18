from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
import logging

from utils.database import get_db
from utils.security import hash_password, verify_password
from models.user import User
from config import get_settings
from services.frs_service import frs_service

router = APIRouter()
settings = get_settings()
security = HTTPBearer()
logger = logging.getLogger(__name__)


@router.post("/register")
async def register(
        request: dict = Body(...),
        db: Session = Depends(get_db)
):
    """用户注册：填写基本信息 + 上传人脸照片"""
    user_id = request.get("user_id")
    password = request.get("password")
    real_name = request.get("real_name")
    face_image_base64 = request.get("face_image_base64")

    if not user_id or not password or not real_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请填写所有信息"
        )

    if not face_image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先拍照上传人脸"
        )

    existing_user = db.query(User).filter(User.user_id == user_id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号已存在"
        )

    if not frs_service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="人脸识别服务未就绪"
        )

    try:
        detect_result = frs_service.detect_face(face_image_base64)
        if not detect_result.get("has_face"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="照片中未检测到有效人脸，请重新拍摄"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"人脸检测失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸检测失败: {str(e)}"
        )

    hashed_password = hash_password(password)
    new_user = User(
        user_id=user_id,
        password_hash=hashed_password,
        real_name=real_name,
        face_image_base64=face_image_base64
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"用户 {new_user.user_id} 注册成功")
    return {
        "success": True,
        "message": "注册成功",
        "user_id": new_user.user_id,
        "real_name": new_user.real_name
    }


@router.post("/login")
async def login(
        request: dict = Body(...),
        db: Session = Depends(get_db)
):
    """用户登录"""
    user_id = request.get("user_id")
    password = request.get("password")

    if not user_id or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请填写学号和密码"
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号或密码错误"
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="学号或密码错误"
        )

    expires_delta = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": str(user.id), "user_id": user.user_id, "exp": expire}
    access_token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "real_name": user.real_name
    }


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证"
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    return user