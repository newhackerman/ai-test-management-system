-- 通知功能增强：逻辑删除
-- 为 system_notifications 表增加 is_deleted / deleted_at 字段
ALTER TABLE system_notifications ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL COMMENT '是否逻辑删除';
ALTER TABLE system_notifications ADD COLUMN deleted_at DATETIME NULL COMMENT '删除时间';
