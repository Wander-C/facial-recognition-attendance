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
            from huaweicloudsdkcore.auth.credentials import BasicCredentials as BasicAuthenticator
            from huaweicloudsdkfrs.v2 import FrsClient, FrsClientBuilder
            from huaweicloudsdkfrs.v2.model import (
                DetectFaceByBase64Request,
                SearchFaceByBase64Request,
                AddFacesByBase64Request,
                DeleteFaceRequest
            )
            
            self.FrsClient = FrsClient
            self.FrsClientBuilder = FrsClientBuilder
            self.DetectFaceByBase64Request = DetectFaceByBase64Request
            self.SearchFaceByBase64Request = SearchFaceByBase64Request
            self.AddFacesByBase64Request = AddFacesByBase64Request
            self.DeleteFaceRequest = DeleteFaceRequest
            
            # 创建客户端
            auth = BasicAuthenticator(
                ak=settings.HWC_AK,
                sk=settings.HWC_SK
            )
            
            self.client = FrsClientBuilder() \
                .with_region(settings.HWC_REGION_NAME) \
                .with_credentials(auth) \
                .build()
            
            logger.info("FRS服务初始化成功")
        
        except Exception as e:
            logger.error(f"FRS服务初始化失败: {str(e)}")
            self.client = None
    
    def _image_to_base64(self, image_data: bytes) -> str:
        """将图像数据转换为Base64"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def _compress_image(self, image_data: bytes, quality: int = 85) -> bytes:
        """压缩图像"""
        try:
            img = Image.open(BytesIO(image_data))
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
            # 压缩图像
            image_data = self._compress_image(image_data)
            base64_image = self._image_to_base64(image_data)
            
            # 创建请求
            request = self.DetectFaceByBase64Request()
            request.body.image_base64 = base64_image
            
            # 调用API
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
            # 压缩图像
            image_data = self._compress_image(image_data)
            base64_image = self._image_to_base64(image_data)
            
            # 创建请求
            request = self.AddFacesByBase64Request()
            request.body.image_base64 = base64_image
            request.body.external_image_id = external_image_id
            request.body.face_set_name = face_set_name
            
            # 调用API
            response = self.client.add_faces_by_base64(request)
            
            # 提取face_id
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
            # 压缩图像
            image_data = self._compress_image(image_data)
            base64_image = self._image_to_base64(image_data)
            
            # 创建请求
            request = self.SearchFaceByBase64Request()
            request.body.image_base64 = base64_image
            request.body.face_set_name = face_set_name
            request.body.max_faces_returned = max_faces_returned
            request.body.sort_by = "DESC"
            request.body.match_threshold = int(settings.FRS_SIMILARITY_THRESHOLD * 100)
            
            # 调用API
            response = self.client.search_face_by_base64(request)
            
            logger.info("人脸搜索完成")
            return {
                "success": True,
                "faces": response.faces if hasattr(response, 'faces') else []
            }
        
        except Exception as e:
            logger.error(f"人脸搜索失败: {str(e)}")
            raise
    
    def delete_face(self, face_id: str, face_set_name: str = None) -> Dict:
        """从人脸库中删除人脸"""
        if not self.client:
            raise Exception("FRS客户端未初始化")
        
        face_set_name = face_set_name or settings.FRS_FACE_SET_NAME
        
        try:
            # 创建请求
            request = self.DeleteFaceRequest()
            request.face_id = face_id
            request.body.face_set_name = face_set_name
            
            # 调用API
            response = self.client.delete_face(request)
            
            logger.info(f"人脸删除成功: {face_id}")
            return {
                "success": True,
                "face_id": face_id
            }
        
        except Exception as e:
            logger.error(f"人脸删除失败: {str(e)}")
            raise
