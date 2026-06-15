from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from loguru import logger

from utils.database import get_db
from models.user import User
from models.attendance_log import AttendanceLog
from routes.auth import get_current_user
from services.frs_service import frs_service
from config import get_settings

router = APIRouter()
logger_instance = logger
settings = get_settings()


@router.post("/detect-face")
async def detect_face(
        request: dict = Body(...),
):
    """检测图片中是否有人脸（注册时使用）"""
    image_base64 = request.get("image_base64")
    if not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少图片数据"
        )

    # 检查FRS服务是否可用（修改这里：检查 available 属性）
    if not frs_service.available:
        logger_instance.error("FRS客户端未初始化，请检查华为云配置")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="人脸识别服务未就绪，请联系管理员检查华为云配置"
        )

    try:
        # 调用FRS服务检测
        result = frs_service.detect_face(image_base64)

        face_count = result.get("face_count", 0)

        logger_instance.info(f"人脸检测完成，检测到 {face_count} 张人脸")

        return {
            "success": True,
            "face_count": face_count,
            "has_face": face_count > 0,
            "message": f"检测到{face_count}张人脸" if face_count > 0 else "未检测到人脸，请重新拍照"
        }

    except Exception as e:
        error_msg = str(e)
        logger_instance.error(f"人脸检测失败: {error_msg}")

        if "Token" in error_msg or "配置" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"人脸识别服务配置错误: {error_msg}"
            )
        elif "未检测到人脸" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未检测到人脸，请确保照片清晰且包含完整人脸"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"人脸检测失败: {error_msg}"
            )


@router.post("/sign")
async def sign_in(
        request: dict = Body(...),
        req: Request = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """用户签到：将签到照片与数据库中存储的注册照片进行比对"""
    sign_image_base64 = request.get("image_base64")
    if not sign_image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少签到照片"
        )

    # 检查FRS服务是否可用（修改这里：检查 available 属性）
    if not frs_service.available:
        logger_instance.error("FRS客户端未初始化，请检查华为云配置")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="人脸识别服务未就绪，请联系管理员检查华为云配置"
        )

    # 1. 从数据库获取该用户注册时的人脸照片
    registered_face_base64 = current_user.face_image_base64
    if not registered_face_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您尚未注册人脸信息，请联系管理员"
        )

    # 2. 检查今日是否已签到
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    existing_sign = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.sign_time >= today_start,
        AttendanceLog.sign_time < today_end
    ).first()

    if existing_sign:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="今日已签到，请勿重复签到"
        )

    # 3. 调用华为云人脸比对服务
    try:
        compare_result = frs_service.compare_faces(registered_face_base64, sign_image_base64)
        similarity = compare_result.get("similarity", 0.0)
        threshold = settings.FRS_SIMILARITY_THRESHOLD

        logger_instance.info(f"用户 {current_user.user_id} 人脸比对相似度: {similarity:.4f}, 阈值: {threshold}")

        if similarity < threshold:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"人脸验证不通过 (相似度: {similarity:.2%}，需大于 {threshold:.0%})"
            )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger_instance.error(f"人脸比对服务调用失败: {error_msg}")
        if "未检测到人脸" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未检测到人脸，请确保照片清晰且包含完整人脸"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"签到服务异常: {error_msg}"
        )

    # 4. 记录签到成功
    client_ip = req.client.host if req else None

    attendance_log = AttendanceLog(
        user_id=current_user.id,
        sign_time=datetime.utcnow(),
        similarity=similarity,
        sign_image_url=None,
        ip_address=client_ip
    )
    db.add(attendance_log)
    db.commit()

    logger_instance.info(f"用户 {current_user.user_id} 签到成功，相似度: {similarity:.4f}")

    return {
        "success": True,
        "message": "签到成功",
        "user_id": current_user.user_id,
        "user_name": current_user.real_name,
        "sign_time": attendance_log.sign_time.isoformat(),
        "similarity": similarity,
        "log_id": attendance_log.id
    }


@router.get("/sign_in_status")
async def get_sign_in_status(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取用户今日签到状态"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

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


@router.get("/records")
async def get_sign_in_records(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = 10,
        offset: int = 0
):
    """获取用户签到记录"""
    records = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id
    ).order_by(AttendanceLog.sign_time.desc()).offset(offset).limit(limit).all()

    return {
        "total": db.query(AttendanceLog).filter(AttendanceLog.user_id == current_user.id).count(),
        "records": [
            {
                "id": r.id,
                "sign_time": r.sign_time.isoformat(),
                "similarity": float(r.similarity),
                "ip_address": r.ip_address
            }
            for r in records
        ]
    }