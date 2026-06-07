"""
文件上传工具类
"""
import os
import uuid
import aiofiles
from fastapi import UploadFile
from typing import Optional
from ..core.config import settings


class FileUtils:
    """文件上传工具类"""
    
    # 允许的图片类型
    ALLOWED_IMAGE_TYPES = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp"
    ]
    
    # 允许的文件类型
    ALLOWED_FILE_TYPES = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain"
    ]
    
    @classmethod
    async def upload_file(cls, file: UploadFile, folder: str = "uploads") -> str:
        """
        上传文件
        
        Args:
            file: 上传的文件
            folder: 存储文件夹
            
        Returns:
            文件URL
        """
        # 检查文件类型
        if file.content_type not in cls.ALLOWED_FILE_TYPES:
            raise ValueError(f"不支持的文件类型: {file.content_type}")
        
        # 生成文件名
        file_extension = file.filename.split(".")[-1] if "." in file.filename else ""
        filename = f"{uuid.uuid4()}.{file_extension}"
        
        # 创建文件夹路径
        folder_path = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # 文件完整路径
        file_path = os.path.join(folder_path, filename)
        
        # 保存文件
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)
        
        # 返回文件URL
        return f"{settings.BASE_URL}/static/{folder}/{filename}"
    
    @classmethod
    async def upload_image(cls, file: UploadFile, folder: str = "images") -> str:
        """
        上传图片
        
        Args:
            file: 上传的图片文件
            folder: 存储文件夹
            
        Returns:
            图片URL
        """
        # 检查文件类型
        if file.content_type not in cls.ALLOWED_IMAGE_TYPES:
            raise ValueError(f"不支持的图片类型: {file.content_type}")
        
        # 生成文件名
        file_extension = file.filename.split(".")[-1] if "." in file.filename else ""
        filename = f"{uuid.uuid4()}.{file_extension}"
        
        # 创建文件夹路径
        folder_path = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # 文件完整路径
        file_path = os.path.join(folder_path, filename)
        
        # 保存文件
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)
        
        # 返回图片URL
        return f"{settings.BASE_URL}/static/{folder}/{filename}"
    
    @classmethod
    async def delete_file(cls, file_url: str) -> bool:
        """
        删除文件
        
        Args:
            file_url: 文件URL
            
        Returns:
            是否删除成功
        """
        try:
            # 从URL中提取文件路径
            if file_url.startswith(settings.BASE_URL):
                file_path = file_url.replace(settings.BASE_URL, "")
                file_path = os.path.join(settings.STATIC_DIR, file_path.lstrip("/"))
            else:
                return False
            
            # 删除文件
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            
            return False
        except Exception:
            return False
    
    @classmethod
    def get_file_size(cls, file_path: str) -> Optional[int]:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        try:
            return os.path.getsize(file_path)
        except Exception:
            return None
    
    @classmethod
    def file_exists(cls, file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否存在
        """
        return os.path.exists(file_path)
    
    @classmethod
    def get_file_extension(cls, filename: str) -> str:
        """
        获取文件扩展名
        
        Args:
            filename: 文件名
            
        Returns:
            文件扩展名
        """
        return filename.split(".")[-1] if "." in filename else ""
    
    @classmethod
    def is_image_file(cls, filename: str) -> bool:
        """
        判断是否为图片文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否为图片文件
        """
        image_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
        extension = cls.get_file_extension(filename).lower()
        return extension in image_extensions
    
    @classmethod
    def format_file_size(cls, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            格式化后的文件大小
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"