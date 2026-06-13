from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
from loguru import logger
from typing import Optional

from config import get_settings
from utils.database import get_db
from utils.security import hash_password, verify_password
from models.user import User

router = APIRouter()
settings = get_settings()

class LoginRequest(BaseModel):
    user_id: str
    password: str

class RegisterRequest(BaseModel):
    user_id: str
    password: str
    real_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = \"bearer\"
    user_id: str
    real_name: str

# 将函数定义放在最前面，避免在使用前未定义
def get_token_from_header(authorization: Optional[str] = Header(None)):
    \"\"\"从Authorization header中提取Token\"\"\"
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=\"缺少授权令牌\"
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != \"bearer\":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=\"无效的授权令牌格式\"
        )
    
    return parts[1]

def get_current_user(token: str = Depends(get_token_from_header), db: Session = Depends(get_db)):
    \"\"\"获取当前用户（JWT验证）\"\"\"
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get(\"sub\")
        user_db_id: int = payload.get(\"user_db_id\")
        if user_id is None or user_db_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=\"无效的令牌\"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=\"令牌验证失败\"
        )
    
    user = db.query(User).filter(User.id == user_db_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=\"用户不存在\"
        )
    
    return user

# 路由处理器
@router.post(\"/register\", response_model=dict)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    \"\"\"用户注册\"\"\"
    
    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.user_id == request.user_id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=\"用户ID已存在\"
        )
    
    # 创建新用户
    new_user = User(
        user_id=request.user_id,
        password_hash=hash_password(request.password),
        real_name=request.real_name
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f\"新用户注册: {request.user_id}\")
    
    return {
        \"message\": \"注册成功\",
        \"user_id\": new_user.user_id,
        \"user_db_id\": new_user.id
    }

@router.post(\"/login\", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    \"\"\"用户登录\"\"\"
    
    # 查询用户
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=\"用户ID或密码错误\"
        )
    
    # 生成JWT Token
    payload = {
        \"sub\": user.user_id,
        \"user_db_id\": user.id,
        \"exp\": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    logger.info(f\"用户登录: {request.user_id}\")
    
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        real_name=user.real_name
    )

@router.post(\"/logout\")
async def logout(token: str = Depends(get_token_from_header)):
    \"\"\"用户登出\"\"\"
    # 可选：将Token加入黑名单
    return {\"message\": \"登出成功\"}
