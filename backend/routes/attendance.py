from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi import Body
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from loguru import logger
import base64
import io
from PIL import Image

from utils.database import get_db
from models.user import User
from models.attendance_log import AttendanceLog
from routes.auth import get_current_user
from config import get_settings

router = APIRouter()
logger_instance = logger
settings = get_settings()

# 初始化华为云 FRS 客户端
try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkfrs.v2 import FrsClient
    from huaweicloudsdkfrs.v2.region.frs_region import FrsRegion
    from huaweicloudsdkfrs.v2.model import (
        DetectFaceByBase64Request,
        SearchFaceByBase64Request,
        AddFacesByBase64Request
    )

    # 创建认证对象
    auth = BasicCredentials(
        ak=settings.HWC_AK,
        sk=settings.HWC_SK,
        project_id=settings.HWC_PROJECT_ID
    )

    # 创建客户端
    frs_client = FrsClient.new_builder() \
        .with_credentials(auth) \
        .with_region(FrsRegion.value_of(settings.HWC_REGION_NAME)) \
        .build()

    FRS_AVAILABLE = True
    logger_instance.info("华为云 FRS 客户端初始化成功")

except Exception as e:
    FRS_AVAILABLE = False
    logger_instance.error(f"华为云 FRS 客户端初始化失败: {str(e)}")
    frs_client = None


def compress_image(image_base64: str, max_size_kb: int = 500) -> str:
    """压缩图片到指定大小以内（华为云有图片大小限制）"""
    try:
        image_data = base64.b64decode(image_base64)
        img = Image.open(io.BytesIO(image_data))

        # 如果是 RGBA 模式，转换为 RGB
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        # 压缩图片
        output = io.BytesIO()
        quality = 85
        img.save(output, format='JPEG', quality=quality, optimize=True)

        # 如果还是太大，继续压缩
        while len(output.getvalue()) > max_size_kb * 1024 and quality > 30:
            quality -= 10
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)

        return base64.b64encode(output.getvalue()).decode('utf-8')
    except Exception as e:
        logger_instance.warning(f"图片压缩失败: {str(e)}")
        return image_base64


@router.post("/detect-face")
async def detect_face(
        request: dict = Body(...),
):
    """使用华为云 FRS 检测图片中是否有人脸"""

    if not FRS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="人脸识别服务未初始化，请检查华为云配置"
        )

    image_base64 = request.get("image_base64")
    if not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少图片数据"
        )

    try:
        # 压缩图片
        compressed_base64 = compress_image(image_base64)

        # 创建检测请求 - 正确的设置方式
        detect_request = DetectFaceByBase64Request()
        # 直接设置 image_base64 属性
        detect_request.image_base64 = compressed_base64

        # 调用华为云 API
        response = frs_client.detect_face_by_base64(detect_request)

        face_count = len(response.faces) if hasattr(response, 'faces') and response.faces else 0

        logger_instance.info(f"人脸检测完成，检测到 {face_count} 张人脸")

        return {
            "success": True,
            "face_count": face_count,
            "has_face": face_count > 0,
            "message": f"检测到{face_count}张人脸" if face_count > 0 else "未检测到人脸，请重新拍照"
        }

    except Exception as e:
        logger_instance.error(f"人脸检测失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸检测失败: {str(e)}"
        )


@router.post("/search-face")
async def search_face_in_frs(
        request: dict = Body(...),
):
    """在华为云人脸库中搜索匹配的人脸（用于签到）"""

    if not FRS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="人脸识别服务未初始化"
        )

    image_base64 = request.get("image_base64")
    if not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少图片数据"
        )

    try:
        # 压缩图片
        compressed_base64 = compress_image(image_base64)

        # 创建搜索请求 - 正确的设置方式
        search_request = SearchFaceByBase64Request()
        search_request.image_base64 = compressed_base64
        search_request.face_set_name = settings.FRS_FACE_SET_NAME
        search_request.match_threshold = int(settings.FRS_SIMILARITY_THRESHOLD * 100)

        # 调用华为云 API
        response = frs_client.search_face_by_base64(search_request)

        faces = []
        if hasattr(response, 'faces') and response.faces:
            for face in response.faces:
                faces.append({
                    "face_id": getattr(face, 'face_id', None),
                    "external_image_id": getattr(face, 'external_image_id', None),
                    "similarity": getattr(face, 'similarity', 0)
                })

        return {
            "success": True,
            "faces": faces,
            "face_count": len(faces)
        }

    except Exception as e:
        logger_instance.error(f"人脸搜索失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸搜索失败: {str(e)}"
        )


@router.post("/add-face-to-frs")
async def add_face_to_frs(
        request: dict = Body(...),
):
    """将人脸添加到华为云人脸库（用于注册）"""

    if not FRS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="人脸识别服务未初始化"
        )

    image_base64 = request.get("image_base64")
    external_image_id = request.get("external_image_id")

    if not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少图片数据"
        )

    if not external_image_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 external_image_id"
        )

    try:
        # 压缩图片
        compressed_base64 = compress_image(image_base64)

        # 创建添加请求 - 正确的设置方式
        add_request = AddFacesByBase64Request()
        add_request.image_base64 = compressed_base64
        add_request.external_image_id = external_image_id
        add_request.face_set_name = settings.FRS_FACE_SET_NAME

        # 调用华为云 API
        response = frs_client.add_faces_by_base64(add_request)

        face_id = None
        if hasattr(response, 'faces') and response.faces:
            face_id = getattr(response.faces[0], 'face_id', None)

        logger_instance.info(f"人脸添加成功，external_image_id: {external_image_id}")

        return {
            "success": True,
            "external_image_id": external_image_id,
            "face_id": face_id,
            "message": "人脸上传成功"
        }

    except Exception as e:
        logger_instance.error(f"人脸上传失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"人脸上传失败: {str(e)}"
        )


@router.post("/sign")
async def sign_in(
        request: dict = Body(...),
        req: Request = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """用户签到 - 使用华为云 FRS 搜索人脸"""

    image_base64 = request.get("image_base64")
    if not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少图片数据"
        )

    if not FRS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="人脸识别服务未初始化"
        )

    try:
        # 压缩图片
        compressed_base64 = compress_image(image_base64)

        # 在华为云人脸库中搜索
        search_request = SearchFaceByBase64Request()
        search_request.image_base64 = compressed_base64
        search_request.face_set_name = settings.FRS_FACE_SET_NAME
        search_request.match_threshold = int(settings.FRS_SIMILARITY_THRESHOLD * 100)

        response = frs_client.search_face_by_base64(search_request)

        if not hasattr(response, 'faces') or not response.faces:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未能识别人脸，请重试"
            )

        # 获取最佳匹配
        best_match = response.faces[0]
        similarity = float(getattr(best_match, 'similarity', 0))
        external_image_id = getattr(best_match, 'external_image_id', None)

        # 检查相似度阈值
        if similarity < settings.FRS_SIMILARITY_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"人脸匹配度不足（{similarity:.2%}），请重试"
            )

        # 根据 external_image_id 查找用户
        user = db.query(User).filter(User.external_image_id == external_image_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到对应的用户"
            )

        # 获取客户端IP
        client_ip = req.client.host if req else "unknown"

        # 保存签到记录
        attendance_log = AttendanceLog(
            user_id=user.id,
            sign_time=datetime.utcnow(),
            similarity=similarity,
            sign_image_url=f"/uploads/{user.id}_{datetime.utcnow().timestamp()}.jpg",
            ip_address=client_ip
        )

        db.add(attendance_log)
        db.commit()

        logger_instance.info(f"用户 {user.user_id} 签到成功，相似度: {similarity}")

        return {
            "success": True,
            "message": "签到成功",
            "user_id": user.user_id,
            "user_name": user.real_name,
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