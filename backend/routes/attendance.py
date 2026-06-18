from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Optional
from loguru import logger

from utils.database import get_db
from models.user import User
from models.attendance_log import AttendanceLog
from services.frs_service import frs_service
from config import get_settings
from routes.users import get_current_user

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
    """用户签到（不需要登录）"""
    try:
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

        # 获取所有已注册人脸的用户
        users_with_face = db.query(User).filter(
            User.face_image_base64.isnot(None)
        ).all()

        if not users_with_face:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="系统中没有已注册人脸的用户，请先注册"
            )

        # 遍历比对
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

        # 检查今日是否已签到
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        existing_sign = db.query(AttendanceLog).filter(
            AttendanceLog.user_id == matched_user.id,
            AttendanceLog.sign_time >= today_start,
            AttendanceLog.sign_time <= today_end
        ).first()

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

        # 记录签到
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
        db.refresh(attendance_log)

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"签到失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"签到失败: {str(e)}"
        )


@router.get("/today-status")
async def get_today_status(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取用户今日签到状态"""
    try:
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
    except Exception as e:
        logger.error(f"获取今日签到状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取状态失败: {str(e)}"
        )


@router.get("/my-records")
async def get_my_records(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        skip: int = 0,
        limit: int = 50,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
):
    """获取用户自己的签到记录（需要登录）"""
    try:
        logger.info(f"获取用户 {current_user.id} 的签到记录, skip={skip}, limit={limit}")

        query = db.query(AttendanceLog).filter(
            AttendanceLog.user_id == current_user.id
        )

        if start_date:
            try:
                start = datetime.fromisoformat(start_date)
                query = query.filter(AttendanceLog.sign_time >= start)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_date格式错误"
                )

        if end_date:
            try:
                end = datetime.fromisoformat(end_date)
                query = query.filter(AttendanceLog.sign_time <= end)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_date格式错误"
                )

        total = query.count()
        logger.info(f"总记录数: {total}")

        records = query.order_by(AttendanceLog.sign_time.desc()).offset(skip).limit(limit).all()
        logger.info(f"返回记录数: {len(records)}")

        # 构建返回数据
        records_data = []
        for r in records:
            records_data.append({
                "id": r.id,
                "sign_time": r.sign_time.isoformat() if r.sign_time else None,
                "similarity": float(r.similarity) if r.similarity else 0.0,
                "ip_address": r.ip_address
            })

        result = {
            "total": total,
            "skip": skip,
            "limit": limit,
            "records": records_data
        }
        logger.info(f"返回数据: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取签到记录失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取记录失败: {str(e)}"
        )


@router.get("/statistics")
async def get_statistics(
        days: int = 7,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取签到统计信息"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="days应在1-365之间"
            )

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        records = db.query(AttendanceLog).filter(
            AttendanceLog.user_id == current_user.id,
            AttendanceLog.sign_time >= start_date,
            AttendanceLog.sign_time <= end_date
        ).all()

        total_sign_ins = len(records)
        avg_similarity = (
            sum(float(log.similarity) for log in records) / len(records)
            if records else 0
        )

        daily_stats = {}
        for log in records:
            date_key = log.sign_time.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = []
            daily_stats[date_key].append({
                "sign_time": log.sign_time.isoformat(),
                "similarity": float(log.similarity)
            })

        return {
            "period": f"最近{days}天",
            "total_sign_ins": total_sign_ins,
            "avg_similarity": round(avg_similarity, 4),
            "daily_stats": daily_stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计失败: {str(e)}"
        )