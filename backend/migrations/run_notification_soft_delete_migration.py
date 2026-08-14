#!/usr/bin/env python3
"""
通知逻辑删除 - 数据库迁移执行脚本
为 system_notifications 表增加 is_deleted / deleted_at 字段，支持重复执行（幂等）。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import engine
from sqlalchemy import text

STATEMENTS = [
    "ALTER TABLE system_notifications ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL COMMENT '是否逻辑删除'",
    "ALTER TABLE system_notifications ADD COLUMN deleted_at DATETIME NULL COMMENT '删除时间'",
    "CREATE INDEX idx_system_notifications_is_deleted ON system_notifications (is_deleted)",
]


def run_migration():
    with engine.connect() as conn:
        for statement in STATEMENTS:
            try:
                conn.execute(text(statement))
                conn.commit()
                print(f"[OK] {statement}")
            except Exception as exc:  # noqa: BLE001
                message = str(exc)
                if "1060" in message or "Duplicate column" in message or "1061" in message or "Duplicate key" in message or "already exists" in message.lower():
                    print(f"[SKIP] 已存在，跳过: {statement}")
                else:
                    print(f"[FAIL] {statement} -> {message}")
                    return False
    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
