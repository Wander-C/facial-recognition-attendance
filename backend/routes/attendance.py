from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from loguru import logger

from utils.database import get_db
from models.user import User
from models.attendance_log import AttendanceLog
from routes.auth import get_current_user
from services.frs_service import FRSService
from utils.cache import redis_client
from config import get_settings

router = APIRouter()
logger_instance = logger
settings = get_settings()
frs_service = FRSService()

@router.post("/sign_in")
async def sign_in(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """用户签到"""
    
    # 限流检查：5秒内不能重复签到
    rate_limit_key = f"sign_in_limit:{current_user.id}"
    if redis_client and redis_client.get(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="签到过于频繁，请稍候5秒后重试"
        )
    
    # 检查文件类型
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持JPEG和PNG格式的图片"
        )
    
    try:
        # 读取文件
        contents = await file.read()
        
        # 调用FRS服务搜索人脸
        search_result = frs_service.search_face(contents)
        
        if not search_result or not search_result.get("faces"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未能识别人脸，请重试"
            )
        
        # 获取匹配结果
        matched_face = search_result["faces"][0]
        similarity = float(matched_face.get("similarity", 0))
        
        # 检查相似度阈值
        if similarity < settings.FRS_SIMILARITY_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"人脸匹配度不足（{similarity:.2%}），请重试"
            )
        
        # 获取客户端IP
        client_ip = request.client.host if request else "unknown"
        
        # 保存签到记录
        attendance_log = AttendanceLog(
            user_id=current_user.id,
            sign_time=datetime.utcnow(),
            similarity=similarity,
            sign_image_url=f"/uploads/{current_user.id}_{datetime.utcnow().timestamp()}.jpg",
            ip_address=client_ip
        )
        
        db.add(attendance_log)
        db.commit()
        db.refresh(attendance_log)
        
        # 设置限流
        if redis_client:
            redis_client.setex(rate_limit_key, 5, 1)
        
        logger_instance.info(f"用户 {current_user.user_id} 签到成功，相似度: {similarity}")
        
        return {
            "message": "签到成功",
            "user_id": current_user.user_id,
            "real_name": current_user.real_name,
            "sign_time": attendance_log.sign_time.isoformat(),
            "similarity": similarity,
            "log_id": attendance_log.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger_instance.error(f"签到失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"签到失败: {str(e)}"
        )

@router.get("/sign_in_status")
async def get_sign_in_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户今日签到状态"""
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # 查询今日签到记录
    sign_in_today = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.sign_time >= today_start,
        AttendanceLog.sign_time < today_end
    ).first()
    
    if sign_in_today:
        return {
            "has_signed_in": True,
            "sign_time": sign_in_today.sign_time.isoformat(),
            "similarity": float(sign_in_today.similarity)
        }
    else:
        return {"has_signed_in": False}
