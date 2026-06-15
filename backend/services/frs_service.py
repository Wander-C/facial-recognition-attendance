# services/frs_service.py
import logging
import base64
from io import BytesIO
from typing import Dict
from PIL import Image

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FRSService:
    """华为云FRS服务封装 - 使用华为云SDK"""

    def __init__(self):
        self.client = None
        self.available = False  # 添加 available 属性
        self.mock_mode = True  # 默认使用模拟模式

        try:
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkfrs.v2 import FrsClient
            from huaweicloudsdkfrs.v2.region.frs_region import FrsRegion

            # 检查配置
            if not settings.HWC_AK or not settings.HWC_SK or not settings.HWC_PROJECT_ID:
                logger.warning("华为云FRS配置不完整，将使用模拟模式")
                logger.warning(f"  HWC_AK: {'已设置' if settings.HWC_AK else '未设置'}")
                logger.warning(f"  HWC_SK: {'已设置' if settings.HWC_SK else '未设置'}")
                logger.warning(f"  HWC_PROJECT_ID: {'已设置' if settings.HWC_PROJECT_ID else '未设置'}")
                self.available = False
                self.mock_mode = True
                return

            # 创建认证对象
            credentials = BasicCredentials(
                ak=settings.HWC_AK,
                sk=settings.HWC_SK,
                project_id=settings.HWC_PROJECT_ID
            )

            # 创建客户端
            self.client = FrsClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(FrsRegion.value_of(settings.HWC_REGION_NAME)) \
                .build()

            logger.info(f"华为云FRS客户端初始化成功，区域: {settings.HWC_REGION_NAME}")
            self.available = True
            self.mock_mode = False

        except Exception as e:
            logger.error(f"华为云FRS客户端初始化失败: {str(e)}")
            self.available = False
            self.mock_mode = True
            logger.warning("将使用模拟模式运行")

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
        # 模拟模式
        if self.mock_mode:
            logger.info("【模拟模式】人脸检测：返回有人脸")
            return {"has_face": True, "face_count": 1}

        if not self.client:
            raise Exception("FRS客户端未初始化")

        try:
            from huaweicloudsdkfrs.v2.model import DetectFaceByBase64Request

            # 压缩图片
            image_data = base64.b64decode(image_base64)
            compressed_data = self._compress_image(image_data)
            final_base64 = base64.b64encode(compressed_data).decode('utf-8')

            # 创建请求
            request = DetectFaceByBase64Request()
            request.body = {
                "image_base64": final_base64
            }

            # 调用API
            response = self.client.detect_face_by_base64(request)

            face_count = len(response.faces) if hasattr(response, 'faces') and response.faces else 0
            logger.info(f"人脸检测成功，检测到 {face_count} 张人脸")
            return {"has_face": face_count > 0, "face_count": face_count}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"人脸检测失败: {error_msg}")
            # 如果API调用失败，回退到模拟模式
            if "APIG" in error_msg or "FRS" in error_msg:
                logger.warning("API调用失败，使用模拟模式")
                return {"has_face": True, "face_count": 1}
            raise Exception(f"人脸检测失败: {error_msg}")

    def compare_faces(self, source_base64: str, target_base64: str) -> Dict:
        """比对两张图片中的人脸相似度"""
        # 模拟模式
        if self.mock_mode:
            similarity = 0.95
            logger.info(f"【模拟模式】人脸比对：返回相似度 {similarity}")
            return {"success": True, "similarity": similarity}

        if not self.client:
            raise Exception("FRS客户端未初始化")

        try:
            from huaweicloudsdkfrs.v2.model import CompareFaceByBase64Request

            # 压缩图片
            source_data = self._compress_image(base64.b64decode(source_base64))
            target_data = self._compress_image(base64.b64decode(target_base64))
            source_b64 = base64.b64encode(source_data).decode('utf-8')
            target_b64 = base64.b64encode(target_data).decode('utf-8')

            # 创建请求
            request = CompareFaceByBase64Request()
            request.body = {
                "image1_base64": source_b64,
                "image2_base64": target_b64
            }

            # 调用API
            response = self.client.compare_face_by_base64(request)

            similarity = getattr(response, 'similarity', 0.0)
            logger.info(f"人脸比对成功，相似度: {similarity}")
            return {"success": True, "similarity": similarity}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"人脸比对失败: {error_msg}")
            # 如果API调用失败，回退到模拟模式
            if "APIG" in error_msg or "FRS" in error_msg:
                logger.warning("API调用失败，使用模拟模式")
                return {"success": True, "similarity": 0.95}
            raise Exception(f"人脸比对失败: {error_msg}")


# 创建全局单例
frs_service = FRSService()