from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from utils.database import get_db
from models.user import User
from models.attendance_log import AttendanceLog
from routes.auth import get_current_user

router = APIRouter()
logger_instance = logger

@router.get("/my_records")
async def get_my_records(
    skip: int = 0,
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取个人签到记录"""
    
    query = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id
    )
    
    # 日期筛选
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(AttendanceLog.sign_time >= start)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date格式错误，应为ISO 8601格式"
            )
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(AttendanceLog.sign_time <= end)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date格式错误，应为ISO 8601格式"
            )
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    records = query.order_by(desc(AttendanceLog.sign_time)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "records": [
            {
                "id": log.id,
                "sign_time": log.sign_time.isoformat(),
                "similarity": float(log.similarity),
                "ip_address": log.ip_address
            }
            for log in records
        ]
    }

@router.get("/statistics")
async def get_statistics(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取签到统计信息"""
    
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days应在1-365之间"
        )
    
    # 计算时间范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 查询签到记录
    records = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.sign_time >= start_date,
        AttendanceLog.sign_time <= end_date
    ).all()
    
    # 统计
    total_sign_ins = len(records)
    avg_similarity = (
        sum(float(log.similarity) for log in records) / len(records)
        if records else 0
    )
    
    # 按天统计
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

@router.get("/admin/all_records")
async def get_all_records(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有签到记录（管理员接口）"""
    
    query = db.query(AttendanceLog).join(
        User, AttendanceLog.user_id == User.id
    )
    
    if user_id:
        query = query.filter(User.user_id == user_id)
    
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
    records = query.order_by(desc(AttendanceLog.sign_time)).offset(skip).limit(limit).all()
    
    result_records = []
    for log in records:
        user = db.query(User).filter(User.id == log.user_id).first()
        if user:
            result_records.append({
                "id": log.id,
                "user_id": user.user_id,
                "real_name": user.real_name,
                "sign_time": log.sign_time.isoformat(),
                "similarity": float(log.similarity),
                "ip_address": log.ip_address
            })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "records": result_records
    }
