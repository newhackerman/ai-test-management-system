import csv
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_session
from ..models.ai_operation_log import AIOperationPriority, AIOperationResult, AIOperationType
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _managed_async_session():
    async for session in get_async_session():
        yield session
        break


def _json_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def _enum_name(value: Any) -> str:
    return value.name if hasattr(value, "name") else str(value)


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _status_value(result: AIOperationResult) -> str:
    mapping = {
        AIOperationResult.SUCCESS: "SUCCESS",
        AIOperationResult.FAILURE: "FAILED",
        AIOperationResult.PARTIAL_SUCCESS: "SUCCESS",
        AIOperationResult.CANCELLED: "CANCELLED",
        AIOperationResult.TIMEOUT: "TIMEOUT",
    }
    return mapping.get(result, "SUCCESS")


class AIOperationLogService:
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.redis_client = None
        self._log_buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100
        self._flush_interval = 30
        self._last_flush = datetime.utcnow()

    async def initialize(self):
        try:
            self.redis_client = await get_redis_client()
            logger.info("AI operation log service initialized")
        except Exception as exc:
            logger.warning("Redis unavailable for AI operation logs: %s", exc)

    def _to_db_row(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        result = log_data.get("result", AIOperationResult.SUCCESS)
        operation_data = {
            "priority": _enum_value(log_data.get("priority", AIOperationPriority.MEDIUM)),
            "category": log_data.get("category"),
            "subcategory": log_data.get("subcategory"),
            "resource_type": log_data.get("resource_type"),
            "resource_id": log_data.get("resource_id"),
            "resource_name": log_data.get("resource_name"),
            "confidence_score": log_data.get("confidence_score"),
            "business_context": log_data.get("business_context"),
            "metadata": log_data.get("operation_metadata") or log_data.get("metadata"),
            "tags": log_data.get("tags"),
            "correlation_id": log_data.get("correlation_id"),
            "trace_id": log_data.get("trace_id"),
        }
        error_data = {
            "error_code": log_data.get("error_code"),
            "error_details": log_data.get("error_details"),
            "result_message": log_data.get("result_message"),
        }
        user_id = log_data.get("user_id")
        return {
            "user_id": int(user_id) if user_id is not None else 0,
            "session_id": int(log_data["session_id"]) if str(log_data.get("session_id") or "").isdigit() else None,
            "operation_type": _enum_name(log_data.get("operation_type")),
            "operation_name": log_data.get("operation_name") or "ai_operation",
            "target_type": log_data.get("resource_type"),
            "target_id": int(log_data["resource_id"]) if str(log_data.get("resource_id") or "").isdigit() else None,
            "operation_data": _json_value(operation_data),
            "request_data": _json_value(
                {
                    "headers": log_data.get("request_headers"),
                    "params": log_data.get("request_params"),
                }
            ),
            "response_data": _json_value(log_data.get("response_data")),
            "error_data": _json_value(error_data),
            "status": _status_value(result),
            "error_code": log_data.get("error_code"),
            "error_message": log_data.get("error_details") or log_data.get("result_message"),
            "execution_time": log_data.get("processing_time"),
            "ai_provider": log_data.get("ai_provider"),
            "ai_model": log_data.get("ai_model"),
            "tokens_used": log_data.get("tokens_used") or 0,
            "cost": log_data.get("cost_amount") or 0,
            "ip_address": log_data.get("request_ip"),
            "user_agent": log_data.get("user_agent"),
            "client_info": _json_value({"is_sensitive": log_data.get("is_sensitive", False)}),
        }

    async def log_operation(
        self,
        operation_type: AIOperationType,
        operation_name: str,
        result: AIOperationResult,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> Optional[int]:
        try:
            kwargs.setdefault("trace_id", str(uuid.uuid4()))
            log_data = {
                "operation_type": operation_type,
                "operation_name": operation_name,
                "result": result,
                "user_id": user_id,
                "session_id": session_id,
                **kwargs,
            }
            if (
                kwargs.get("priority") == AIOperationPriority.CRITICAL
                or kwargs.get("is_sensitive", False)
                or result == AIOperationResult.FAILURE
            ):
                return await self._write_log_immediately(log_data)
            await self._add_to_buffer(log_data)
            await self._check_and_flush_buffer()
            return None
        except Exception as exc:
            logger.error("Failed to log AI operation: %s", exc)
            return None

    async def _write_log_immediately(self, log_data: Dict[str, Any]) -> Optional[int]:
        try:
            if self.db:
                return await self._insert_log(self.db, log_data)
            async with _managed_async_session() as db:
                return await self._insert_log(db, log_data)
        except Exception as exc:
            logger.error("Failed to write AI operation log immediately: %s", exc)
            return None

    async def _insert_log(self, db: AsyncSession, log_data: Dict[str, Any]) -> int:
        row = self._to_db_row(log_data)
        result = await db.execute(
            text(
                """
                INSERT INTO ai_operation_logs (
                    user_id, session_id, operation_type, operation_name,
                    target_type, target_id, operation_data, request_data,
                    response_data, error_data, status, error_code, error_message,
                    execution_time, ai_provider, ai_model, tokens_used, cost,
                    ip_address, user_agent, client_info
                ) VALUES (
                    :user_id, :session_id, :operation_type, :operation_name,
                    :target_type, :target_id, :operation_data, :request_data,
                    :response_data, :error_data, :status, :error_code, :error_message,
                    :execution_time, :ai_provider, :ai_model, :tokens_used, :cost,
                    :ip_address, :user_agent, :client_info
                )
                """
            ),
            row,
        )
        await db.commit()
        return int(getattr(result, "lastrowid", 0) or 0)

    async def _add_to_buffer(self, log_data: Dict[str, Any]):
        self._log_buffer.append(log_data)
        if len(self._log_buffer) >= self._buffer_size:
            await self._flush_buffer()

    async def _check_and_flush_buffer(self):
        if (datetime.utcnow() - self._last_flush).total_seconds() >= self._flush_interval:
            await self._flush_buffer()

    async def _flush_buffer(self):
        if not self._log_buffer:
            return
        buffer_copy = self._log_buffer.copy()
        self._log_buffer.clear()
        self._last_flush = datetime.utcnow()
        try:
            async with _managed_async_session() as db:
                for item in buffer_copy:
                    await self._insert_log(db, item)
            logger.debug("Flushed %s AI operation logs", len(buffer_copy))
        except Exception as exc:
            logger.error("Failed to flush AI operation log buffer: %s", exc)
            self._log_buffer.extend(buffer_copy)

    async def log_ai_model_call(
        self,
        user_id: int,
        ai_provider: str,
        ai_model: str,
        tokens_used: int,
        processing_time: float,
        result: AIOperationResult,
        cost_amount: Optional[float] = None,
        confidence_score: Optional[float] = None,
        error_details: Optional[str] = None,
        **kwargs,
    ) -> Optional[int]:
        return await self.log_operation(
            operation_type=AIOperationType.AI_MODEL_CALL,
            operation_name=f"{ai_provider}_{ai_model}_call",
            result=result,
            user_id=user_id,
            ai_provider=ai_provider,
            ai_model=ai_model,
            tokens_used=tokens_used,
            processing_time=processing_time,
            cost_amount=cost_amount,
            confidence_score=confidence_score,
            error_details=error_details,
            category="ai_service",
            subcategory="model_call",
            **kwargs,
        )

    async def log_conversation_activity(self, user_id: int, conversation_id: str, activity_type: str, result: AIOperationResult, **kwargs):
        operation_type_map = {
            "create": AIOperationType.CONVERSATION_CREATE,
            "delete": AIOperationType.CONVERSATION_DELETE,
            "send_message": AIOperationType.MESSAGE_SEND,
            "receive_message": AIOperationType.MESSAGE_RECEIVE,
        }
        return await self.log_operation(
            operation_type=operation_type_map.get(activity_type, AIOperationType.MESSAGE_SEND),
            operation_name=f"conversation_{activity_type}",
            result=result,
            user_id=user_id,
            session_id=conversation_id,
            resource_type="conversation",
            resource_id=conversation_id,
            category="conversation",
            subcategory=activity_type,
            **kwargs,
        )

    async def log_suggestion_activity(self, user_id: int, suggestion_id: str, activity_type: str, result: AIOperationResult, **kwargs):
        operation_type_map = {
            "generate": AIOperationType.SUGGESTION_GENERATE,
            "accept": AIOperationType.SUGGESTION_ACCEPT,
            "reject": AIOperationType.SUGGESTION_REJECT,
            "implement": AIOperationType.SUGGESTION_IMPLEMENT,
        }
        return await self.log_operation(
            operation_type=operation_type_map.get(activity_type, AIOperationType.SUGGESTION_GENERATE),
            operation_name=f"suggestion_{activity_type}",
            result=result,
            user_id=user_id,
            resource_type="suggestion",
            resource_id=suggestion_id,
            category="suggestion",
            subcategory=activity_type,
            **kwargs,
        )

    async def log_security_event(self, event_type: str, severity: str, user_id: Optional[int] = None, ip_address: Optional[str] = None, details: Optional[str] = None, **kwargs):
        operation_type_map = {
            "unauthorized_access": AIOperationType.UNAUTHORIZED_ACCESS,
            "rate_limit_exceeded": AIOperationType.RATE_LIMIT_EXCEEDED,
            "suspicious_activity": AIOperationType.SUSPICIOUS_ACTIVITY,
        }
        priority_map = {
            "low": AIOperationPriority.LOW,
            "medium": AIOperationPriority.MEDIUM,
            "high": AIOperationPriority.HIGH,
            "critical": AIOperationPriority.CRITICAL,
        }
        return await self.log_operation(
            operation_type=operation_type_map.get(event_type, AIOperationType.SUSPICIOUS_ACTIVITY),
            operation_name=f"security_{event_type}",
            result=AIOperationResult.FAILURE,
            user_id=user_id,
            request_ip=ip_address,
            error_details=details,
            priority=priority_map.get(severity, AIOperationPriority.HIGH),
            category="security",
            subcategory=event_type,
            is_sensitive=True,
            **kwargs,
        )

    def _log_row_to_dict(self, row: Any) -> Dict[str, Any]:
        data = dict(row._mapping)
        operation_data = json.loads(data.pop("operation_data") or "{}")
        error_data = json.loads(data.pop("error_data") or "{}")
        data["operation_type"] = data.get("operation_type")
        data["result"] = data.pop("status", None)
        data["processing_time"] = float(data.pop("execution_time") or 0)
        data["cost_amount"] = float(data.pop("cost") or 0)
        data["request_ip"] = data.pop("ip_address", None)
        data["error_details"] = data.pop("error_message", None) or error_data.get("error_details")
        data.update({key: value for key, value in operation_data.items() if value is not None})
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat()
        return data

    async def get_operation_logs(
        self,
        user_id: Optional[int] = None,
        operation_type: Optional[AIOperationType] = None,
        result: Optional[AIOperationResult] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        try:
            where = []
            params: Dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
            if user_id:
                where.append("user_id = :user_id")
                params["user_id"] = user_id
            if operation_type:
                where.append("operation_type = :operation_type")
                params["operation_type"] = _enum_name(operation_type)
            if result:
                where.append("status = :status")
                params["status"] = _status_value(result)
            if start_date:
                where.append("created_at >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("created_at <= :end_date")
                params["end_date"] = end_date

            where_sql = f"WHERE {' AND '.join(where)}" if where else ""
            allowed_order = {
                "id", "user_id", "operation_type", "operation_name", "status",
                "ai_provider", "ai_model", "tokens_used", "execution_time", "created_at",
            }
            order_column = order_by if order_by in allowed_order else "created_at"
            direction = "DESC" if order_desc else "ASC"
            async with _managed_async_session() as db:
                total = (await db.execute(text(f"SELECT COUNT(*) FROM ai_operation_logs {where_sql}"), params)).scalar() or 0
                rows = (
                    await db.execute(
                        text(
                            f"""
                            SELECT * FROM ai_operation_logs
                            {where_sql}
                            ORDER BY {order_column} {direction}
                            LIMIT :limit OFFSET :offset
                            """
                        ),
                        params,
                    )
                ).all()
                return [self._log_row_to_dict(row) for row in rows], total
        except Exception as exc:
            logger.error("Failed to query AI operation logs: %s", exc)
            return [], 0

    async def get_operation_statistics(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "operation_type",
    ) -> Dict[str, Any]:
        try:
            where = []
            params: Dict[str, Any] = {}
            if user_id:
                where.append("user_id = :user_id")
                params["user_id"] = user_id
            if start_date:
                where.append("created_at >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("created_at <= :end_date")
                params["end_date"] = end_date
            where_sql = f"WHERE {' AND '.join(where)}" if where else ""

            if group_by == "overall":
                async with _managed_async_session() as db:
                    row = (
                        await db.execute(
                            text(
                                f"""
                                SELECT COUNT(*) total_operations,
                                       COALESCE(SUM(tokens_used), 0) total_tokens,
                                       COALESCE(SUM(cost), 0) total_cost,
                                       COALESCE(AVG(execution_time), 0) avg_processing_time
                                FROM ai_operation_logs {where_sql}
                                """
                            ),
                            params,
                        )
                    ).first()
                    return dict(row._mapping) if row else {}

            group_expr = {
                "operation_type": "operation_type",
                "result": "status",
                "ai_provider": "ai_provider",
                "date": "DATE(created_at)",
            }.get(group_by, "operation_type")
            async with _managed_async_session() as db:
                rows = (
                    await db.execute(
                        text(
                            f"""
                            SELECT {group_expr} group_key,
                                   COUNT(*) count,
                                   COALESCE(SUM(tokens_used), 0) total_tokens,
                                   COALESCE(SUM(cost), 0) total_cost,
                                   COALESCE(AVG(execution_time), 0) avg_processing_time
                            FROM ai_operation_logs
                            {where_sql}
                            GROUP BY {group_expr}
                            """
                        ),
                        params,
                    )
                ).all()
                return {
                    "group_by": group_by,
                    "statistics": {
                        str(row._mapping["group_key"] or "unknown"): {
                            "count": row._mapping["count"],
                            "total_tokens": row._mapping["total_tokens"],
                            "total_cost": float(row._mapping["total_cost"] or 0),
                            "avg_processing_time": float(row._mapping["avg_processing_time"] or 0),
                        }
                        for row in rows
                    },
                }
        except Exception as exc:
            logger.error("Failed to calculate AI operation statistics: %s", exc)
            return {}

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            async with _managed_async_session() as db:
                count = (
                    await db.execute(
                        text("SELECT COUNT(*) FROM ai_operation_logs WHERE created_at < :cutoff_date"),
                        {"cutoff_date": cutoff_date},
                    )
                ).scalar() or 0
                await db.execute(text("DELETE FROM ai_operation_logs WHERE created_at < :cutoff_date"), {"cutoff_date": cutoff_date})
                await db.commit()
                return count
        except Exception as exc:
            logger.error("Failed to cleanup AI operation logs: %s", exc)
            return 0

    async def generate_daily_summary(self, target_date: Optional[datetime] = None) -> bool:
        return True

    async def export_logs(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        operation_type: Optional[AIOperationType] = None,
        format_type: str = "json",
    ) -> Optional[str]:
        logs, _ = await self.get_operation_logs(
            user_id=user_id,
            operation_type=operation_type,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=10000,
        )
        if not logs:
            return None
        if format_type == "csv":
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=list(logs[0].keys()))
            writer.writeheader()
            writer.writerows(logs)
            return output.getvalue()
        return json.dumps(logs, ensure_ascii=False, default=str, indent=2)


_log_service_instance: Optional[AIOperationLogService] = None


async def get_ai_operation_log_service(db: AsyncSession = None) -> AIOperationLogService:
    global _log_service_instance
    if db is not None:
        service = AIOperationLogService(db)
        await service.initialize()
        return service
    if _log_service_instance is None:
        _log_service_instance = AIOperationLogService()
        await _log_service_instance.initialize()
    return _log_service_instance
