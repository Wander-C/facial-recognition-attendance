# services/frs_service.py
import logging
from typing import Dict, Optional
import base64
from io import BytesIO
from PIL import Image

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FRSService:
    """华为云FRS服务封装"""

    def __init__(self):
        """初始化FRS服务"""
        try:
            # 正确的导入方式
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkfrs.v2 import FrsClient
            from huaweicloudsdkfrs.v2.region.frs_region import FrsRegion
            from huaweicloudsdkfrs.v2.model import (
                DetectFaceByBase64Request,
                SearchFaceByBase64Request,
                AddFacesByBase64Request,
                # 注意：官方SDK可能没有DeleteFaceRequest这个单独的类
                # 删除人脸的功能可能通过其他方式实现，我们先注释掉
            )

            # 存储模型类供方法使用
            self.DetectFaceByBase64Request = DetectFaceByBase64Request
            self.SearchFaceByBase64Request = SearchFaceByBase64Request
            self.AddFacesByBase64Request = AddFacesByBase64Request

            # 创建认证对象（必须包含 project_id）
            auth = BasicCredentials(
                ak=settings.HWC_AK,
                sk=settings.HWC_SK,
                project_id=settings.HWC_PROJECT_ID  # 这个必须在.env中配置正确
            )

            # 创建客户端 - 这是官方文档推荐的方式
            self.client = FrsClient.new_builder() \
                .with_credentials(auth) \
                .with_region(FrsRegion.value_of(settings.HWC_REGION_NAME)) \
                .build()

            logger.info("FRS服务初始化成功")

        except Exception as e:
            logger.error(f"FRS服务初始化失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.client = None

    def _image_to_base64(self, image_data: bytes) -> str:
        """将图像数据转换为Base64"""
        return base64.b64encode(image_data).decode('utf-8')

    def _compress_image(self, image_data: bytes, quality: int = 85) -> bytes:
        """压缩图像"""
        try:
            img = Image.open(BytesIO(image_data))
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()
        except Exception as e:
            logger.warning(f"图像压缩失败: {str(e)}，使用原始图像")
            return image_data

    def detect_face(self, image_data: bytes) -> Dict:
        """检测图像中的人脸"""
        if not self.client:
            raise Exception("FRS客户端未初始化")

        try:
            image_data = self._compress_image(image_data)
            base64_image = self._image_to_base64(image_data)

            # 创建请求并设置参数
            request = self.DetectFaceByBase64Request()
            # 根据官方文档，请求体的设置方式
            request.body = type('Body', (), {})()
            request.body.image_base64 = base64_image

            response = self.client.detect_face_by_base64(request)

            logger.info("人脸检测成功")
            return {
                "success": True,
                "faces": response.faces if hasattr(response, 'faces') else []
            }

        except Exception as e:
            logger.error(f"人脸检测失败: {str(e)}")
            raise

    def add_face(
            self,
            image_data: bytes,
            external_image_id: str,
            face_set_name: str = None
    ) -> Dict:
        """添加人脸到人脸库"""
        if not self.client:
            raise Exception("FRS客户端未初始化")

        face_set_name = face_set_name or settings.FRS_FACE_SET_NAME

        try:
            image_data = self._compress_image(image_data)
            base64_image = self._image_to_base64(image_data)

            request = self.AddFacesByBase64Request()
            request.body = type('Body', (), {})()
            request.body.image_base64 = base64_image
            request.body.external_image_id = external_image_id
            request.body.face_set_name = face_set_name

            response = self.client.add_faces_by_base64(request)

            face_id = None
            if hasattr(response, 'faces') and response.faces:
                face_id = response.faces[0].get('face_id')

            logger.info(f"人脸添加成功: {external_image_id}")
            return {
                "success": True,
                "face_id": face_id,
                "external_image_id": external_image_id
            }

        except Exception as e:
            logger.error(f"人脸添加失败: {str(e)}")
            raise

    def search_face(
            self,
            image_data: bytes,
            face_set_name: str = None,
            max_faces_returned: int = None
    ) -> Dict:
        """在人脸库中搜索匹配的人脸"""
        if not self.client:
            raise Exception("FRS客户端未初始化")

        face_set_name = face_set_name or settings.FRS_FACE_SET_NAME
        max_faces_returned = max_faces_returned or settings.FRS_MAX_FACES_RETURNED

        try:
            image_data = self._compress_image(image_data)
            base64_image = self._image_to_base64(image_data)

            request = self.SearchFaceByBase64Request()
            request.body = type('Body', (), {})()
            request.body.image_base64 = base64_image
            request.body.face_set_name = face_set_name
            request.body.max_faces_returned = max_faces_returned
            request.body.match_threshold = int(settings.FRS_SIMILARITY_THRESHOLD * 100)

            response = self.client.search_face_by_base64(request)

            logger.info("人脸搜索完成")
            return {
                "success": True,
                "faces": response.faces if hasattr(response, 'faces') else []
            }

        except Exception as e:
            logger.error(f"人脸搜索失败: {str(e)}")
            raise

    def delete_face(self, face_id: str = None, external_image_id: str = None, face_set_name: str = None) -> Dict:
        """从人脸库中删除人脸

        根据官方API文档，删除人脸可以通过 face_id 或 external_image_id
        """
        if not self.client:
            raise Exception("FRS客户端未初始化")

        face_set_name = face_set_name or settings.FRS_FACE_SET_NAME

        try:
            # 根据官方文档，删除人脸是直接调用客户端的 delete_face 方法
            # 传参方式可能需要根据实际SDK版本调整
            response = self.client.delete_face(
                face_set_name=face_set_name,
                face_id=face_id,
                external_image_id=external_image_id
            )

            logger.info(f"人脸删除成功: face_id={face_id}, external_image_id={external_image_id}")
            return {
                "success": True,
                "face_id": face_id,
                "external_image_id": external_image_id
            }

        except Exception as e:
            logger.error(f"人脸删除失败: {str(e)}")
            raise