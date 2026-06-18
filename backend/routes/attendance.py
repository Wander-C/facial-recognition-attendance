from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from datetime import datetime, date
from loguru import logger

from utils.database import get_db
from models.user import User
from models.attendance_log import AttendanceLog
from services.frs_service import frs_service
from config import get_settings
from routes.auth import get_current_user

router = APIRouter()
settings = get_settings()


@router.post("/detect-face")
async def detect_face(
        request: dict = Body(...),
):
    """检测图片中是否有人脸"""
    image_base64 = request.get("image_base64")
    if not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少图片数据"
        )

    if not frs_service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="人脸识别服务未就绪"
        )

    try:
        result = frs_service.detect_face(image_base64)
        face_count = result.get("face_count", 0)
        return {
            "success": True,
            "face_count": face_count,
            "has_face": face_count > 0,
            "message": f"检测到{face_count}张人脸" if face_count > 0 else "未检测到人脸"
        }
    except Exception as e:
        logger.error(f"人脸检测失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸检测失败: {str(e)}"
        )


@router.post("/sign")
async def sign_in(
        request: dict = Body(...),
        req: Request = None,
        db: Session = Depends(get_db)
):
    """
    用户签到（不需要登录）
    通过人脸比对从照片库中检索用户
    已签到的用户可以再次签到，但会提示已在xx时间签过到，不重复记录
    """
    sign_image_base64 = request.get("image_base64")
    if not sign_image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少签到照片"
        )

    if not frs_service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="人脸识别服务未就绪"
        )

    # 1. 获取所有已注册人脸的用户
    users_with_face = db.query(User).filter(
        User.face_image_base64.isnot(None)
    ).all()

    if not users_with_face:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系统中没有已注册人脸的用户，请先注册"
        )

    # 2. 遍历比对
    matched_user = None
    best_similarity = 0.0
    threshold = settings.FRS_SIMILARITY_THRESHOLD

    for user in users_with_face:
        try:
            result = frs_service.compare_faces(
                user.face_image_base64,
                sign_image_base64
            )
            similarity = result.get("similarity", 0.0)
            logger.info(f"比对用户 {user.user_id} ({user.real_name}) 相似度: {similarity:.4f}")

            if similarity > best_similarity:
                best_similarity = similarity
                if similarity >= threshold:
                    matched_user = user
                    if similarity >= 0.95:
                        break
        except Exception as e:
            logger.warning(f"比对用户 {user.user_id} 失败: {str(e)}")
            continue

    if not matched_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"人脸验证不通过，最高相似度: {best_similarity:.2%}，需大于 {threshold:.0%}"
        )

    # 3. 检查今日是否已签到（只检查，不阻止）
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    existing_sign = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == matched_user.id,
        AttendanceLog.sign_time >= today_start,
        AttendanceLog.sign_time <= today_end
    ).first()

    # 4. 如果已签到，返回提示但不记录新签到
    if existing_sign:
        return {
            "success": True,
            "already_signed": True,
            "message": f"已在 {existing_sign.sign_time.strftime('%Y-%m-%d %H:%M:%S')} 签过到",
            "user_id": matched_user.user_id,
            "user_name": matched_user.real_name,
            "sign_time": existing_sign.sign_time.isoformat(),
            "similarity": float(existing_sign.similarity)
        }

    # 5. 记录签到
    client_ip = req.client.host if req else None

    attendance_log = AttendanceLog(
        user_id=matched_user.id,
        sign_time=datetime.utcnow(),
        similarity=best_similarity,
        sign_image_url=None,
        ip_address=client_ip
    )
    db.add(attendance_log)
    db.commit()

    logger.info(f"用户 {matched_user.user_id} ({matched_user.real_name}) 签到成功，相似度: {best_similarity:.4f}")

    return {
        "success": True,
        "already_signed": False,
        "message": "签到成功",
        "user_id": matched_user.user_id,
        "user_name": matched_user.real_name,
        "sign_time": attendance_log.sign_time.isoformat(),
        "similarity": best_similarity,
        "log_id": attendance_log.id
    }


@router.get("/today-status")
async def get_today_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户今日签到状态（已签/未签）"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    existing_sign = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.sign_time >= today_start,
        AttendanceLog.sign_time <= today_end
    ).first()

    if existing_sign:
        return {
            "has_signed": True,
            "sign_time": existing_sign.sign_time.isoformat(),
            "similarity": float(existing_sign.similarity),
            "message": f"已在 {existing_sign.sign_time.strftime('%Y-%m-%d %H:%M:%S')} 签到"
        }
    else:
        return {
            "has_signed": False,
            "message": "今日尚未签到"
        }


@router.get("/my-records")
async def get_my_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """获取用户自己的签到记录（需要登录）"""
    records = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id
    ).order_by(AttendanceLog.sign_time.desc()).offset(offset).limit(limit).all()

    total = db.query(AttendanceLog).filter(AttendanceLog.user_id == current_user.id).count()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
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