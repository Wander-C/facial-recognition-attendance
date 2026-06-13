from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from loguru import logger

from utils.database import get_db
from models.user import User
from routes.auth import get_current_user
from services.frs_service import FRSService
from config import get_settings

router = APIRouter()
logger_instance = logger
settings = get_settings()
frs_service = FRSService()

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户个人信息"""
    return {
        "user_id": current_user.user_id,
        "real_name": current_user.real_name,
        "has_face": current_user.external_image_id is not None,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.post("/upload_face")
async def upload_face(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传用户人脸照片到人脸库"""
    
    # 检查文件类型
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持JPEG和PNG格式的图片"
        )
    
    try:
        # 读取文件
        contents = await file.read()
        
        # 调用FRS服务添加人脸
        result = frs_service.add_face(
            image_data=contents,
            external_image_id=str(current_user.id)
        )
        
        # 保存face_id到数据库
        current_user.external_image_id = result.get("face_id")
        db.commit()
        db.refresh(current_user)
        
        logger_instance.info(f"用户 {current_user.user_id} 上传人脸成功")
        
        return {
            "message": "人脸上传成功",
            "face_id": result.get("face_id")
        }
    
    except Exception as e:
        logger_instance.error(f"上传人脸失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传人脸失败: {str(e)}"
        )

@router.delete("/delete_face")
async def delete_face(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户人脸"""
    
    if not current_user.external_image_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户还未上传人脸"
        )
    
    try:
        # 调用FRS服务删除人脸
        frs_service.delete_face(current_user.external_image_id)
        
        # 删除数据库记录
        current_user.external_image_id = None
        db.commit()
        
        logger_instance.info(f"用户 {current_user.user_id} 删除人脸成功")
        
        return {"message": "人脸删除成功"}
    
    except Exception as e:
        logger_instance.error(f"删除人脸失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除人脸失败: {str(e)}"
        )
