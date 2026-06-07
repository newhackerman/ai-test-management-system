-- 用户角色权限管理增强 - 数据库迁移脚本
-- 支持zentao风格的角色权限控制和操作审计

-- 1. 创建权限组表
CREATE TABLE IF NOT EXISTS permission_groups (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '权限组ID',
    code VARCHAR(100) NOT NULL UNIQUE COMMENT '权限组代码',
    name VARCHAR(100) NOT NULL COMMENT '权限组名称',
    description TEXT COMMENT '权限组描述',
    color VARCHAR(20) COMMENT '显示颜色',
    icon VARCHAR(50) COMMENT '图标',
    sort_order INT DEFAULT 0 NOT NULL COMMENT '排序顺序',
    is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_permission_groups_code (code),
    INDEX idx_permission_groups_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限组表';

-- 2. 创建权限组项目关联表
CREATE TABLE IF NOT EXISTS permission_group_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '关联ID',
    group_id BIGINT NOT NULL COMMENT '权限组ID',
    permission_id INT NOT NULL COMMENT '权限ID',
    sort_order INT DEFAULT 0 NOT NULL COMMENT '排序顺序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (group_id) REFERENCES permission_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    INDEX idx_permission_group_items_group (group_id),
    INDEX idx_permission_group_items_permission (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限组项目关联表';

-- 3. 创建角色组表
CREATE TABLE IF NOT EXISTS role_groups (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '角色组ID',
    code VARCHAR(100) NOT NULL UNIQUE COMMENT '角色组代码',
    name VARCHAR(100) NOT NULL COMMENT '角色组名称',
    description TEXT COMMENT '角色组描述',
    color VARCHAR(20) COMMENT '显示颜色',
    icon VARCHAR(50) COMMENT '图标',
    sort_order INT DEFAULT 0 NOT NULL COMMENT '排序顺序',
    is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_role_groups_code (code),
    INDEX idx_role_groups_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色组表';

-- 4. 创建角色组项目关联表
CREATE TABLE IF NOT EXISTS role_group_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '关联ID',
    group_id BIGINT NOT NULL COMMENT '角色组ID',
    role_id INT NOT NULL COMMENT '角色ID',
    sort_order INT DEFAULT 0 NOT NULL COMMENT '排序顺序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (group_id) REFERENCES role_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    INDEX idx_role_group_items_group (group_id),
    INDEX idx_role_group_items_role (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色组项目关联表';

-- 5. 创建角色模板表
CREATE TABLE IF NOT EXISTS role_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '模板ID',
    name VARCHAR(100) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    category VARCHAR(50) COMMENT '模板分类',
    template_data JSON NOT NULL COMMENT '模板数据',
    is_system_template BOOLEAN DEFAULT FALSE NOT NULL COMMENT '是否系统模板',
    is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活',
    usage_count INT DEFAULT 0 NOT NULL COMMENT '使用次数',
    last_used_at TIMESTAMP NULL COMMENT '最后使用时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_role_templates_name (name),
    INDEX idx_role_templates_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色模板表';

-- 6. 创建角色审批表
CREATE TABLE IF NOT EXISTS role_approvals (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '审批ID',
    user_id INT NOT NULL COMMENT '申请用户ID',
    role_id INT NOT NULL COMMENT '申请角色ID',
    action VARCHAR(20) NOT NULL COMMENT '操作类型',
    reason TEXT COMMENT '申请原因',
    status VARCHAR(20) DEFAULT 'pending' NOT NULL COMMENT '审批状态',
    approver_id INT COMMENT '审批人ID',
    approved_at TIMESTAMP NULL COMMENT '审批时间',
    approval_reason TEXT COMMENT '审批意见',
    effective_at TIMESTAMP NULL COMMENT '生效时间',
    expires_at TIMESTAMP NULL COMMENT '过期时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_role_approvals_user (user_id),
    INDEX idx_role_approvals_role (role_id),
    INDEX idx_role_approvals_status (status),
    INDEX idx_role_approvals_approver (approver_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色审批表';

-- 7. 创建用户直接权限表
CREATE TABLE IF NOT EXISTS user_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '关联ID',
    user_id INT NOT NULL COMMENT '用户ID',
    permission_id INT NOT NULL COMMENT '权限ID',
    effect ENUM('ALLOW', 'DENY') DEFAULT 'ALLOW' COMMENT '权限效果',
    conditions JSON COMMENT '权限条件',
    granted_by INT COMMENT '授权人',
    granted_at TIMESTAMP NULL COMMENT '授权时间',
    expires_at TIMESTAMP NULL COMMENT '过期时间',
    reason TEXT COMMENT '授权原因',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_permissions_user (user_id),
    INDEX idx_user_permissions_permission (permission_id),
    INDEX idx_user_permissions_granted_by (granted_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户直接权限表';

-- 8. 创建数据权限表
CREATE TABLE IF NOT EXISTS data_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '数据权限ID',
    name VARCHAR(100) NOT NULL COMMENT '数据权限名称',
    description TEXT COMMENT '权限描述',
    resource_type VARCHAR(50) NOT NULL COMMENT '资源类型',
    scope_type VARCHAR(20) NOT NULL COMMENT '范围类型',
    scope_value JSON COMMENT '范围值',
    filter_conditions JSON COMMENT '过滤条件',
    field_permissions JSON COMMENT '字段权限',
    is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活',
    priority INT DEFAULT 0 NOT NULL COMMENT '优先级',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_data_permissions_resource_type (resource_type),
    INDEX idx_data_permissions_scope_type (scope_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据权限表';

-- 9. 创建用户数据权限关联表
CREATE TABLE IF NOT EXISTS user_data_permissions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '关联ID',
    user_id INT NOT NULL COMMENT '用户ID',
    data_permission_id BIGINT NOT NULL COMMENT '数据权限ID',
    granted_by INT COMMENT '授权人',
    granted_at TIMESTAMP NULL COMMENT '授权时间',
    expires_at TIMESTAMP NULL COMMENT '过期时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (data_permission_id) REFERENCES data_permissions(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_data_permissions_user (user_id),
    INDEX idx_user_data_permissions_data_permission (data_permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户数据权限关联表';

-- 10. 增强现有角色表的字段（检查字段是否存在）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'roles' 
     AND table_schema = DATABASE() 
     AND column_name = 'inherit_parent_permissions') > 0,
    'SELECT ''Column inherit_parent_permissions already exists'' as message',
    'ALTER TABLE roles ADD COLUMN inherit_parent_permissions BOOLEAN DEFAULT TRUE NOT NULL COMMENT ''是否继承父角色权限'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'roles' 
     AND table_schema = DATABASE() 
     AND column_name = 'permission_policy') > 0,
    'SELECT ''Column permission_policy already exists'' as message',
    'ALTER TABLE roles ADD COLUMN permission_policy VARCHAR(20) DEFAULT ''merge'' NOT NULL COMMENT ''权限策略'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'roles' 
     AND table_schema = DATABASE() 
     AND column_name = 'data_scope') > 0,
    'SELECT ''Column data_scope already exists'' as message',
    'ALTER TABLE roles ADD COLUMN data_scope VARCHAR(20) DEFAULT ''all'' NOT NULL COMMENT ''数据范围'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'roles' 
     AND table_schema = DATABASE() 
     AND column_name = 'data_scope_config') > 0,
    'SELECT ''Column data_scope_config already exists'' as message',
    'ALTER TABLE roles ADD COLUMN data_scope_config JSON COMMENT ''数据范围配置'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 11. 增强现有权限表的字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'permissions' 
     AND table_schema = DATABASE() 
     AND column_name = 'conditions') > 0,
    'SELECT ''Column conditions already exists'' as message',
    'ALTER TABLE permissions ADD COLUMN conditions JSON COMMENT ''权限条件'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 12. 增强现有角色权限关联表的字段
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'role_permissions' 
     AND table_schema = DATABASE() 
     AND column_name = 'conditions') > 0,
    'SELECT ''Column conditions already exists'' as message',
    'ALTER TABLE role_permissions ADD COLUMN conditions JSON COMMENT ''权限条件'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'role_permissions' 
     AND table_schema = DATABASE() 
     AND column_name = 'granted_by') > 0,
    'SELECT ''Column granted_by already exists'' as message',
    'ALTER TABLE role_permissions ADD COLUMN granted_by INT COMMENT ''授权人'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'role_permissions' 
     AND table_schema = DATABASE() 
     AND column_name = 'granted_at') > 0,
    'SELECT ''Column granted_at already exists'' as message',
    'ALTER TABLE role_permissions ADD COLUMN granted_at TIMESTAMP NULL COMMENT ''授权时间'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'role_permissions' 
     AND table_schema = DATABASE() 
     AND column_name = 'expires_at') > 0,
    'SELECT ''Column expires_at already exists'' as message',
    'ALTER TABLE role_permissions ADD COLUMN expires_at TIMESTAMP NULL COMMENT ''过期时间'''
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加外键约束（检查约束是否存在）
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
     WHERE table_name = 'role_permissions' 
     AND table_schema = DATABASE() 
     AND constraint_name = 'fk_role_permissions_granted_by') > 0,
    'SELECT ''Foreign key fk_role_permissions_granted_by already exists'' as message',
    'ALTER TABLE role_permissions ADD CONSTRAINT fk_role_permissions_granted_by FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 13. 初始化默认权限组
INSERT IGNORE INTO permission_groups (code, name, description, color, icon, sort_order) VALUES
('user_management', '用户管理', '用户账户管理相关权限', '#1890ff', 'UserOutlined', 1),
('role_management', '角色管理', '角色和权限管理相关权限', '#52c41a', 'SafetyOutlined', 2),
('project_management', '项目管理', '项目管理相关权限', '#722ed1', 'ProjectOutlined', 3),
('requirement_management', '需求管理', '需求管理相关权限', '#fa8c16', 'FileTextOutlined', 4),
('test_management', '测试管理', '测试管理相关权限', '#eb2f96', 'BugOutlined', 5),
('system_management', '系统管理', '系统配置和管理相关权限', '#f5222d', 'SettingOutlined', 6);

-- 14. 初始化默认角色组
INSERT IGNORE INTO role_groups (code, name, description, color, icon, sort_order) VALUES
('admin_roles', '管理员角色', '系统管理员相关角色', '#f5222d', 'CrownOutlined', 1),
('business_roles', '业务角色', '业务相关角色', '#1890ff', 'TeamOutlined', 2),
('technical_roles', '技术角色', '技术相关角色', '#52c41a', 'CodeOutlined', 3),
('guest_roles', '访客角色', '访客和只读角色', '#d9d9d9', 'EyeOutlined', 4);

-- 15. 初始化默认数据权限
INSERT IGNORE INTO data_permissions (name, description, resource_type, scope_type, scope_value, is_active, priority) VALUES
('全部数据权限', '可以访问所有数据', 'all', 'all', JSON_ARRAY('*'), TRUE, 100),
('部门数据权限', '只能访问本部门数据', 'department', 'dept', JSON_ARRAY(), TRUE, 80),
('个人数据权限', '只能访问个人数据', 'personal', 'self', JSON_ARRAY(), TRUE, 60),
('项目数据权限', '只能访问参与的项目数据', 'project', 'custom', JSON_ARRAY(), TRUE, 70);

-- 16. 创建操作审计日志增强表（如果不存在）
CREATE TABLE IF NOT EXISTS audit_logs_enhanced (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '审计日志ID',
    user_id INT COMMENT '用户ID',
    session_id VARCHAR(100) COMMENT '会话ID',
    action VARCHAR(50) NOT NULL COMMENT '操作类型',
    resource_type VARCHAR(50) NOT NULL COMMENT '资源类型',
    resource_id VARCHAR(100) NOT NULL COMMENT '资源ID',
    result ENUM('SUCCESS', 'FAILURE', 'PARTIAL') NOT NULL COMMENT '操作结果',
    old_values JSON COMMENT '操作前的值',
    new_values JSON COMMENT '操作后的值',
    error_message TEXT COMMENT '错误信息',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    extra_data JSON COMMENT '额外数据',
    risk_level ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'LOW' COMMENT '风险级别',
    is_suspicious BOOLEAN DEFAULT FALSE COMMENT '是否可疑操作',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_audit_logs_enhanced_user (user_id),
    INDEX idx_audit_logs_enhanced_action (action),
    INDEX idx_audit_logs_enhanced_resource (resource_type, resource_id),
    INDEX idx_audit_logs_enhanced_result (result),
    INDEX idx_audit_logs_enhanced_created_at (created_at),
    INDEX idx_audit_logs_enhanced_ip (ip_address),
    INDEX idx_audit_logs_enhanced_suspicious (is_suspicious)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='增强审计日志表';

-- 17. 创建用户会话管理表（如果不存在）
CREATE TABLE IF NOT EXISTS user_sessions_enhanced (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '会话ID',
    user_id INT NOT NULL COMMENT '用户ID',
    session_token VARCHAR(500) UNIQUE NOT NULL COMMENT '会话令牌',
    refresh_token VARCHAR(500) COMMENT '刷新令牌',
    device_type VARCHAR(50) COMMENT '设备类型',
    device_id VARCHAR(100) COMMENT '设备ID',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    location VARCHAR(100) COMMENT '地理位置',
    is_active BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否激活',
    is_trusted BOOLEAN DEFAULT FALSE COMMENT '是否受信任设备',
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '最后活动时间',
    expires_at TIMESTAMP NOT NULL COMMENT '过期时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_sessions_enhanced_user (user_id),
    INDEX idx_user_sessions_enhanced_token (session_token),
    INDEX idx_user_sessions_enhanced_active (is_active),
    INDEX idx_user_sessions_enhanced_expires (expires_at),
    INDEX idx_user_sessions_enhanced_ip (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='增强用户会话表';

-- 18. 创建权限缓存表
CREATE TABLE IF NOT EXISTS permission_cache (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '缓存ID',
    user_id INT NOT NULL COMMENT '用户ID',
    permission_codes TEXT NOT NULL COMMENT '权限代码列表',
    data_scope JSON COMMENT '数据权限范围',
    cache_key VARCHAR(100) UNIQUE NOT NULL COMMENT '缓存键',
    expires_at TIMESTAMP NOT NULL COMMENT '过期时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_permission_cache_user (user_id),
    INDEX idx_permission_cache_key (cache_key),
    INDEX idx_permission_cache_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限缓存表';

-- 19. 创建安全事件表
CREATE TABLE IF NOT EXISTS security_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '事件ID',
    event_type VARCHAR(50) NOT NULL COMMENT '事件类型',
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL COMMENT '严重程度',
    user_id INT COMMENT '相关用户ID',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    event_data JSON COMMENT '事件数据',
    description TEXT COMMENT '事件描述',
    is_resolved BOOLEAN DEFAULT FALSE COMMENT '是否已解决',
    resolved_by INT COMMENT '解决人ID',
    resolved_at TIMESTAMP NULL COMMENT '解决时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_security_events_type (event_type),
    INDEX idx_security_events_severity (severity),
    INDEX idx_security_events_user (user_id),
    INDEX idx_security_events_ip (ip_address),
    INDEX idx_security_events_resolved (is_resolved),
    INDEX idx_security_events_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='安全事件表';

-- 20. 创建通知配置表
CREATE TABLE IF NOT EXISTS notification_configs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    user_id INT NOT NULL COMMENT '用户ID',
    notification_type VARCHAR(50) NOT NULL COMMENT '通知类型',
    channel VARCHAR(20) NOT NULL COMMENT '通知渠道',
    is_enabled BOOLEAN DEFAULT TRUE NOT NULL COMMENT '是否启用',
    config_data JSON COMMENT '配置数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notification_configs_user (user_id),
    INDEX idx_notification_configs_type (notification_type),
    INDEX idx_notification_configs_channel (channel),
    UNIQUE KEY uk_notification_configs (user_id, notification_type, channel)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知配置表';

-- 完成迁移
SELECT 'User Role Permission Enhancement Migration Completed Successfully' as status;