-- =====================================================
-- AI自动化测试管理系统 - 配置管理模块表结构脚本
-- 版本: 1.0
-- 创建时间: 2024-12-19
-- 说明: 配置管理相关的表结构定义
-- =====================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 配置分组表 (sys_config_group)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_config_group` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `group_name` varchar(100) NOT NULL COMMENT '分组名称',
  `group_code` varchar(100) NOT NULL COMMENT '分组代码',
  `parent_id` bigint(20) DEFAULT 0 COMMENT '父分组ID',
  `level` int(11) DEFAULT 1 COMMENT '分组层级',
  `path` varchar(500) DEFAULT NULL COMMENT '分组路径',
  `sort_order` int(11) DEFAULT 0 COMMENT '排序序号',
  `description` text COMMENT '分组描述',
  `icon` varchar(100) DEFAULT NULL COMMENT '分组图标',
  `color` varchar(20) DEFAULT NULL COMMENT '分组颜色',
  `is_system` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否系统分组',
  `is_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_code` (`group_code`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_level` (`level`),
  KEY `idx_sort_order` (`sort_order`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配置分组表';

-- =====================================================
-- 2. 系统配置表 (sys_config)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_config` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `config_key` varchar(200) NOT NULL COMMENT '配置键名',
  `config_value` text COMMENT '配置值',
  `config_type` enum('STRING','INTEGER','BOOLEAN','JSON','PASSWORD','URL') NOT NULL DEFAULT 'STRING' COMMENT '配置类型',
  `group_id` bigint(20) DEFAULT NULL COMMENT '分组ID',
  `environment` enum('dev','test','prod') NOT NULL DEFAULT 'prod' COMMENT '环境标识',
  `description` text COMMENT '配置描述',
  `default_value` text COMMENT '默认值',
  `example_value` text COMMENT '示例值',
  `validation_rule` json COMMENT '验证规则',
  `is_core` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否核心配置',
  `is_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `is_encrypted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否加密存储',
  `is_required` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否必填',
  `tags` json COMMENT '配置标签',
  `sort_order` int(11) DEFAULT 0 COMMENT '排序序号',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key_env` (`config_key`, `environment`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_environment` (`environment`),
  KEY `idx_config_type` (`config_type`),
  KEY `idx_is_core` (`is_core`),
  KEY `idx_is_enabled` (`is_enabled`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_sort_order` (`sort_order`),
  CONSTRAINT `fk_sys_config_group` FOREIGN KEY (`group_id`) REFERENCES `sys_config_group` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- =====================================================
-- 3. 配置变更历史表 (sys_config_history)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_config_history` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `config_id` bigint(20) NOT NULL COMMENT '配置ID',
  `config_key` varchar(200) NOT NULL COMMENT '配置键名',
  `environment` enum('dev','test','prod') NOT NULL COMMENT '环境标识',
  `old_value` text COMMENT '变更前值',
  `new_value` text COMMENT '变更后值',
  `change_type` enum('CREATE','UPDATE','DELETE','ROLLBACK') NOT NULL COMMENT '变更类型',
  `change_reason` text COMMENT '变更原因',
  `change_summary` varchar(500) COMMENT '变更摘要',
  `impact_scope` json COMMENT '影响范围',
  `operator_id` bigint(20) DEFAULT NULL COMMENT '操作人ID',
  `operator_ip` varchar(45) COMMENT '操作IP',
  `user_agent` text COMMENT '用户代理',
  `audit_id` bigint(20) DEFAULT NULL COMMENT '关联审核ID',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  PRIMARY KEY (`id`),
  KEY `idx_config_id` (`config_id`),
  KEY `idx_config_key` (`config_key`),
  KEY `idx_environment` (`environment`),
  KEY `idx_change_type` (`change_type`),
  KEY `idx_operator_id` (`operator_id`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_sys_config_history_config` FOREIGN KEY (`config_id`) REFERENCES `sys_config` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配置变更历史表';

-- =====================================================
-- 4. 配置审核表 (sys_config_audit)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_config_audit` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `audit_code` varchar(50) NOT NULL COMMENT '审核编号',
  `config_id` bigint(20) DEFAULT NULL COMMENT '配置ID',
  `config_key` varchar(200) NOT NULL COMMENT '配置键名',
  `environment` enum('dev','test','prod') NOT NULL COMMENT '环境标识',
  `old_value` text COMMENT '变更前值',
  `new_value` text COMMENT '变更后值',
  `change_type` enum('CREATE','UPDATE','DELETE') NOT NULL COMMENT '变更类型',
  `audit_status` enum('PENDING','IN_REVIEW','APPROVED','REJECTED','CANCELLED') DEFAULT 'PENDING' COMMENT '审核状态',
  `priority` enum('LOW','MEDIUM','HIGH','URGENT') DEFAULT 'MEDIUM' COMMENT '优先级',
  `apply_user_id` bigint(20) NOT NULL COMMENT '申请人ID',
  `audit_user_id` bigint(20) DEFAULT NULL COMMENT '审核人ID',
  `apply_reason` text COMMENT '申请原因',
  `audit_reason` text COMMENT '审核意见',
  `impact_assessment` json COMMENT '影响评估',
  `risk_level` enum('LOW','MEDIUM','HIGH','CRITICAL') COMMENT '风险等级',
  `estimated_downtime` int(11) COMMENT '预估停机时间(分钟)',
  `rollback_plan` text COMMENT '回滚计划',
  `applied_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '申请时间',
  `audited_at` datetime DEFAULT NULL COMMENT '审核时间',
  `executed_at` datetime DEFAULT NULL COMMENT '执行时间',
  `expires_at` datetime DEFAULT NULL COMMENT '过期时间',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_audit_code` (`audit_code`),
  KEY `idx_config_id` (`config_id`),
  KEY `idx_config_key` (`config_key`),
  KEY `idx_environment` (`environment`),
  KEY `idx_audit_status` (`audit_status`),
  KEY `idx_apply_user_id` (`apply_user_id`),
  KEY `idx_audit_user_id` (`audit_user_id`),
  KEY `idx_applied_at` (`applied_at`),
  CONSTRAINT `fk_sys_config_audit_config` FOREIGN KEY (`config_id`) REFERENCES `sys_config` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配置审核表';

-- =====================================================
-- 5. 环境管理表 (sys_environment)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_environment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `env_name` varchar(100) NOT NULL COMMENT '环境名称',
  `env_code` enum('dev','test','prod') NOT NULL COMMENT '环境代码',
  `description` text COMMENT '环境描述',
  `base_url` varchar(500) COMMENT '环境基础URL',
  `config_data` json COMMENT '环境配置数据',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否激活',
  `is_default` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否默认环境',
  `sort_order` int(11) DEFAULT 0 COMMENT '排序序号',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_env_code` (`env_code`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='环境管理表';

-- =====================================================
-- 6. 配置权限表 (sys_config_permission)
-- =====================================================
CREATE TABLE IF NOT EXISTS `sys_config_permission` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `permission_type` enum('CONFIG','GROUP','ENVIRONMENT','GLOBAL') NOT NULL COMMENT '权限类型',
  `config_id` bigint(20) DEFAULT NULL COMMENT '配置ID',
  `group_id` bigint(20) DEFAULT NULL COMMENT '分组ID',
  `environment` enum('dev','test','prod') DEFAULT NULL COMMENT '环境标识',
  `actions` json NOT NULL COMMENT '允许的操作列表',
  `granted_by` bigint(20) DEFAULT NULL COMMENT '授权人ID',
  `granted_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '授权时间',
  `expires_at` datetime DEFAULT NULL COMMENT '过期时间',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_permission_type` (`permission_type`),
  KEY `idx_config_id` (`config_id`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_environment` (`environment`),
  KEY `idx_granted_by` (`granted_by`),
  KEY `idx_expires_at` (`expires_at`),
  CONSTRAINT `fk_sys_config_permission_config` FOREIGN KEY (`config_id`) REFERENCES `sys_config` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_sys_config_permission_group` FOREIGN KEY (`group_id`) REFERENCES `sys_config_group` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配置权限表';

-- =====================================================
-- 索引优化
-- =====================================================

-- 为高频查询字段添加组合索引
ALTER TABLE `sys_config` ADD INDEX `idx_key_env_enabled` (`config_key`, `environment`, `is_enabled`);
ALTER TABLE `sys_config` ADD INDEX `idx_group_env_enabled` (`group_id`, `environment`, `is_enabled`);
ALTER TABLE `sys_config` ADD INDEX `idx_type_env_enabled` (`config_type`, `environment`, `is_enabled`);

-- 为历史查询添加索引
ALTER TABLE `sys_config_history` ADD INDEX `idx_config_operator_time` (`config_id`, `operator_id`, `created_at`);
ALTER TABLE `sys_config_history` ADD INDEX `idx_key_env_time` (`config_key`, `environment`, `created_at`);

-- 为审核查询添加索引
ALTER TABLE `sys_config_audit` ADD INDEX `idx_status_priority_time` (`audit_status`, `priority`, `applied_at`);
ALTER TABLE `sys_config_audit` ADD INDEX `idx_apply_user_time` (`apply_user_id`, `applied_at`);

-- 为权限查询添加索引
ALTER TABLE `sys_config_permission` ADD INDEX `idx_user_type_env` (`user_id`, `permission_type`, `environment`);
ALTER TABLE `sys_config_permission` ADD INDEX `idx_expires_check` (`expires_at`, `deleted_at`);

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;