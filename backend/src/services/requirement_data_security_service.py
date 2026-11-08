"""
需求管理数据安全服务

本模块实现需求管理模块的数据安全功能，包括：
- 敏感数据加密
- 数据备份机制
- 数据恢复功能
- 数据完整性验证
"""
import os
import json
import hashlib
import gzip
import shutil
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload

from ..models.requirement import Requirement, RequirementStatusHistory, RequirementReview
from ..models.requirement_permission import RequirementAuditLog
from ..models.user import User
from ..models.project import Project
from ..core.config import get_settings

settings = get_settings()


class RequirementDataSecurityService:
    """需求数据安全服务类"""
    
    def __init__(self, db: AsyncSession, encryption_key: Optional[str] = None):
        self.db = db
        self.encryption_key = encryption_key or self._generate_encryption_key()
        self.cipher_suite = self._create_cipher_suite()
        self.backup_directory = Path(settings.BACKUP_DIRECTORY if hasattr(settings, 'BACKUP_DIRECTORY') else './backups')
        self.backup_directory.mkdir(exist_ok=True)
    
    def _generate_encryption_key(self) -> str:
        """生成加密密钥。

        密钥来自配置 REQUIREMENT_ENCRYPTION_PASSWORD / _SALT（backend/.env，
        经应用 Settings 读取；脚本等场景可改用同名环境变量）。两者缺一即
        直接报错，绝不回退到任何默认值——2026-11-08 前这里用的公开默认
        字符串写死在代码里，任何人读仓库都能解密所谓“加密”的需求字段。
        """
        password = (
            getattr(settings, "REQUIREMENT_ENCRYPTION_PASSWORD", None)
            or os.environ.get("REQUIREMENT_ENCRYPTION_PASSWORD")
        )
        salt = (
            getattr(settings, "REQUIREMENT_ENCRYPTION_SALT", None)
            or os.environ.get("REQUIREMENT_ENCRYPTION_SALT")
        )
        if not password or not salt:
            raise RuntimeError(
                "需求数据加密未配置：请在 backend/.env 中设置真实的 "
                "REQUIREMENT_ENCRYPTION_PASSWORD 与 REQUIREMENT_ENCRYPTION_SALT"
            )
        salt_bytes = salt.encode() if isinstance(salt, str) else salt

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode()
    
    def _create_cipher_suite(self) -> Fernet:
        """创建加密套件"""
        return Fernet(self.encryption_key.encode())
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据"""
        if not data:
            return data
        
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            raise ValueError(f"数据加密失败: {str(e)}")
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感数据"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"数据解密失败: {str(e)}")
    
    async def encrypt_requirement_sensitive_fields(self, requirement: Requirement) -> Requirement:
        """加密需求的敏感字段"""
        # 定义需要加密的敏感字段
        sensitive_fields = ['description', 'acceptance_criteria']
        
        for field in sensitive_fields:
            if hasattr(requirement, field):
                field_value = getattr(requirement, field)
                if field_value:
                    encrypted_value = self.encrypt_sensitive_data(field_value)
                    setattr(requirement, field, encrypted_value)
        
        # 加密自定义字段中的敏感数据
        if requirement.custom_fields:
            encrypted_custom_fields = {}
            for key, value in requirement.custom_fields.items():
                if isinstance(value, str) and self._is_sensitive_field(key):
                    encrypted_custom_fields[key] = self.encrypt_sensitive_data(value)
                else:
                    encrypted_custom_fields[key] = value
            requirement.custom_fields = encrypted_custom_fields
        
        return requirement
    
    async def decrypt_requirement_sensitive_fields(self, requirement: Requirement) -> Requirement:
        """解密需求的敏感字段"""
        # 定义需要解密的敏感字段
        sensitive_fields = ['description', 'acceptance_criteria']
        
        for field in sensitive_fields:
            if hasattr(requirement, field):
                field_value = getattr(requirement, field)
                if field_value and self._is_encrypted_data(field_value):
                    try:
                        decrypted_value = self.decrypt_sensitive_data(field_value)
                        setattr(requirement, field, decrypted_value)
                    except ValueError:
                        # 如果解密失败，可能数据未加密，保持原值
                        pass
        
        # 解密自定义字段中的敏感数据
        if requirement.custom_fields:
            decrypted_custom_fields = {}
            for key, value in requirement.custom_fields.items():
                if isinstance(value, str) and self._is_sensitive_field(key) and self._is_encrypted_data(value):
                    try:
                        decrypted_custom_fields[key] = self.decrypt_sensitive_data(value)
                    except ValueError:
                        decrypted_custom_fields[key] = value
                else:
                    decrypted_custom_fields[key] = value
            requirement.custom_fields = decrypted_custom_fields
        
        return requirement
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """判断字段是否为敏感字段"""
        sensitive_keywords = [
            'password', 'secret', 'key', 'token', 'credential',
            'confidential', 'private', 'sensitive', 'personal'
        ]
        field_lower = field_name.lower()
        return any(keyword in field_lower for keyword in sensitive_keywords)
    
    def _is_encrypted_data(self, data: str) -> bool:
        """判断数据是否已加密"""
        try:
            # 尝试base64解码，如果成功且长度合理，可能是加密数据
            decoded = base64.urlsafe_b64decode(data.encode())
            return len(decoded) > 32  # Fernet加密后的最小长度
        except Exception:
            return False
    
    async def create_requirement_backup(
        self,
        project_id: Optional[int] = None,
        backup_name: Optional[str] = None,
        include_audit_logs: bool = True,
        compress: bool = True
    ) -> Dict[str, Any]:
        """创建需求数据备份"""
        if not backup_name:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"requirement_backup_{timestamp}"
        
        backup_path = self.backup_directory / backup_name
        backup_path.mkdir(exist_ok=True)
        
        backup_info = {
            "backup_name": backup_name,
            "backup_path": str(backup_path),
            "created_at": datetime.utcnow().isoformat(),
            "project_id": project_id,
            "include_audit_logs": include_audit_logs,
            "compressed": compress,
            "files": [],
            "statistics": {}
        }
        
        try:
            # 备份需求数据
            requirements_file = await self._backup_requirements(backup_path, project_id)
            backup_info["files"].append(requirements_file)
            
            # 备份需求状态历史
            status_history_file = await self._backup_requirement_status_history(backup_path, project_id)
            backup_info["files"].append(status_history_file)
            
            # 备份需求评审数据
            reviews_file = await self._backup_requirement_reviews(backup_path, project_id)
            backup_info["files"].append(reviews_file)
            
            # 备份审计日志（如果需要）
            if include_audit_logs:
                audit_logs_file = await self._backup_audit_logs(backup_path, project_id)
                backup_info["files"].append(audit_logs_file)
            
            # 生成备份元数据
            metadata_file = backup_path / "backup_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            backup_info["files"].append(str(metadata_file))
            
            # 生成校验和
            checksum_file = await self._generate_backup_checksum(backup_path)
            backup_info["files"].append(checksum_file)
            
            # 压缩备份（如果需要）
            if compress:
                compressed_file = await self._compress_backup(backup_path)
                backup_info["compressed_file"] = compressed_file
                backup_info["compressed"] = True
            
            backup_info["status"] = "success"
            backup_info["completed_at"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            backup_info["status"] = "failed"
            backup_info["error"] = str(e)
            backup_info["failed_at"] = datetime.utcnow().isoformat()
            
            # 清理失败的备份
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            raise ValueError(f"备份创建失败: {str(e)}")
        
        return backup_info
    
    async def _backup_requirements(self, backup_path: Path, project_id: Optional[int]) -> str:
        """备份需求数据"""
        query = select(Requirement).options(
            selectinload(Requirement.project)
        )
        
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        requirements = result.scalars().all()
        
        # 转换为可序列化的格式
        requirements_data = []
        for req in requirements:
            req_data = req.to_dict()
            # 解密敏感数据用于备份
            decrypted_req = await self.decrypt_requirement_sensitive_fields(req)
            req_data.update({
                'description': decrypted_req.description,
                'acceptance_criteria': decrypted_req.acceptance_criteria,
                'custom_fields': decrypted_req.custom_fields
            })
            requirements_data.append(req_data)
        
        # 保存到文件
        requirements_file = backup_path / "requirements.json"
        with open(requirements_file, 'w', encoding='utf-8') as f:
            json.dump(requirements_data, f, ensure_ascii=False, indent=2)
        
        return str(requirements_file)
    
    async def _backup_requirement_status_history(self, backup_path: Path, project_id: Optional[int]) -> str:
        """备份需求状态历史"""
        query = select(RequirementStatusHistory).options(
            selectinload(RequirementStatusHistory.requirement)
        )
        
        if project_id:
            query = query.join(Requirement).where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        status_history = result.scalars().all()
        
        # 转换为可序列化的格式
        history_data = [history.to_dict() for history in status_history]
        
        # 保存到文件
        history_file = backup_path / "requirement_status_history.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        return str(history_file)
    
    async def _backup_requirement_reviews(self, backup_path: Path, project_id: Optional[int]) -> str:
        """备份需求评审数据"""
        query = select(RequirementReview).options(
            selectinload(RequirementReview.requirement),
            selectinload(RequirementReview.comments)
        )
        
        if project_id:
            query = query.join(Requirement).where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        reviews = result.scalars().all()
        
        # 转换为可序列化的格式
        reviews_data = []
        for review in reviews:
            review_data = review.to_dict()
            review_data['comments'] = [comment.to_dict() for comment in review.comments]
            reviews_data.append(review_data)
        
        # 保存到文件
        reviews_file = backup_path / "requirement_reviews.json"
        with open(reviews_file, 'w', encoding='utf-8') as f:
            json.dump(reviews_data, f, ensure_ascii=False, indent=2)
        
        return str(reviews_file)
    
    async def _backup_audit_logs(self, backup_path: Path, project_id: Optional[int]) -> str:
        """备份审计日志"""
        query = select(RequirementAuditLog)
        
        if project_id:
            query = query.where(RequirementAuditLog.project_id == project_id)
        
        result = await self.db.execute(query)
        audit_logs = result.scalars().all()
        
        # 转换为可序列化的格式
        logs_data = [log.to_dict() for log in audit_logs]
        
        # 保存到文件
        logs_file = backup_path / "audit_logs.json"
        with open(logs_file, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, ensure_ascii=False, indent=2)
        
        return str(logs_file)
    
    async def _generate_backup_checksum(self, backup_path: Path) -> str:
        """生成备份校验和"""
        checksums = {}
        
        for file_path in backup_path.glob("*.json"):
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                checksums[file_path.name] = file_hash
        
        # 保存校验和文件
        checksum_file = backup_path / "checksums.json"
        with open(checksum_file, 'w', encoding='utf-8') as f:
            json.dump(checksums, f, ensure_ascii=False, indent=2)
        
        return str(checksum_file)
    
    async def _compress_backup(self, backup_path: Path) -> str:
        """压缩备份文件"""
        compressed_file = backup_path.with_suffix('.tar.gz')
        
        # 使用tar.gz压缩
        shutil.make_archive(
            str(backup_path),
            'gztar',
            str(backup_path.parent),
            str(backup_path.name)
        )
        
        # 删除原始目录
        shutil.rmtree(backup_path)
        
        return str(compressed_file)
    
    async def restore_requirement_backup(
        self,
        backup_path: str,
        target_project_id: Optional[int] = None,
        verify_integrity: bool = True,
        overwrite_existing: bool = False
    ) -> Dict[str, Any]:
        """恢复需求数据备份"""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise ValueError(f"备份文件不存在: {backup_path}")
        
        restore_info = {
            "backup_path": str(backup_path),
            "target_project_id": target_project_id,
            "started_at": datetime.utcnow().isoformat(),
            "verify_integrity": verify_integrity,
            "overwrite_existing": overwrite_existing,
            "restored_items": {},
            "errors": []
        }
        
        try:
            # 如果是压缩文件，先解压
            if backup_path.suffix == '.gz':
                extracted_path = await self._extract_backup(backup_path)
                backup_path = extracted_path
            
            # 验证备份完整性
            if verify_integrity:
                integrity_check = await self._verify_backup_integrity(backup_path)
                if not integrity_check["valid"]:
                    raise ValueError(f"备份完整性验证失败: {integrity_check['errors']}")
            
            # 读取备份元数据
            metadata_file = backup_path / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    backup_metadata = json.load(f)
                restore_info["backup_metadata"] = backup_metadata
            
            # 恢复需求数据
            requirements_restored = await self._restore_requirements(
                backup_path, target_project_id, overwrite_existing
            )
            restore_info["restored_items"]["requirements"] = requirements_restored
            
            # 恢复状态历史
            history_restored = await self._restore_status_history(
                backup_path, overwrite_existing
            )
            restore_info["restored_items"]["status_history"] = history_restored
            
            # 恢复评审数据
            reviews_restored = await self._restore_reviews(
                backup_path, overwrite_existing
            )
            restore_info["restored_items"]["reviews"] = reviews_restored
            
            # 恢复审计日志（可选）
            audit_logs_file = backup_path / "audit_logs.json"
            if audit_logs_file.exists():
                logs_restored = await self._restore_audit_logs(
                    backup_path, overwrite_existing
                )
                restore_info["restored_items"]["audit_logs"] = logs_restored
            
            restore_info["status"] = "success"
            restore_info["completed_at"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            restore_info["status"] = "failed"
            restore_info["error"] = str(e)
            restore_info["failed_at"] = datetime.utcnow().isoformat()
            raise ValueError(f"备份恢复失败: {str(e)}")
        
        return restore_info
    
    async def _extract_backup(self, compressed_file: Path) -> Path:
        """解压备份文件"""
        extract_path = compressed_file.parent / compressed_file.stem
        
        shutil.unpack_archive(str(compressed_file), str(extract_path))
        
        return extract_path
    
    async def _verify_backup_integrity(self, backup_path: Path) -> Dict[str, Any]:
        """验证备份完整性"""
        integrity_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 检查必需文件
        required_files = ["requirements.json", "checksums.json"]
        for required_file in required_files:
            file_path = backup_path / required_file
            if not file_path.exists():
                integrity_result["valid"] = False
                integrity_result["errors"].append(f"缺少必需文件: {required_file}")
        
        # 验证校验和
        checksums_file = backup_path / "checksums.json"
        if checksums_file.exists():
            with open(checksums_file, 'r', encoding='utf-8') as f:
                expected_checksums = json.load(f)
            
            for filename, expected_checksum in expected_checksums.items():
                file_path = backup_path / filename
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        actual_checksum = hashlib.sha256(f.read()).hexdigest()
                    
                    if actual_checksum != expected_checksum:
                        integrity_result["valid"] = False
                        integrity_result["errors"].append(f"文件校验和不匹配: {filename}")
                else:
                    integrity_result["warnings"].append(f"校验和文件中引用的文件不存在: {filename}")
        
        return integrity_result
    
    async def _restore_requirements(
        self,
        backup_path: Path,
        target_project_id: Optional[int],
        overwrite_existing: bool
    ) -> Dict[str, Any]:
        """恢复需求数据"""
        requirements_file = backup_path / "requirements.json"
        if not requirements_file.exists():
            return {"count": 0, "skipped": 0, "errors": []}
        
        with open(requirements_file, 'r', encoding='utf-8') as f:
            requirements_data = json.load(f)
        
        restored_count = 0
        skipped_count = 0
        errors = []
        
        for req_data in requirements_data:
            try:
                # 如果指定了目标项目，更新项目ID
                if target_project_id:
                    req_data["project_id"] = target_project_id
                
                # 检查是否已存在
                existing_query = select(Requirement).where(
                    Requirement.requirement_code == req_data["requirement_code"]
                )
                existing_result = await self.db.execute(existing_query)
                existing_req = existing_result.scalar_one_or_none()
                
                if existing_req and not overwrite_existing:
                    skipped_count += 1
                    continue
                
                # 创建或更新需求
                if existing_req and overwrite_existing:
                    # 更新现有需求
                    for key, value in req_data.items():
                        if hasattr(existing_req, key) and key != 'id':
                            setattr(existing_req, key, value)
                    requirement = existing_req
                else:
                    # 创建新需求
                    req_data.pop('id', None)  # 移除ID，让数据库自动生成
                    requirement = Requirement(**req_data)
                    self.db.add(requirement)
                
                # 加密敏感字段
                requirement = await self.encrypt_requirement_sensitive_fields(requirement)
                
                await self.db.commit()
                restored_count += 1
                
            except Exception as e:
                errors.append(f"恢复需求 {req_data.get('requirement_code', 'unknown')} 失败: {str(e)}")
                await self.db.rollback()
        
        return {
            "count": restored_count,
            "skipped": skipped_count,
            "errors": errors
        }
    
    async def _restore_status_history(
        self,
        backup_path: Path,
        overwrite_existing: bool
    ) -> Dict[str, Any]:
        """恢复状态历史数据"""
        history_file = backup_path / "requirement_status_history.json"
        if not history_file.exists():
            return {"count": 0, "skipped": 0, "errors": []}
        
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        restored_count = 0
        skipped_count = 0
        errors = []
        
        for history_item in history_data:
            try:
                # 检查对应的需求是否存在
                req_query = select(Requirement).where(
                    Requirement.id == history_item["requirement_id"]
                )
                req_result = await self.db.execute(req_query)
                requirement = req_result.scalar_one_or_none()
                
                if not requirement:
                    errors.append(f"需求 {history_item['requirement_id']} 不存在，跳过状态历史恢复")
                    continue
                
                # 创建状态历史记录
                history_item.pop('id', None)  # 移除ID
                status_history = RequirementStatusHistory(**history_item)
                self.db.add(status_history)
                
                await self.db.commit()
                restored_count += 1
                
            except Exception as e:
                errors.append(f"恢复状态历史失败: {str(e)}")
                await self.db.rollback()
        
        return {
            "count": restored_count,
            "skipped": skipped_count,
            "errors": errors
        }
    
    async def _restore_reviews(
        self,
        backup_path: Path,
        overwrite_existing: bool
    ) -> Dict[str, Any]:
        """恢复评审数据"""
        reviews_file = backup_path / "requirement_reviews.json"
        if not reviews_file.exists():
            return {"count": 0, "skipped": 0, "errors": []}
        
        with open(reviews_file, 'r', encoding='utf-8') as f:
            reviews_data = json.load(f)
        
        restored_count = 0
        skipped_count = 0
        errors = []
        
        for review_data in reviews_data:
            try:
                # 检查对应的需求是否存在
                req_query = select(Requirement).where(
                    Requirement.id == review_data["requirement_id"]
                )
                req_result = await self.db.execute(req_query)
                requirement = req_result.scalar_one_or_none()
                
                if not requirement:
                    errors.append(f"需求 {review_data['requirement_id']} 不存在，跳过评审恢复")
                    continue
                
                # 提取评论数据
                comments_data = review_data.pop('comments', [])
                
                # 创建评审记录
                review_data.pop('id', None)  # 移除ID
                review = RequirementReview(**review_data)
                self.db.add(review)
                await self.db.flush()  # 获取生成的ID
                
                # 创建评论记录
                for comment_data in comments_data:
                    comment_data.pop('id', None)  # 移除ID
                    comment_data['review_id'] = review.id
                    comment = RequirementReviewComment(**comment_data)
                    self.db.add(comment)
                
                await self.db.commit()
                restored_count += 1
                
            except Exception as e:
                errors.append(f"恢复评审数据失败: {str(e)}")
                await self.db.rollback()
        
        return {
            "count": restored_count,
            "skipped": skipped_count,
            "errors": errors
        }
    
    async def _restore_audit_logs(
        self,
        backup_path: Path,
        overwrite_existing: bool
    ) -> Dict[str, Any]:
        """恢复审计日志"""
        logs_file = backup_path / "audit_logs.json"
        if not logs_file.exists():
            return {"count": 0, "skipped": 0, "errors": []}
        
        with open(logs_file, 'r', encoding='utf-8') as f:
            logs_data = json.load(f)
        
        restored_count = 0
        errors = []
        
        for log_data in logs_data:
            try:
                log_data.pop('id', None)  # 移除ID
                audit_log = RequirementAuditLog(**log_data)
                self.db.add(audit_log)
                restored_count += 1
                
            except Exception as e:
                errors.append(f"恢复审计日志失败: {str(e)}")
        
        try:
            await self.db.commit()
        except Exception as e:
            errors.append(f"提交审计日志失败: {str(e)}")
            await self.db.rollback()
        
        return {
            "count": restored_count,
            "skipped": 0,
            "errors": errors
        }
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for backup_item in self.backup_directory.iterdir():
            if backup_item.is_dir() or backup_item.suffix == '.gz':
                backup_info = {
                    "name": backup_item.name,
                    "path": str(backup_item),
                    "created_at": datetime.fromtimestamp(backup_item.stat().st_ctime).isoformat(),
                    "size": backup_item.stat().st_size,
                    "is_compressed": backup_item.suffix == '.gz'
                }
                
                # 尝试读取元数据
                if backup_item.is_dir():
                    metadata_file = backup_item / "backup_metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            backup_info.update(metadata)
                        except Exception:
                            pass
                
                backups.append(backup_info)
        
        # 按创建时间排序
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        return backups
    
    async def delete_backup(self, backup_name: str) -> bool:
        """删除备份"""
        backup_path = self.backup_directory / backup_name
        
        if backup_path.exists():
            if backup_path.is_dir():
                shutil.rmtree(backup_path)
            else:
                backup_path.unlink()
            return True
        
        return False
    
    async def cleanup_old_backups(self, keep_days: int = 30) -> Dict[str, Any]:
        """清理旧备份"""
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        
        deleted_count = 0
        deleted_size = 0
        errors = []
        
        for backup_item in self.backup_directory.iterdir():
            try:
                created_time = datetime.fromtimestamp(backup_item.stat().st_ctime)
                if created_time < cutoff_date:
                    size = backup_item.stat().st_size
                    
                    if backup_item.is_dir():
                        shutil.rmtree(backup_item)
                    else:
                        backup_item.unlink()
                    
                    deleted_count += 1
                    deleted_size += size
                    
            except Exception as e:
                errors.append(f"删除备份 {backup_item.name} 失败: {str(e)}")
        
        return {
            "deleted_count": deleted_count,
            "deleted_size": deleted_size,
            "errors": errors
        }