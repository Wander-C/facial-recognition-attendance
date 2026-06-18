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
print("🔥🔥🔥 attendance.py 文件被加载了 🔥🔥🔥")


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
    每次签到都写入数据库，同时返回今日已签到次数
    """
    try:
        logger.info("========== 开始签到 ==========")

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

        logger.info(f"✅ 匹配到用户: ID={matched_user.id}, 学号={matched_user.user_id}, 姓名={matched_user.real_name}")

        # 3. 写入签到记录（存用户自增主键 ID，使用系统本地时间）
        now = datetime.now()
        attendance_log = AttendanceLog(
            user_id=matched_user.id,
            sign_time=now
        )
        db.add(attendance_log)
        db.commit()

        logger.info(f"✅ 签到记录已写入数据库，ID: {attendance_log.id}, user_id: {attendance_log.user_id}")

        # 4. 查询今日已签到次数（使用系统本地时间）
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        today_count = db.query(AttendanceLog).filter(
            AttendanceLog.user_id == matched_user.id,
            AttendanceLog.sign_time >= today_start,
            AttendanceLog.sign_time <= today_end
        ).count()

        logger.info(f"📊 用户 {matched_user.user_id} 今日已签到 {today_count} 次")

        # 5. 返回结果
        return {
            "success": True,
            "already_signed": today_count > 1,
            "message": f"签到成功！今日第 {today_count} 次签到",
            "user_id": matched_user.user_id,
            "user_name": matched_user.real_name,
            "sign_time": attendance_log.sign_time.isoformat(),
            "today_count": today_count,
            "log_id": attendance_log.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 签到失败: {str(e)}")
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
    print("🔥🔥🔥 today-status 被调用了 🔥🔥🔥")
    from sqlalchemy import text
    try:
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        sql = text("""
            SELECT id, user_id, sign_time 
            FROM attendance_logs 
            WHERE user_id = :user_id 
            AND sign_time >= :start 
            AND sign_time <= :end
            ORDER BY sign_time DESC
        """)
        result = db.execute(sql, {
            "user_id": current_user.id,
            "start": today_start,
            "end": today_end
        })
        records = result.fetchall()

        today_count = len(records)

        if today_count > 0:
            latest = records[0]
            return {
                "has_signed": True,
                "sign_time": latest[2].isoformat() if latest[2] else None,
                "today_count": today_count,
                "message": f"今日已签到 {today_count} 次"
            }
        else:
            return {
                "has_signed": False,
                "today_count": 0,
                "message": "今日尚未签到"
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "has_signed": False,
            "today_count": 0,
            "message": str(e)
        }


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
    print("🔥🔥🔥 my-records 被调用了 🔥🔥🔥")
    import traceback
    try:
        from sqlalchemy import text

        logger.info("=" * 50)
        logger.info("查询签到记录")
        logger.info(f"用户: id={current_user.id}, 学号={current_user.user_id}, 姓名={current_user.real_name}")

        # 直接用原生 SQL 查询
        sql = text(
            "SELECT id, user_id, sign_time FROM attendance_logs WHERE user_id = :user_id ORDER BY sign_time DESC LIMIT :limit OFFSET :skip")
        result = db.execute(sql, {"user_id": current_user.id, "limit": limit, "skip": skip})
        records = result.fetchall()

        count_sql = text("SELECT COUNT(*) FROM attendance_logs WHERE user_id = :user_id")
        total = db.execute(count_sql, {"user_id": current_user.id}).scalar() or 0

        logger.info(f"总数: {total}, 记录数: {len(records)}")

        records_data = []
        for r in records:
            records_data.append({
                "id": r[0],
                "sign_time": r[2].isoformat() if r[2] else None
            })
            logger.info(f"  记录: id={r[0]}, user_id={r[1]}, time={r[2]}")

        result_data = {
            "total": total,
            "skip": skip,
            "limit": limit,
            "records": records_data
        }

        logger.info(f"返回数据: {result_data}")
        print(f"🔥 返回数据: {result_data}")

        return result_data

    except Exception as e:
        logger.error(f"❌ 错误: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "total": 0,
            "skip": skip,
            "limit": limit,
            "records": [],
            "error": str(e)
        }


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

        # 使用系统本地时间
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        records = db.query(AttendanceLog).filter(
            AttendanceLog.user_id == current_user.id,
            AttendanceLog.sign_time >= start_date,
            AttendanceLog.sign_time <= end_date
        ).all()

        total_sign_ins = len(records)

        daily_stats = {}
        for log in records:
            date_key = log.sign_time.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = []
            daily_stats[date_key].append({
                "sign_time": log.sign_time.isoformat()
            })

        return {
            "period": f"最近{days}天",
            "total_sign_ins": total_sign_ins,
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


@router.get("/ping")
async def ping():
    """测试接口是否正常"""
    print("🏓🏓🏓 ping 被调用了 🏓🏓🏓")
    return {"status": "pong", "message": "测试成功"}