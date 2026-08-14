-- P0-2: 数据库Schema修复
-- 添加缺失的列

-- 1. 添加 roles.color 列 (如果不存在)
ALTER TABLE roles ADD COLUMN IF NOT EXISTS color VARCHAR(20) DEFAULT NULL COMMENT '显示颜色';

-- 2. 添加 role_permissions.effect 列 (如果不存在)
ALTER TABLE role_permissions ADD COLUMN IF NOT EXISTS effect VARCHAR(10) DEFAULT 'allow' COMMENT '权限效果';