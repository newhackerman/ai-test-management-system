"""
需求批量状态管理服务

本模块实现需求的批量状态变更功能，包括批量操作的合法性验证、
操作进度跟踪和部分成功处理。
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, in_
from enum import Enum as PyEnum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models.requirement import Requirement, RequirementStatus
from ..models.requirement_status_flow import PreconditionCheckResult
from ..services.requirement_status_validator import RequirementStatusValidator
from ..services.requirement_status_actions import RequirementStatusActionManager
from ..services.requirement_notification_service import RequirementNotificationService


class BatchOperationStatus(PyEnum):
    """批量操作状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BatchOperationResult:
    """批量操作结果"""
    
    def __init__(self, operation_id: str, total_count: int):
        self.operation_id = operation_id
        self.total_count = total_count
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.status = BatchOperationStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.success_items = []
        self.failed_items = []
        self.skipped_items = []
        self.error_summary = {}
    
    def add_success(self, requirement_id: int, requirement_code: str, old_status: str, new_status: str):
        """添加成功项"""
        self.success_items.append({
            'requirement_id': requirement_id,
            'requirement_code': requirement_code,
            'old_status': old_status,
            'new_status': new_status,
            'processed_at': datetime.utcnow().isoformat()
        })
        self.success_count += 1
        self.processed_count += 1
    
    def add_failed(self, requirement_id: int, requirement_code: str, error: str):
        """添加失败项"""
        self.failed_items.append({
            'requirement_id': requirement_id,
            'requirement_code': requirement_code,
            'error': error,
            'processed_at': datetime.utcnow().isoformat()
        })
        self.failed_count += 1
        self.processed_count += 1
        
        # 统计错误类型
        if error not in self.error_summary:
            self.error_summary[error] = 0
        self.error_summary[error] += 1
    
    def add_skipped(self, requirement_id: int, requirement_code: str, reason: str):
        """添加跳过项"""
        self.skipped_items.append({
            'requirement_id': requirement_id,
            'requirement_code': requirement_code,
            'reason': reason,
            'processed_at': datetime.utcnow().isoformat()
        })
        self.skipped_count += 1
        self.processed_count += 1
    
    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_count == 0:
            return 100.0
        return (self.processed_count / self.total_count) * 100
    
    def is_completed(self) -> bool:
        """检查是否完成"""
        return self.processed_count >= self.total_count
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'operation_id': self.operation_id,
            'status': self.status.value,
            'total_count': self.total_count,
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'progress_percentage': self.get_progress_percentage(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'success_items': self.success_items,
            'failed_items': self.failed_items,
            'skipped_items': self.skipped_items,
            'error_summary': self.error_summary
        }


class RequirementBatchStatusService:
    """需求批量状态管理服务"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.validator = RequirementStatusValidator(db_session)
        self.action_manager = RequirementStatusActionManager(db_session)
        self.notification_service = RequirementNotificationService(db_session)
        self.active_operations = {}  # 存储活跃的批量操作
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def batch_update_status(
        self, 
        requirement_ids: List[int], 
        new_status: RequirementStatus, 
        user_id: int,
        reason: str = None,
        force_update: bool = False,
        validate_before_execute: bool = True
    ) -> BatchOperationResult:
        """
        批量更新需求状态
        
        Args:
            requirement_ids: 需求ID列表
            new_status: 目标状态
            user_id: 操作用户ID
            reason: 变更原因
            force_update: 是否强制更新（跳过某些验证）
            validate_before_execute: 是否在执行前进行验证
            
        Returns:
            BatchOperationResult: 批量操作结果
        """
        # 生成操作ID
        operation_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{user_id}"
        
        # 创建操作结果对象
        result = BatchOperationResult(operation_id, len(requirement_ids))
        result.status = BatchOperationStatus.PENDING
        self.active_operations[operation_id] = result
        
        try:
            # 获取需求列表
            requirements = self.db.query(Requirement).filter(
                Requirement.id.in_(requirement_ids)
            ).all()
            
            if len(requirements) != len(requirement_ids):
                found_ids = {req.id for req in requirements}
                missing_ids = set(requirement_ids) - found_ids
                for missing_id in missing_ids:
                    result.add_failed(missing_id, f"REQ-{missing_id}", "需求不存在")
            
            # 预验证阶段
            if validate_before_execute:
                validation_results = await self._validate_batch_operation(
                    requirements, new_status, user_id, force_update
                )
                
                # 处理验证失败的需求
                for req_id, validation_result in validation_results.items():
                    if not validation_result.is_valid:
                        requirement = next((r for r in requirements if r.id == req_id), None)
                        if requirement:
                            error_msg = "; ".join(validation_result.error_messages)
                            result.add_failed(req_id, requirement.requirement_code, error_msg)
                
                # 过滤出可以处理的需求
                valid_requirements = [
                    req for req in requirements 
                    if req.id in validation_results and validation_results[req.id].is_valid
                ]
            else:
                valid_requirements = requirements
            
            # 开始批量处理
            result.status = BatchOperationStatus.RUNNING
            result.start_time = datetime.utcnow()
            
            # 分批处理以避免数据库锁定
            batch_size = 10
            for i in range(0, len(valid_requirements), batch_size):
                batch = valid_requirements[i:i + batch_size]
                await self._process_requirement_batch(batch, new_status, user_id, reason, result)
                
                # 提交当前批次的更改
                self.db.commit()
            
            # 完成操作
            result.status = BatchOperationStatus.COMPLETED
            result.end_time = datetime.utcnow()
            
        except Exception as e:
            result.status = BatchOperationStatus.FAILED
            result.end_time = datetime.utcnow()
            # 将未处理的需求标记为失败
            for req in requirements:
                if req.id not in [item['requirement_id'] for item in result.success_items + result.failed_items + result.skipped_items]:
                    result.add_failed(req.id, req.requirement_code, f"批量操作异常: {str(e)}")
            
            self.db.rollback()
            raise
        
        return result
    
    async def _validate_batch_operation(
        self, 
        requirements: List[Requirement], 
        new_status: RequirementStatus, 
        user_id: int,
        force_update: bool = False
    ) -> Dict[int, PreconditionCheckResult]:
        """验证批量操作"""
        validation_results = {}
        
        for requirement in requirements:
            try:
                # 跳过已经是目标状态的需求
                if requirement.status == new_status:
                    result = PreconditionCheckResult(is_valid=False)
                    result.add_error(f"需求已经是 {new_status.value} 状态")
                    validation_results[requirement.id] = result
                    continue
                
                # 执行状态流转验证
                validation_result = self.validator.validate_status_transition(
                    requirement, new_status, user_id
                )
                
                # 如果强制更新，将错误转为警告
                if force_update and not validation_result.is_valid:
                    validation_result.warnings.extend(validation_result.error_messages)
                    validation_result.error_messages = []
                    validation_result.is_valid = True
                
                validation_results[requirement.id] = validation_result
                
            except Exception as e:
                result = PreconditionCheckResult(is_valid=False)
                result.add_error(f"验证异常: {str(e)}")
                validation_results[requirement.id] = result
        
        return validation_results
    
    async def _process_requirement_batch(
        self, 
        requirements: List[Requirement], 
        new_status: RequirementStatus, 
        user_id: int,
        reason: str,
        result: BatchOperationResult
    ):
        """处理需求批次"""
        for requirement in requirements:
            try:
                await self._process_single_requirement(
                    requirement, new_status, user_id, reason, result
                )
            except Exception as e:
                result.add_failed(
                    requirement.id, 
                    requirement.requirement_code, 
                    f"处理异常: {str(e)}"
                )
    
    async def _process_single_requirement(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        user_id: int,
        reason: str,
        result: BatchOperationResult
    ):
        """处理单个需求"""
        old_status = requirement.status
        
        try:
            # 更新需求状态
            requirement.status = new_status
            requirement.updated_by = user_id
            requirement.updated_at = datetime.utcnow()
            
            # 记录状态历史
            await self._record_status_history(
                requirement.id, old_status, new_status, user_id, reason
            )
            
            # 执行后置动作
            context = {'reason': reason, 'batch_operation': True}
            action_result = await self.action_manager.execute_post_actions(
                requirement, old_status, new_status, user_id, context
            )
            
            # 发送通知（批量操作时可能需要合并通知）
            await self.notification_service.send_status_change_notifications(
                requirement, old_status, new_status, user_id, context
            )
            
            result.add_success(
                requirement.id, 
                requirement.requirement_code, 
                old_status.value, 
                new_status.value
            )
            
        except Exception as e:
            result.add_failed(
                requirement.id, 
                requirement.requirement_code, 
                f"状态更新失败: {str(e)}"
            )
            # 回滚单个需求的更改
            requirement.status = old_status
    
    async def _record_status_history(
        self, 
        requirement_id: int, 
        old_status: RequirementStatus, 
        new_status: RequirementStatus, 
        user_id: int,
        reason: str
    ):
        """记录状态历史"""
        from ..models.requirement import RequirementStatusHistory
        
        history = RequirementStatusHistory(
            requirement_id=requirement_id,
            old_status=old_status,
            new_status=new_status,
            change_reason=reason,
            change_description=f"批量操作: {reason}" if reason else "批量状态变更",
            changed_by=user_id,
            changed_at=datetime.utcnow()
        )
        
        self.db.add(history)
    
    def get_operation_status(self, operation_id: str) -> Optional[BatchOperationResult]:
        """获取操作状态"""
        return self.active_operations.get(operation_id)
    
    def cancel_operation(self, operation_id: str, user_id: int) -> bool:
        """取消操作"""
        if operation_id in self.active_operations:
            result = self.active_operations[operation_id]
            if result.status == BatchOperationStatus.RUNNING:
                result.status = BatchOperationStatus.CANCELLED
                result.end_time = datetime.utcnow()
                return True
        return False
    
    def cleanup_completed_operations(self, hours: int = 24):
        """清理已完成的操作记录"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        completed_operations = [
            op_id for op_id, result in self.active_operations.items()
            if result.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED, BatchOperationStatus.CANCELLED]
            and result.end_time and result.end_time < cutoff_time
        ]
        
        for op_id in completed_operations:
            del self.active_operations[op_id]
    
    async def batch_validate_status_transitions(
        self, 
        requirement_ids: List[int], 
        new_status: RequirementStatus, 
        user_id: int
    ) -> Dict[int, PreconditionCheckResult]:
        """批量验证状态流转"""
        requirements = self.db.query(Requirement).filter(
            Requirement.id.in_(requirement_ids)
        ).all()
        
        return await self._validate_batch_operation(requirements, new_status, user_id)
    
    async def get_batch_operation_preview(
        self, 
        requirement_ids: List[int], 
        new_status: RequirementStatus, 
        user_id: int
    ) -> Dict[str, Any]:
        """获取批量操作预览"""
        requirements = self.db.query(Requirement).filter(
            Requirement.id.in_(requirement_ids)
        ).all()
        
        validation_results = await self._validate_batch_operation(
            requirements, new_status, user_id
        )
        
        valid_count = sum(1 for result in validation_results.values() if result.is_valid)
        invalid_count = len(validation_results) - valid_count
        
        # 统计当前状态分布
        status_distribution = {}
        for req in requirements:
            status = req.status.value
            if status not in status_distribution:
                status_distribution[status] = 0
            status_distribution[status] += 1
        
        # 统计错误类型
        error_types = {}
        for result in validation_results.values():
            for error in result.error_messages:
                if error not in error_types:
                    error_types[error] = 0
                error_types[error] += 1
        
        return {
            'total_count': len(requirements),
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'target_status': new_status.value,
            'current_status_distribution': status_distribution,
            'validation_errors': error_types,
            'estimated_duration_minutes': self._estimate_operation_duration(len(requirements)),
            'requirements_preview': [
                {
                    'id': req.id,
                    'code': req.requirement_code,
                    'title': req.title,
                    'current_status': req.status.value,
                    'is_valid': validation_results.get(req.id, PreconditionCheckResult(False)).is_valid,
                    'errors': validation_results.get(req.id, PreconditionCheckResult(False)).error_messages
                }
                for req in requirements[:10]  # 只返回前10个作为预览
            ]
        }
    
    def _estimate_operation_duration(self, requirement_count: int) -> int:
        """估算操作持续时间（分钟）"""
        # 基于需求数量估算，每个需求大约需要2-5秒
        base_seconds = requirement_count * 3
        # 加上数据库操作和通知发送的开销
        total_seconds = base_seconds + (requirement_count * 0.5)
        return max(1, int(total_seconds / 60))
    
    def get_active_operations_summary(self) -> List[Dict[str, Any]]:
        """获取活跃操作摘要"""
        return [
            {
                'operation_id': op_id,
                'status': result.status.value,
                'progress_percentage': result.get_progress_percentage(),
                'total_count': result.total_count,
                'processed_count': result.processed_count,
                'start_time': result.start_time.isoformat() if result.start_time else None
            }
            for op_id, result in self.active_operations.items()
        ]