-- 仪表板管理模块数据库迁移脚本
-- 创建仪表板管理相关的数据库表结构

-- 设置字符集和排序规则
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 仪表板配置表 (dashboard_configs)
-- =====================================================
CREATE TABLE IF NOT EXISTS `dashboard_configs` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `role_type` ENUM('ADMIN','PROJECT_MANAGER','REQUIREMENT_MANAGER','DESIGNER','ARCHITECT','DEVELOPER','TESTER','DEVOPS','THIRD_PARTY') NOT NULL COMMENT '角色类型',
    `dashboard_name` VARCHAR(100) NOT NULL COMMENT '仪表板名称',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认配置',
    `layout_config` JSON COMMENT '布局配置JSON',
    `widget_configs` JSON COMMENT '组件配置列表JSON',
    `theme_config` JSON COMMENT '主题配置JSON',
    `refresh_interval` INT DEFAULT 30 COMMENT '刷新间隔(秒)',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    CONSTRAINT `fk_dashboard_configs_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    
    -- 索引
    INDEX `idx_user_role` (`user_id`, `role_type`),
    INDEX `idx_role_type` (`role_type`),
    INDEX `idx_is_default` (`is_default`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仪表板配置表';

-- =====================================================
-- 2. 组件定义表 (widget_definitions)
-- =====================================================
CREATE TABLE IF NOT EXISTS `widget_definitions` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '组件定义ID',
    `widget_type` VARCHAR(50) NOT NULL UNIQUE COMMENT '组件类型',
    `widget_name` VARCHAR(100) NOT NULL COMMENT '组件名称',
    `description` TEXT COMMENT '组件描述',
    `category` ENUM('STATISTICS','CHARTS','PROGRESS','STATUS','RANKING','CALENDAR','MAP','TABLE','MONITORING','NOTIFICATION') NOT NULL COMMENT '组件分类',
    `default_config` JSON COMMENT '默认配置JSON',
    `data_source_config` JSON COMMENT '数据源配置JSON',
    `supported_roles` JSON COMMENT '支持的角色列表JSON',
    `min_width` INT DEFAULT 2 COMMENT '最小宽度',
    `min_height` INT DEFAULT 2 COMMENT '最小高度',
    `max_width` INT DEFAULT 12 COMMENT '最大宽度',
    `max_height` INT DEFAULT 12 COMMENT '最大高度',
    `permission_required` VARCHAR(100) COMMENT '所需权限',
    `is_premium` TINYINT(1) DEFAULT 0 COMMENT '是否为高级组件',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `version` VARCHAR(20) DEFAULT '1.0.0' COMMENT '组件版本',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_widget_type` (`widget_type`),
    INDEX `idx_category` (`category`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_is_premium` (`is_premium`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组件定义表';

-- =====================================================
-- 3. 配色方案表 (color_schemes)
-- =====================================================
CREATE TABLE IF NOT EXISTS `color_schemes` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配色方案ID',
    `scheme_name` VARCHAR(100) NOT NULL COMMENT '方案名称',
    `scheme_type` ENUM('SYSTEM','ENTERPRISE','USER_CUSTOM') NOT NULL COMMENT '方案类型',
    `scheme_category` ENUM('BUSINESS','TECHNOLOGY','FRESH','WARM','COOL','DARK','LIGHT','COLORFUL','MONOCHROME') COMMENT '方案分类',
    `color_palette` JSON NOT NULL COMMENT '颜色数组JSON',
    `description` TEXT COMMENT '方案描述',
    `preview_image` VARCHAR(500) COMMENT '预览图片路径',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认方案',
    `is_public` TINYINT(1) DEFAULT 0 COMMENT '是否公开方案',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `created_by` BIGINT COMMENT '创建者ID',
    `organization_id` BIGINT COMMENT '组织ID（企业方案）',
    `usage_count` INT DEFAULT 0 COMMENT '使用次数',
    `rating` DECIMAL(3,2) DEFAULT 0.00 COMMENT '用户评分',
    `accessibility_compliant` TINYINT(1) DEFAULT 0 COMMENT '是否符合可访问性标准',
    `contrast_ratio` DECIMAL(4,2) COMMENT '对比度比值',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    CONSTRAINT `fk_color_schemes_creator` FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON DELETE SET NULL,
    
    -- 索引
    INDEX `idx_scheme_type` (`scheme_type`),
    INDEX `idx_scheme_category` (`scheme_category`),
    INDEX `idx_is_default` (`is_default`),
    INDEX `idx_is_public` (`is_public`),
    INDEX `idx_created_by` (`created_by`),
    INDEX `idx_organization_id` (`organization_id`),
    INDEX `idx_usage_count` (`usage_count`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配色方案表';

-- =====================================================
-- 4. 用户配色偏好表 (user_color_preferences)
-- =====================================================
CREATE TABLE IF NOT EXISTS `user_color_preferences` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '偏好ID',
    `user_id` BIGINT NOT NULL UNIQUE COMMENT '用户ID',
    `color_scheme_id` BIGINT COMMENT '选择的配色方案ID',
    `custom_colors` JSON COMMENT '用户自定义颜色JSON',
    `auto_switch_dark_mode` TINYINT(1) DEFAULT 0 COMMENT '是否自动切换暗色模式',
    `accessibility_mode` TINYINT(1) DEFAULT 0 COMMENT '是否启用无障碍模式',
    `high_contrast` TINYINT(1) DEFAULT 0 COMMENT '是否启用高对比度',
    `apply_to_charts` TINYINT(1) DEFAULT 1 COMMENT '是否应用到图表',
    `apply_to_widgets` TINYINT(1) DEFAULT 1 COMMENT '是否应用到组件',
    `apply_to_theme` TINYINT(1) DEFAULT 0 COMMENT '是否应用到整体主题',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    CONSTRAINT `fk_user_color_preferences_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_color_preferences_scheme` FOREIGN KEY (`color_scheme_id`) REFERENCES `color_schemes`(`id`) ON DELETE SET NULL,
    
    -- 索引
    INDEX `idx_color_scheme_id` (`color_scheme_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户配色偏好表';

-- =====================================================
-- 5. 仪表板数据缓存表 (dashboard_data_cache)
-- =====================================================
CREATE TABLE IF NOT EXISTS `dashboard_data_cache` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '缓存ID',
    `cache_key` VARCHAR(255) NOT NULL UNIQUE COMMENT '缓存键',
    `data_type` ENUM('PROJECT_OVERVIEW','REQUIREMENT_METRICS','TEST_METRICS','SYSTEM_METRICS','USER_STATISTICS','PERFORMANCE_DATA','CHART_DATA','WIDGET_DATA','AGGREGATED_DATA') NOT NULL COMMENT '数据类型',
    `data_content` JSON NOT NULL COMMENT '数据内容JSON',
    `data_size` INT COMMENT '数据大小(字节)',
    `data_hash` VARCHAR(64) COMMENT '数据哈希值',
    `project_id` BIGINT COMMENT '关联项目ID',
    `user_id` BIGINT COMMENT '关联用户ID',
    `widget_type` VARCHAR(50) COMMENT '组件类型',
    `ttl_seconds` INT DEFAULT 300 COMMENT '生存时间(秒)',
    `expires_at` TIMESTAMP NOT NULL COMMENT '过期时间',
    `refresh_interval` INT DEFAULT 60 COMMENT '刷新间隔(秒)',
    `status` ENUM('ACTIVE','EXPIRED','INVALIDATED','REFRESHING') DEFAULT 'ACTIVE' COMMENT '缓存状态',
    `hit_count` INT DEFAULT 0 COMMENT '命中次数',
    `last_hit_at` TIMESTAMP COMMENT '最后命中时间',
    `generation_time_ms` FLOAT COMMENT '生成时间(毫秒)',
    `compression_ratio` FLOAT COMMENT '压缩比率',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    CONSTRAINT `fk_dashboard_cache_project` FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dashboard_cache_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    
    -- 索引
    INDEX `idx_cache_key` (`cache_key`),
    INDEX `idx_data_type` (`data_type`),
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_widget_type` (`widget_type`),
    INDEX `idx_expires_at` (`expires_at`),
    INDEX `idx_status` (`status`),
    INDEX `idx_project_user` (`project_id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仪表板数据缓存表';

-- =====================================================
-- 6. 缓存清理策略表 (cache_cleanup_policies)
-- =====================================================
CREATE TABLE IF NOT EXISTS `cache_cleanup_policies` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '策略ID',
    `data_type` ENUM('PROJECT_OVERVIEW','REQUIREMENT_METRICS','TEST_METRICS','SYSTEM_METRICS','USER_STATISTICS','PERFORMANCE_DATA','CHART_DATA','WIDGET_DATA','AGGREGATED_DATA') NOT NULL UNIQUE COMMENT '数据类型',
    `policy_name` VARCHAR(100) NOT NULL COMMENT '策略名称',
    `max_entries` INT DEFAULT 1000 COMMENT '最大条目数',
    `max_age_hours` INT DEFAULT 24 COMMENT '最大存活时间(小时)',
    `max_size_mb` INT DEFAULT 100 COMMENT '最大大小(MB)',
    `cleanup_on_hit_count` INT COMMENT '基于命中次数清理',
    `cleanup_on_last_access` INT COMMENT '基于最后访问时间清理(小时)',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `priority` INT DEFAULT 0 COMMENT '优先级',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_data_type` (`data_type`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_priority` (`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='缓存清理策略表';

-- =====================================================
-- 7. WebSocket连接管理表 (websocket_connections)
-- =====================================================
CREATE TABLE IF NOT EXISTS `websocket_connections` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '连接ID',
    `connection_id` VARCHAR(255) NOT NULL UNIQUE COMMENT '连接标识',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `role_type` ENUM('ADMIN','PROJECT_MANAGER','REQUIREMENT_MANAGER','DESIGNER','ARCHITECT','DEVELOPER','TESTER','DEVOPS','THIRD_PARTY') NOT NULL COMMENT '角色类型',
    `session_id` VARCHAR(255) COMMENT '会话ID',
    `client_ip` VARCHAR(45) COMMENT '客户端IP',
    `user_agent` TEXT COMMENT '用户代理',
    `project_ids` JSON COMMENT '订阅的项目ID列表',
    `subscribed_events` JSON COMMENT '订阅的事件类型',
    `widget_subscriptions` JSON COMMENT '组件订阅信息',
    `status` ENUM('CONNECTING','CONNECTED','DISCONNECTED','RECONNECTING','ERROR','TIMEOUT') DEFAULT 'CONNECTING' COMMENT '连接状态',
    `connected_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '连接时间',
    `last_heartbeat` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最后心跳时间',
    `last_activity` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最后活动时间',
    `message_count` INT DEFAULT 0 COMMENT '消息数量',
    `bytes_sent` BIGINT DEFAULT 0 COMMENT '发送字节数',
    `bytes_received` BIGINT DEFAULT 0 COMMENT '接收字节数',
    `latency_ms` FLOAT COMMENT '延迟(毫秒)',
    `client_info` JSON COMMENT '客户端信息JSON',
    `connection_quality` FLOAT DEFAULT 1.0 COMMENT '连接质量评分',
    `disconnected_at` TIMESTAMP COMMENT '断开时间',
    `disconnect_reason` VARCHAR(255) COMMENT '断开原因',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    CONSTRAINT `fk_websocket_connections_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    
    -- 索引
    INDEX `idx_connection_id` (`connection_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_role_type` (`role_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_last_heartbeat` (`last_heartbeat`),
    INDEX `idx_connected_at` (`connected_at`),
    INDEX `idx_user_status` (`user_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='WebSocket连接管理表';

-- =====================================================
-- 8. WebSocket连接事件表 (websocket_connection_events)
-- =====================================================
CREATE TABLE IF NOT EXISTS `websocket_connection_events` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '事件ID',
    `connection_id` VARCHAR(255) NOT NULL COMMENT '连接标识',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `event_type` VARCHAR(50) NOT NULL COMMENT '事件类型',
    `event_data` JSON COMMENT '事件数据',
    `message_size` INT COMMENT '消息大小',
    `processing_time_ms` FLOAT COMMENT '处理时间(毫秒)',
    `queue_time_ms` FLOAT COMMENT '队列时间(毫秒)',
    `success` TINYINT(1) DEFAULT 1 COMMENT '是否成功',
    `error_message` TEXT COMMENT '错误信息',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    -- 索引
    INDEX `idx_connection_id` (`connection_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_event_type` (`event_type`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_success` (`success`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='WebSocket连接事件表';

-- =====================================================
-- 插入系统预设数据
-- =====================================================

-- 插入系统预设组件定义
INSERT IGNORE INTO `widget_definitions` (
    `widget_type`, `widget_name`, `description`, `category`, 
    `default_config`, `data_source_config`, `supported_roles`,
    `min_width`, `min_height`, `max_width`, `max_height`
) VALUES 
-- 统计类组件
('project_overview', '项目概览', '显示项目总体状态和关键指标', 'STATISTICS',
 '{"show_total": true, "show_active": true, "show_completed": true, "show_delayed": true}',
 '{"type": "API", "endpoint": "/api/v1/projects/overview", "refresh_interval": 300}',
 '["ADMIN", "PROJECT_MANAGER"]', 4, 2, 8, 4),

('system_overview', '系统概览', '显示系统整体运行状态', 'STATISTICS',
 '{"show_users": true, "show_projects": true, "show_tests": true, "show_performance": true}',
 '{"type": "API", "endpoint": "/api/v1/system/overview", "refresh_interval": 60}',
 '["ADMIN"]', 6, 3, 12, 6),

-- 图表类组件
('test_trend_chart', '测试趋势图', '显示测试执行和通过率趋势', 'CHARTS',
 '{"chart_type": "line", "time_range": "7d", "show_pass_rate": true, "show_execution_count": true}',
 '{"type": "API", "endpoint": "/api/v1/tests/trends", "refresh_interval": 300}',
 '["TESTER", "PROJECT_MANAGER", "ADMIN"]', 6, 4, 12, 8),

('requirement_status_chart', '需求状态图', '显示需求状态分布饼图', 'CHARTS',
 '{"chart_type": "pie", "show_labels": true, "show_percentages": true}',
 '{"type": "API", "endpoint": "/api/v1/requirements/status-distribution", "refresh_interval": 600}',
 '["REQUIREMENT_MANAGER", "PROJECT_MANAGER", "ADMIN"]', 4, 4, 8, 6),

-- 进度类组件
('milestone_progress', '里程碑进度', '显示项目里程碑完成进度', 'PROGRESS',
 '{"show_percentage": true, "show_timeline": true, "highlight_overdue": true}',
 '{"type": "API", "endpoint": "/api/v1/projects/milestones", "refresh_interval": 300}',
 '["PROJECT_MANAGER", "ADMIN"]', 6, 3, 12, 5),

-- 状态类组件
('build_status', '构建状态', '显示CI/CD构建状态', 'STATUS',
 '{"show_latest_builds": 5, "show_success_rate": true, "auto_refresh": true}',
 '{"type": "WEBSOCKET", "endpoint": "/ws/builds", "fallback_api": "/api/v1/builds/status"}',
 '["DEVELOPER", "DEVOPS", "ADMIN"]', 4, 2, 8, 4),

-- 表格类组件
('my_tasks', '我的任务', '显示当前用户的任务列表', 'TABLE',
 '{"page_size": 10, "show_priority": true, "show_due_date": true, "sortable": true}',
 '{"type": "API", "endpoint": "/api/v1/tasks/my-tasks", "refresh_interval": 180}',
 '["DEVELOPER", "TESTER", "REQUIREMENT_MANAGER", "DESIGNER"]', 6, 4, 12, 8),

-- 监控类组件
('system_performance', '系统性能', '显示系统性能指标', 'MONITORING',
 '{"show_cpu": true, "show_memory": true, "show_disk": true, "show_network": true, "alert_threshold": 80}',
 '{"type": "WEBSOCKET", "endpoint": "/ws/system-metrics", "refresh_interval": 30}',
 '["DEVOPS", "ADMIN"]', 4, 3, 8, 6);

-- 插入系统预设配色方案
INSERT IGNORE INTO `color_schemes` (
    `scheme_name`, `scheme_type`, `scheme_category`, `color_palette`, 
    `description`, `is_default`, `is_public`, `accessibility_compliant`
) VALUES 
('默认蓝色', 'SYSTEM', 'BUSINESS', 
 '["#1890FF", "#52C41A", "#FAAD14", "#F5222D", "#722ED1", "#13C2C2", "#EB2F96", "#FA8C16"]',
 '经典蓝色商务配色方案，适合大多数业务场景', 1, 1, 1),

('商务经典', 'SYSTEM', 'BUSINESS',
 '["#2F54EB", "#389E0D", "#D48806", "#CF1322", "#531DAB", "#08979C", "#C41D7F", "#D4380D"]',
 '深色商务配色，专业稳重', 0, 1, 1),

('科技蓝', 'SYSTEM', 'TECHNOLOGY',
 '["#0050B3", "#006D75", "#7CB305", "#AD4E00", "#9254DE", "#E91E63", "#FF5722", "#795548"]',
 '科技感十足的蓝色系配色', 0, 1, 0),

('清新绿', 'SYSTEM', 'FRESH',
 '["#52C41A", "#1890FF", "#FAAD14", "#F5222D", "#722ED1", "#13C2C2", "#EB2F96", "#FA8C16"]',
 '清新自然的绿色主题配色', 0, 1, 0),

('温暖橙', 'SYSTEM', 'WARM',
 '["#FA8C16", "#FAAD14", "#F5222D", "#EB2F96", "#722ED1", "#1890FF", "#52C41A", "#13C2C2"]',
 '温暖的橙色系配色方案', 0, 1, 0),

('冷静蓝', 'SYSTEM', 'COOL',
 '["#13C2C2", "#1890FF", "#722ED1", "#2F54EB", "#08979C", "#0050B3", "#531DAB", "#9254DE"]',
 '冷静理性的蓝色系配色', 0, 1, 0),

('暗夜模式', 'SYSTEM', 'DARK',
 '["#434343", "#616161", "#757575", "#9E9E9E", "#1976D2", "#388E3C", "#F57C00", "#D32F2F"]',
 '适合暗色主题的配色方案', 0, 1, 0),

('彩虹色彩', 'SYSTEM', 'COLORFUL',
 '["#FF5722", "#FF9800", "#FFEB3B", "#8BC34A", "#00BCD4", "#2196F3", "#3F51B5", "#9C27B0"]',
 '丰富多彩的彩虹配色方案', 0, 1, 0);

-- 插入缓存清理策略
INSERT IGNORE INTO `cache_cleanup_policies` (
    `data_type`, `policy_name`, `max_entries`, `max_age_hours`, 
    `max_size_mb`, `cleanup_on_last_access`
) VALUES 
('PROJECT_OVERVIEW', '项目概览清理策略', 500, 12, 50, 6),
('CHART_DATA', '图表数据清理策略', 1000, 6, 100, 3),
('SYSTEM_METRICS', '系统指标清理策略', 200, 2, 20, 1),
('WIDGET_DATA', '组件数据清理策略', 2000, 8, 200, 4);

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 创建完成提示
SELECT 'Dashboard Management Module Migration Completed Successfully!' as Status;