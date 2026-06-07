-- 仪表板管理模块数据库迁移脚本
-- 版本: 1.0.0
-- 创建时间: 2024-01-01
-- 描述: 创建仪表板管理模块所需的所有数据库表和索引

-- 设置字符集和排序规则
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================================
-- 1. 仪表板配置表 (dashboard_configs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `dashboard_configs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '配置ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `role_type` ENUM('ADMIN','PROJECT_MANAGER','REQUIREMENT_MANAGER','DESIGNER','ARCHITECT','DEVELOPER','TESTER','DEVOPS','THIRD_PARTY') NOT NULL COMMENT '角色类型',
    `dashboard_name` VARCHAR(100) NOT NULL COMMENT '仪表板名称',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认配置',
    `layout_config` JSON COMMENT '布局配置',
    `widget_configs` JSON COMMENT '组件配置列表',
    `theme_config` JSON COMMENT '主题配置',
    `refresh_interval` INT DEFAULT 30 COMMENT '刷新间隔(秒)',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    INDEX `idx_user_role` (`user_id`, `role_type`),
    INDEX `idx_role_type` (`role_type`),
    INDEX `idx_is_default` (`is_default`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仪表板配置表';

-- ============================================================================
-- 2. 组件定义表 (widget_definitions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `widget_definitions` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '组件定义ID',
    `widget_type` VARCHAR(50) NOT NULL UNIQUE COMMENT '组件类型',
    `widget_name` VARCHAR(100) NOT NULL COMMENT '组件名称',
    `description` TEXT COMMENT '组件描述',
    `category` ENUM('STATISTICS','CHARTS','PROGRESS','STATUS','RANKING','CALENDAR','MAP','TABLE') NOT NULL COMMENT '组件分类',
    `default_config` JSON COMMENT '默认配置',
    `data_source_config` JSON COMMENT '数据源配置',
    `supported_roles` JSON COMMENT '支持的角色列表',
    `min_width` INT DEFAULT 2 COMMENT '最小宽度',
    `min_height` INT DEFAULT 2 COMMENT '最小高度',
    `max_width` INT DEFAULT 12 COMMENT '最大宽度',
    `max_height` INT DEFAULT 12 COMMENT '最大高度',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_widget_type` (`widget_type`),
    INDEX `idx_category` (`category`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组件定义表';

-- ============================================================================
-- 3. 配色方案表 (color_schemes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `color_schemes` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '配色方案ID',
    `scheme_name` VARCHAR(100) NOT NULL COMMENT '方案名称',
    `scheme_type` ENUM('SYSTEM','ENTERPRISE','USER_CUSTOM') NOT NULL COMMENT '方案类型',
    `scheme_category` VARCHAR(50) COMMENT '方案分类（商务、科技、清新等）',
    `color_palette` JSON NOT NULL COMMENT '颜色数组',
    `description` TEXT COMMENT '方案描述',
    `preview_image` VARCHAR(500) COMMENT '预览图片路径',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认方案',
    `is_public` TINYINT(1) DEFAULT 0 COMMENT '是否公开方案',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否激活',
    `created_by` BIGINT COMMENT '创建者ID',
    `organization_id` BIGINT COMMENT '组织ID（企业方案）',
    `usage_count` INT DEFAULT 0 COMMENT '使用次数',
    `rating` DECIMAL(3,2) DEFAULT 0.00 COMMENT '用户评分',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    INDEX `idx_scheme_type` (`scheme_type`),
    INDEX `idx_scheme_category` (`scheme_category`),
    INDEX `idx_is_default` (`is_default`),
    INDEX `idx_is_public` (`is_public`),
    INDEX `idx_created_by` (`created_by`),
    INDEX `idx_organization_id` (`organization_id`),
    INDEX `idx_usage_count` (`usage_count`),
    INDEX `idx_rating` (`rating`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='配色方案表';

-- ============================================================================
-- 4. 用户配色偏好表 (user_color_preferences)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `user_color_preferences` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '偏好ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `color_scheme_id` BIGINT COMMENT '选择的配色方案ID',
    `custom_colors` JSON COMMENT '用户自定义颜色',
    `auto_switch_dark_mode` TINYINT(1) DEFAULT 0 COMMENT '是否自动切换暗色模式',
    `accessibility_mode` TINYINT(1) DEFAULT 0 COMMENT '是否启用无障碍模式',
    `high_contrast` TINYINT(1) DEFAULT 0 COMMENT '是否启用高对比度',
    `apply_to_charts` TINYINT(1) DEFAULT 1 COMMENT '是否应用到图表',
    `apply_to_widgets` TINYINT(1) DEFAULT 1 COMMENT '是否应用到组件',
    `apply_to_theme` TINYINT(1) DEFAULT 0 COMMENT '是否应用到整体主题',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_color_preferences` (`user_id`),
    INDEX `idx_color_scheme_id` (`color_scheme_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户配色偏好表';

-- ============================================================================
-- 5. 仪表板数据缓存表 (dashboard_data_cache)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `dashboard_data_cache` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '缓存ID',
    `cache_key` VARCHAR(255) NOT NULL COMMENT '缓存键',
    `data_type` VARCHAR(50) NOT NULL COMMENT '数据类型',
    `data_content` JSON NOT NULL COMMENT '数据内容',
    `project_id` BIGINT COMMENT '关联项目ID',
    `user_id` BIGINT COMMENT '关联用户ID',
    `expires_at` TIMESTAMP NOT NULL COMMENT '过期时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cache_key` (`cache_key`),
    INDEX `idx_data_type` (`data_type`),
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_expires_at` (`expires_at`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仪表板数据缓存表';

-- ============================================================================
-- 6. WebSocket连接管理表 (websocket_connections)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `websocket_connections` (
    `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '连接ID',
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `connection_id` VARCHAR(255) NOT NULL COMMENT '连接标识',
    `role_type` ENUM('ADMIN','PROJECT_MANAGER','REQUIREMENT_MANAGER','DESIGNER','ARCHITECT','DEVELOPER','TESTER','DEVOPS','THIRD_PARTY') NOT NULL COMMENT '角色类型',
    `project_ids` JSON COMMENT '订阅的项目ID列表',
    `subscribed_events` JSON COMMENT '订阅的事件类型',
    `client_info` JSON COMMENT '客户端信息',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否活跃',
    `last_heartbeat` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最后心跳时间',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_connection_id` (`connection_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_role_type` (`role_type`),
    INDEX `idx_is_active` (`is_active`),
    INDEX `idx_last_heartbeat` (`last_heartbeat`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='WebSocket连接管理表';

-- ============================================================================
-- 7. 插入默认数据
-- ============================================================================

-- 插入默认组件定义
INSERT IGNORE INTO `widget_definitions` (`widget_type`, `widget_name`, `description`, `category`, `default_config`, `supported_roles`, `min_width`, `min_height`, `max_width`, `max_height`) VALUES
('stat_card', '统计卡片', '显示关键指标的数值卡片', 'STATISTICS', '{"showIcon": true, "showTrend": true, "precision": 2}', '["ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER"]', 2, 2, 4, 3),
('line_chart', '折线图', '显示趋势数据的折线图', 'CHARTS', '{"showGrid": true, "showLegend": true, "smooth": false}', '["ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER"]', 4, 3, 12, 8),
('bar_chart', '柱状图', '显示对比数据的柱状图', 'CHARTS', '{"showGrid": true, "showLegend": true, "stacked": false}', '["ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER"]', 4, 3, 12, 8),
('pie_chart', '饼图', '显示占比数据的饼图', 'CHARTS', '{"showLegend": true, "showLabels": true, "donut": false}', '["ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER"]', 3, 3, 6, 6),
('progress_bar', '进度条', '显示进度的条形图', 'PROGRESS', '{"showPercentage": true, "showLabel": true, "animated": true}', '["ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER"]', 2, 1, 8, 2),
('status_panel', '状态面板', '显示系统状态的面板', 'STATUS', '{"showIcon": true, "autoRefresh": true, "alertThreshold": 80}', '["ADMIN", "DEVOPS"]', 3, 2, 6, 4),
('ranking_list', '排行榜', '显示排序数据的列表', 'RANKING', '{"showRank": true, "showValue": true, "maxItems": 10}', '["ADMIN", "PROJECT_MANAGER"]', 3, 4, 6, 8),
('calendar_view', '日历视图', '显示时间事件的日历', 'CALENDAR', '{"showWeekends": true, "showEvents": true, "defaultView": "month"}', '["PROJECT_MANAGER", "DEVELOPER", "TESTER"]', 4, 4, 12, 8),
('data_table', '数据表格', '显示结构化数据的表格', 'TABLE', '{"showPagination": true, "showSearch": true, "pageSize": 10}', '["ADMIN", "PROJECT_MANAGER", "DEVELOPER", "TESTER"]', 4, 3, 12, 8);

-- 插入默认配色方案
INSERT IGNORE INTO `color_schemes` (`scheme_name`, `scheme_type`, `scheme_category`, `color_palette`, `description`, `is_default`, `is_public`) VALUES
('默认蓝色', 'SYSTEM', '商务', '["#1890ff", "#52c41a", "#faad14", "#f5222d", "#722ed1", "#13c2c2", "#eb2f96", "#fa8c16"]', '经典蓝色商务配色方案', 1, 1),
('绿色生态', 'SYSTEM', '环保', '["#52c41a", "#73d13d", "#95de64", "#b7eb8f", "#d9f7be", "#f6ffed", "#389e0d", "#237804"]', '清新绿色环保主题', 0, 1),
('紫色科技', 'SYSTEM', '科技', '["#722ed1", "#9254de", "#b37feb", "#d3adf7", "#efdbff", "#f9f0ff", "#531dab", "#391085"]', '现代紫色科技感配色', 0, 1),
('橙色活力', 'SYSTEM', '活跃', '["#fa8c16", "#ffa940", "#ffc069", "#ffd591", "#ffe7ba", "#fff7e6", "#d46b08", "#ad4e00"]', '充满活力的橙色主题', 0, 1),
('青色清新', 'SYSTEM', '清新', '["#13c2c2", "#36cfc9", "#5cdbd3", "#87e8de", "#b5f5ec", "#e6fffb", "#08979c", "#006d75"]', '清新淡雅的青色主题', 0, 1);

-- 插入默认仪表板配置（系统级别）
INSERT IGNORE INTO `dashboard_configs` (`user_id`, `role_type`, `dashboard_name`, `is_default`, `layout_config`, `widget_configs`, `theme_config`) VALUES
(0, 'ADMIN', '系统管理员默认仪表板', 1, 
'[{"i": "system-overview", "x": 0, "y": 0, "w": 6, "h": 4}, {"i": "user-statistics", "x": 6, "y": 0, "w": 6, "h": 4}, {"i": "performance-metrics", "x": 0, "y": 4, "w": 12, "h": 6}]',
'[{"id": "system-overview", "type": "stat_card", "title": "系统概览"}, {"id": "user-statistics", "type": "bar_chart", "title": "用户统计"}, {"id": "performance-metrics", "type": "line_chart", "title": "性能指标"}]',
'{"colorScheme": "default", "theme": "light"}'),

(0, 'PROJECT_MANAGER', '项目管理员默认仪表板', 1,
'[{"i": "project-overview", "x": 0, "y": 0, "w": 8, "h": 4}, {"i": "team-status", "x": 8, "y": 0, "w": 4, "h": 4}, {"i": "progress-chart", "x": 0, "y": 4, "w": 6, "h": 6}, {"i": "milestone-timeline", "x": 6, "y": 4, "w": 6, "h": 6}]',
'[{"id": "project-overview", "type": "stat_card", "title": "项目概览"}, {"id": "team-status", "type": "status_panel", "title": "团队状态"}, {"id": "progress-chart", "type": "progress_bar", "title": "项目进度"}, {"id": "milestone-timeline", "type": "calendar_view", "title": "里程碑时间线"}]',
'{"colorScheme": "default", "theme": "light"}'),

(0, 'DEVELOPER', '开发人员默认仪表板', 1,
'[{"i": "my-tasks", "x": 0, "y": 0, "w": 6, "h": 4}, {"i": "code-quality", "x": 6, "y": 0, "w": 6, "h": 4}, {"i": "commit-activity", "x": 0, "y": 4, "w": 12, "h": 6}]',
'[{"id": "my-tasks", "type": "data_table", "title": "我的任务"}, {"id": "code-quality", "type": "stat_card", "title": "代码质量"}, {"id": "commit-activity", "type": "line_chart", "title": "提交活动"}]',
'{"colorScheme": "default", "theme": "light"}'),

(0, 'TESTER', '测试人员默认仪表板', 1,
'[{"i": "test-execution", "x": 0, "y": 0, "w": 6, "h": 4}, {"i": "defect-summary", "x": 6, "y": 0, "w": 6, "h": 4}, {"i": "test-coverage", "x": 0, "y": 4, "w": 12, "h": 6}]',
'[{"id": "test-execution", "type": "stat_card", "title": "测试执行"}, {"id": "defect-summary", "type": "pie_chart", "title": "缺陷统计"}, {"id": "test-coverage", "type": "bar_chart", "title": "测试覆盖率"}]',
'{"colorScheme": "default", "theme": "light"}');

-- ============================================================================
-- 8. 创建触发器和存储过程
-- ============================================================================

-- 创建清理过期缓存的存储过程
DELIMITER $$
CREATE PROCEDURE IF NOT EXISTS `CleanExpiredDashboardCache`()
BEGIN
    DELETE FROM `dashboard_data_cache` WHERE `expires_at` < NOW();
    SELECT ROW_COUNT() as deleted_rows;
END$$
DELIMITER ;

-- 创建清理非活跃WebSocket连接的存储过程
DELIMITER $$
CREATE PROCEDURE IF NOT EXISTS `CleanInactiveWebSocketConnections`()
BEGIN
    DELETE FROM `websocket_connections` 
    WHERE `is_active` = 0 OR `last_heartbeat` < DATE_SUB(NOW(), INTERVAL 1 HOUR);
    SELECT ROW_COUNT() as deleted_rows;
END$$
DELIMITER ;

-- 创建获取用户仪表板统计的存储过程
DELIMITER $$
CREATE PROCEDURE IF NOT EXISTS `GetUserDashboardStats`(IN p_user_id BIGINT)
BEGIN
    SELECT 
        COUNT(*) as total_dashboards,
        COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_dashboards,
        COUNT(DISTINCT role_type) as role_count,
        MAX(updated_at) as last_updated
    FROM `dashboard_configs` 
    WHERE `user_id` = p_user_id;
END$$
DELIMITER ;

-- ============================================================================
-- 9. 创建视图
-- ============================================================================

-- 创建仪表板使用统计视图
CREATE OR REPLACE VIEW `dashboard_usage_stats` AS
SELECT 
    dc.role_type,
    COUNT(*) as config_count,
    COUNT(DISTINCT dc.user_id) as user_count,
    AVG(dc.refresh_interval) as avg_refresh_interval,
    MAX(dc.updated_at) as last_updated
FROM `dashboard_configs` dc
WHERE dc.is_active = 1
GROUP BY dc.role_type;

-- 创建组件使用统计视图
CREATE OR REPLACE VIEW `widget_usage_stats` AS
SELECT 
    wd.widget_type,
    wd.widget_name,
    wd.category,
    COUNT(*) as usage_count
FROM `widget_definitions` wd
WHERE wd.is_active = 1
GROUP BY wd.widget_type, wd.widget_name, wd.category
ORDER BY usage_count DESC;

-- 创建配色方案使用统计视图
CREATE OR REPLACE VIEW `color_scheme_stats` AS
SELECT 
    cs.scheme_name,
    cs.scheme_type,
    cs.scheme_category,
    cs.usage_count,
    cs.rating,
    COUNT(ucp.user_id) as active_users
FROM `color_schemes` cs
LEFT JOIN `user_color_preferences` ucp ON cs.id = ucp.color_scheme_id
WHERE cs.is_active = 1
GROUP BY cs.id, cs.scheme_name, cs.scheme_type, cs.scheme_category, cs.usage_count, cs.rating
ORDER BY cs.usage_count DESC, cs.rating DESC;

-- ============================================================================
-- 10. 设置权限和约束
-- ============================================================================

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 创建数据库用户（如果需要）
-- CREATE USER IF NOT EXISTS 'dashboard_user'@'localhost' IDENTIFIED BY 'dashboard_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON *.dashboard_* TO 'dashboard_user'@'localhost';
-- FLUSH PRIVILEGES;

-- ============================================================================
-- 迁移完成标记
-- ============================================================================

-- 创建迁移记录表（如果不存在）
CREATE TABLE IF NOT EXISTS `migration_history` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `migration_name` VARCHAR(255) NOT NULL,
    `version` VARCHAR(50) NOT NULL,
    `description` TEXT,
    `executed_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_migration_name` (`migration_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据库迁移历史记录';

-- 记录本次迁移
INSERT IGNORE INTO `migration_history` (`migration_name`, `version`, `description`) 
VALUES ('dashboard_module_migration', '1.0.0', '仪表板管理模块初始化迁移');

-- 输出迁移完成信息
SELECT 'Dashboard module migration completed successfully!' as status;