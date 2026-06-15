# services/frs_service.py
import logging
from typing import Dict
import base64
from io import BytesIO
from PIL import Image

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FRSService:
    """华为云FRS服务封装（人脸检测与人脸比对）"""

    def __init__(self):
        self.client = None
        try:
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkfrs.v2 import FrsClient
            from huaweicloudsdkfrs.v2.region.frs_region import FrsRegion

            if not settings.HWC_AK or not settings.HWC_SK or not settings.HWC_PROJECT_ID:
                logger.warning("华为云FRS配置不完整，服务将不可用")
                return

            auth = BasicCredentials(
                ak=settings.HWC_AK,
                sk=settings.HWC_SK,
                project_id=settings.HWC_PROJECT_ID
            )

            self.client = FrsClient.new_builder() \
                .with_credentials(auth) \
                .with_region(FrsRegion.value_of(settings.HWC_REGION_NAME)) \
                .build()
            logger.info("华为云FRS客户端初始化成功")

        except Exception as e:
            logger.error(f"华为云FRS客户端初始化失败: {str(e)}")

    def _compress_image(self, image_data: bytes, quality: int = 85) -> bytes:
        """压缩图片"""
        try:
            img = Image.open(BytesIO(image_data))
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()
        except Exception as e:
            logger.warning(f"图片压缩失败: {e}")
            return image_data

    def detect_face(self, image_base64: str) -> Dict:
        """检测图片中是否有人脸"""
        if not self.client:
            raise Exception("FRS客户端未初始化")

        try:
            from huaweicloudsdkfrs.v2.model import DetectFaceByBase64Request

            # 解码并压缩
            image_data = base64.b64decode(image_base64)
            compressed_data = self._compress_image(image_data)
            compressed_base64 = base64.b64encode(compressed_data).decode('utf-8')

            request = DetectFaceByBase64Request()
            # 关键修复：使用 body 属性设置参数
            request.body = {
                "image_base64": compressed_base64
            }

            response = self.client.detect_face_by_base64(request)

            face_count = len(response.faces) if hasattr(response, 'faces') and response.faces else 0
            logger.info(f"人脸检测完成，检测到 {face_count} 张人脸")
            return {"has_face": face_count > 0, "face_count": face_count}

        except Exception as e:
            logger.error(f"人脸检测失败: {str(e)}")
            raise Exception(f"人脸检测失败: {str(e)}")

    def compare_faces(self, source_base64: str, target_base64: str) -> Dict:
        """比对两张图片中的人脸相似度"""
        if not self.client:
            raise Exception("FRS客户端未初始化")

        try:
            from huaweicloudsdkfrs.v2.model import CompareFaceByBase64Request

            # 压缩图片
            source_data = self._compress_image(base64.b64decode(source_base64))
            target_data = self._compress_image(base64.b64decode(target_base64))

            source_b64 = base64.b64encode(source_data).decode('utf-8')
            target_b64 = base64.b64encode(target_data).decode('utf-8')

            request = CompareFaceByBase64Request()
            # 关键修复：使用 body 属性设置参数
            request.body = {
                "image1_base64": source_b64,
                "image2_base64": target_b64
            }

            response = self.client.compare_face_by_base64(request)
            similarity = getattr(response, 'similarity', 0.0)

            logger.info(f"人脸比对完成，相似度: {similarity}")
            return {"success": True, "similarity": similarity}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"人脸比对失败: {error_msg}")
            if "FRS.0501" in error_msg:
                raise Exception("未检测到人脸，请确保照片清晰")
            raise Exception(f"人脸比对失败: {error_msg}")


frs_service = FRSService()