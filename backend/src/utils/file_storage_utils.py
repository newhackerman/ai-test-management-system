"""
文件存储工具函数
"""
import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import json

# Optional imports
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    magic = None
    MAGIC_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False

from ..core.file_storage_config import file_storage_settings
from ..models.ai_file_storage import FileType
import logging

logger = logging.getLogger(__name__)


class FileStorageUtils:
    """文件存储工具类"""
    
    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """计算文件SHA256哈希值"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    @staticmethod
    def calculate_content_hash(content: bytes) -> str:
        """计算内容SHA256哈希值"""
        return hashlib.sha256(content).hexdigest()
    
    @staticmethod
    def detect_mime_type(file_path: Path) -> str:
        """检测文件MIME类型"""
        if MAGIC_AVAILABLE:
            try:
                # 使用python-magic检测
                mime_type = magic.from_file(str(file_path), mime=True)
                if mime_type:
                    return mime_type
            except Exception as e:
                logger.warning(f"Failed to detect MIME type with magic: {e}")
        
        # 回退到mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def get_file_type(mime_type: str) -> FileType:
        """根据MIME类型确定文件类型"""
        if mime_type.startswith('image/'):
            return FileType.IMAGE
        elif mime_type.startswith('audio/'):
            return FileType.AUDIO
        elif mime_type.startswith('video/'):
            return FileType.VIDEO
        elif mime_type in [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'text/markdown',
            'text/html',
            'text/rtf'
        ]:
            return FileType.DOCUMENT
        elif mime_type in [
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed',
            'application/x-tar',
            'application/gzip'
        ]:
            return FileType.ARCHIVE
        elif mime_type in [
            'text/x-python',
            'text/javascript',
            'text/css',
            'application/x-sh',
            'text/x-java-source'
        ] or mime_type.startswith('text/x-'):
            return FileType.CODE
        elif mime_type in [
            'application/json',
            'text/csv',
            'application/xml',
            'text/xml'
        ]:
            return FileType.DATA
        else:
            return FileType.OTHER
    
    @staticmethod
    def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
        """提取图片元数据"""
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, cannot extract image metadata")
            return {}
            
        try:
            with Image.open(file_path) as img:
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                }
                
                # 提取EXIF数据
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    if exif:
                        metadata['exif'] = {k: v for k, v in exif.items() if isinstance(v, (str, int, float))}
                
                return metadata
        except Exception as e:
            logger.warning(f"Failed to extract image metadata: {e}")
            return {}
    
    @staticmethod
    def extract_document_metadata(file_path: Path) -> Dict[str, Any]:
        """提取文档元数据"""
        metadata = {}
        
        try:
            # 对于PDF文件
            if file_path.suffix.lower() == '.pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        metadata['pages'] = len(reader.pages)
                        if reader.metadata:
                            metadata.update({
                                'title': reader.metadata.get('/Title'),
                                'author': reader.metadata.get('/Author'),
                                'subject': reader.metadata.get('/Subject'),
                                'creator': reader.metadata.get('/Creator'),
                                'producer': reader.metadata.get('/Producer'),
                                'creation_date': reader.metadata.get('/CreationDate'),
                                'modification_date': reader.metadata.get('/ModDate')
                            })
                except ImportError:
                    logger.warning("PyPDF2 not installed, skipping PDF metadata extraction")
                except Exception as e:
                    logger.warning(f"Failed to extract PDF metadata: {e}")
            
            # 对于Office文档
            elif file_path.suffix.lower() in ['.docx', '.xlsx', '.pptx']:
                try:
                    import zipfile
                    with zipfile.ZipFile(file_path, 'r') as zip_file:
                        # 读取核心属性
                        if 'docProps/core.xml' in zip_file.namelist():
                            core_xml = zip_file.read('docProps/core.xml').decode('utf-8')
                            # 简单的XML解析（可以使用更复杂的解析器）
                            if '<dc:title>' in core_xml:
                                title_start = core_xml.find('<dc:title>') + 10
                                title_end = core_xml.find('</dc:title>')
                                if title_end > title_start:
                                    metadata['title'] = core_xml[title_start:title_end]
                            
                            if '<dc:creator>' in core_xml:
                                creator_start = core_xml.find('<dc:creator>') + 12
                                creator_end = core_xml.find('</dc:creator>')
                                if creator_end > creator_start:
                                    metadata['author'] = core_xml[creator_start:creator_end]
                except Exception as e:
                    logger.warning(f"Failed to extract Office document metadata: {e}")
            
            # 对于文本文件
            elif file_path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.html', '.css']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        metadata['lines'] = len(content.splitlines())
                        metadata['characters'] = len(content)
                        metadata['encoding'] = 'utf-8'
                except UnicodeDecodeError:
                    try:
                        with open(file_path, 'r', encoding='gbk') as f:
                            content = f.read()
                            metadata['lines'] = len(content.splitlines())
                            metadata['characters'] = len(content)
                            metadata['encoding'] = 'gbk'
                    except Exception:
                        metadata['encoding'] = 'unknown'
                except Exception as e:
                    logger.warning(f"Failed to extract text file metadata: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to extract document metadata: {e}")
        
        return metadata
    
    @staticmethod
    def extract_file_metadata(file_path: Path, mime_type: str) -> Dict[str, Any]:
        """提取文件元数据"""
        metadata = {
            'file_size': file_path.stat().st_size,
            'created_time': file_path.stat().st_ctime,
            'modified_time': file_path.stat().st_mtime,
            'mime_type': mime_type
        }
        
        # 根据文件类型提取特定元数据
        if mime_type.startswith('image/'):
            metadata.update(FileStorageUtils.extract_image_metadata(file_path))
        elif mime_type.startswith('application/') or mime_type.startswith('text/'):
            metadata.update(FileStorageUtils.extract_document_metadata(file_path))
        
        return metadata
    
    @staticmethod
    def validate_file_security(file_path: Path, mime_type: str) -> Tuple[bool, Optional[str]]:
        """验证文件安全性"""
        # 检查文件扩展名
        if file_storage_settings.is_extension_blocked(file_path.name):
            return False, f"文件扩展名 {file_path.suffix} 被禁止"
        
        # 检查文件大小
        file_size = file_path.stat().st_size
        if file_size == 0:
            return False, "文件为空"
        
        # 检查MIME类型和实际文件内容是否匹配
        detected_mime = FileStorageUtils.detect_mime_type(file_path)
        if detected_mime != mime_type:
            logger.warning(f"MIME type mismatch: declared={mime_type}, detected={detected_mime}")
        
        # 基本的恶意文件检查
        if mime_type in ['application/x-executable', 'application/x-msdownload']:
            return False, "不允许上传可执行文件"
        
        # 检查文件头部是否包含恶意内容
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # 读取前1KB
                
                # 检查常见的恶意文件签名
                malicious_signatures = [
                    b'MZ',  # Windows可执行文件
                    b'\x7fELF',  # Linux可执行文件
                    b'<script',  # 可能的脚本注入
                    b'javascript:',  # JavaScript协议
                    b'vbscript:',  # VBScript协议
                ]
                
                for signature in malicious_signatures:
                    if signature in header.lower():
                        return False, f"文件包含可疑内容: {signature.decode('utf-8', errors='ignore')}"
        
        except Exception as e:
            logger.warning(f"Failed to scan file for malicious content: {e}")
        
        return True, None
    
    @staticmethod
    def generate_thumbnail(file_path: Path, output_path: Path, size: Tuple[int, int] = (200, 200)) -> bool:
        """生成缩略图"""
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, cannot generate thumbnail")
            return False
            
        try:
            with Image.open(file_path) as img:
                # 转换为RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 生成缩略图
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # 保存缩略图
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                
                return True
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {e}")
            return False
    
    @staticmethod
    def compress_image(file_path: Path, output_path: Path, quality: int = 85, max_size: Optional[Tuple[int, int]] = None) -> bool:
        """压缩图片"""
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, cannot compress image")
            return False
            
        try:
            with Image.open(file_path) as img:
                # 转换为RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # 调整大小（如果指定）
                if max_size:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 保存压缩后的图片
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                return True
        except Exception as e:
            logger.error(f"Failed to compress image: {e}")
            return False
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """清理文件名，移除不安全字符"""
        # 移除路径分隔符和其他不安全字符
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
        clean_name = filename
        
        for char in unsafe_chars:
            clean_name = clean_name.replace(char, '_')
        
        # 限制文件名长度
        if len(clean_name) > 255:
            name, ext = os.path.splitext(clean_name)
            clean_name = name[:255-len(ext)] + ext
        
        return clean_name
    
    @staticmethod
    def get_file_info(file_path: Path) -> Dict[str, Any]:
        """获取文件基本信息"""
        try:
            stat = file_path.stat()
            mime_type = FileStorageUtils.detect_mime_type(file_path)
            
            return {
                'name': file_path.name,
                'size': stat.st_size,
                'mime_type': mime_type,
                'file_type': FileStorageUtils.get_file_type(mime_type),
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
                'is_file': file_path.is_file(),
                'is_dir': file_path.is_dir(),
                'exists': file_path.exists()
            }
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return {}
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小显示"""
        return file_storage_settings.format_file_size(size_bytes)