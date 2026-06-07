-- =====================================================
-- AI自动化测试管理系统 - 配置管理模块基础数据脚本
-- 版本: 1.0
-- 创建时间: 2024-12-19
-- 说明: 配置管理相关的基础数据插入
-- =====================================================

-- 设置字符集
SET NAMES utf8mb4;

-- =====================================================
-- 1. 插入环境数据
-- =====================================================
INSERT INTO `sys_environment` (`env_name`, `env_code`, `description`, `is_active`, `sort_order`, `created_at`) VALUES
('开发环境', 'dev', '用于开发和调试的环境', 1, 1, NOW()),
('测试环境', 'test', '用于功能测试和集成测试的环境', 1, 2, NOW()),
('生产环境', 'prod', '正式运行的生产环境', 1, 3, NOW());

-- =====================================================
-- 2. 插入配置分组
-- =====================================================
INSERT INTO `sys_config_group` (`group_name`, `group_code`, `description`, `is_system`, `is_enabled`, `sort_order`, `icon`, `color`, `created_at`) VALUES
('系统配置', 'system', '系统核心配置项', 1, 1, 1, 'settings', '#409EFF', NOW()),
('数据库配置', 'database', '数据库连接和配置参数', 1, 1, 2, 'database', '#67C23A', NOW()),
('缓存配置', 'cache', 'Redis缓存相关配置', 1, 1, 3, 'layer-group', '#E6A23C', NOW()),
('安全配置', 'security', '安全认证和加密配置', 1, 1, 4, 'shield', '#F56C6C', NOW()),
('邮件配置', 'email', '邮件服务配置', 1, 1, 5, 'envelope', '#909399', NOW()),
('日志配置', 'logging', '日志记录相关配置', 1, 1, 6, 'file-text', '#606266', NOW()),
('业务配置', 'business', '业务相关配置项', 0, 1, 7, 'briefcase', '#8E44AD', NOW()),
('第三方服务', 'third_party', '第三方API和服务配置', 0, 1, 8, 'plug', '#16A085', NOW());

-- =====================================================
-- 3. 插入开发环境配置
-- =====================================================
INSERT INTO `sys_config` (`config_key`, `config_value`, `config_type`, `group_id`, `environment`, `description`, `is_core`, `is_enabled`, `is_encrypted`, `is_required`, `sort_order`, `created_at`) VALUES
-- 系统配置
('system.app_name', 'AI自动化测试管理系统', 'STRING', 1, 'dev', '应用系统名称', 1, 1, 0, 1, 1, NOW()),
('system.app_version', '1.0.0', 'STRING', 1, 'dev', '应用版本号', 1, 1, 0, 1, 2, NOW()),
('system.debug_mode', 'true', 'BOOLEAN', 1, 'dev', '是否开启调试模式', 1, 1, 0, 1, 3, NOW()),
('system.max_upload_size', '10485760', 'INTEGER', 1, 'dev', '最大上传文件大小(字节)', 1, 1, 0, 1, 4, NOW()),
('system.session_timeout', '7200', 'INTEGER', 1, 'dev', '会话超时时间(秒)', 1, 1, 0, 1, 5, NOW()),

-- 数据库配置
('database.host', 'localhost', 'STRING', 2, 'dev', '数据库主机地址', 1, 1, 0, 1, 1, NOW()),
('database.port', '3306', 'INTEGER', 2, 'dev', '数据库端口', 1, 1, 0, 1, 2, NOW()),
('database.name', 'ai_test_management_dev', 'STRING', 2, 'dev', '数据库名称', 1, 1, 0, 1, 3, NOW()),
('database.username', 'root', 'STRING', 2, 'dev', '数据库用户名', 1, 1, 0, 1, 4, NOW()),
('database.password', 'dev_password_123', 'PASSWORD', 2, 'dev', '数据库密码', 1, 1, 1, 1, 5, NOW()),
('database.pool_size', '10', 'INTEGER', 2, 'dev', '连接池大小', 1, 1, 0, 1, 6, NOW()),
('database.max_overflow', '20', 'INTEGER', 2, 'dev', '连接池最大溢出', 1, 1, 0, 1, 7, NOW()),

-- 缓存配置
('cache.redis_host', 'localhost', 'STRING', 3, 'dev', 'Redis主机地址', 1, 1, 0, 1, 1, NOW()),
('cache.redis_port', '6379', 'INTEGER', 3, 'dev', 'Redis端口', 1, 1, 0, 1, 2, NOW()),
('cache.redis_password', '', 'PASSWORD', 3, 'dev', 'Redis密码', 0, 1, 1, 0, 3, NOW()),
('cache.redis_db', '0', 'INTEGER', 3, 'dev', 'Redis数据库索引', 1, 1, 0, 1, 4, NOW()),
('cache.default_ttl', '3600', 'INTEGER', 3, 'dev', '默认缓存过期时间(秒)', 1, 1, 0, 1, 5, NOW()),

-- 安全配置
('security.jwt_secret', 'your-super-secret-jwt-key-for-dev', 'PASSWORD', 4, 'dev', 'JWT签名密钥', 1, 1, 1, 1, 1, NOW()),
('security.jwt_expire_hours', '24', 'INTEGER', 4, 'dev', 'JWT过期时间(小时)', 1, 1, 0, 1, 2, NOW()),
('security.password_min_length', '6', 'INTEGER', 4, 'dev', '密码最小长度', 1, 1, 0, 1, 3, NOW()),
('security.max_login_attempts', '10', 'INTEGER', 4, 'dev', '最大登录尝试次数', 1, 1, 0, 1, 4, NOW()),
('security.account_lockout_duration', '300', 'INTEGER', 4, 'dev', '账户锁定时长(秒)', 1, 1, 0, 1, 5, NOW()),

-- 邮件配置
('email.smtp_host', 'smtp.gmail.com', 'STRING', 5, 'dev', 'SMTP服务器地址', 0, 1, 0, 0, 1, NOW()),
('email.smtp_port', '587', 'INTEGER', 5, 'dev', 'SMTP端口', 0, 1, 0, 0, 2, NOW()),
('email.smtp_username', 'dev@yourcompany.com', 'STRING', 5, 'dev', 'SMTP用户名', 0, 1, 0, 0, 3, NOW()),
('email.smtp_password', 'dev_email_password', 'PASSWORD', 5, 'dev', 'SMTP密码', 0, 1, 1, 0, 4, NOW()),
('email.from_address', 'noreply-dev@yourcompany.com', 'STRING', 5, 'dev', '发件人地址', 0, 1, 0, 0, 5, NOW()),

-- 日志配置
('logging.level', 'DEBUG', 'STRING', 6, 'dev', '日志级别', 1, 1, 0, 1, 1, NOW()),
('logging.max_file_size', '100MB', 'STRING', 6, 'dev', '单个日志文件最大大小', 1, 1, 0, 1, 2, NOW()),
('logging.backup_count', '10', 'INTEGER', 6, 'dev', '日志文件备份数量', 1, 1, 0, 1, 3, NOW()),
('logging.retention_days', '30', 'INTEGER', 6, 'dev', '日志保留天数', 1, 1, 0, 1, 4, NOW());

-- =====================================================
-- 4. 插入测试环境配置
-- =====================================================
INSERT INTO `sys_config` (`config_key`, `config_value`, `config_type`, `group_id`, `environment`, `description`, `is_core`, `is_enabled`, `is_encrypted`, `is_required`, `sort_order`, `created_at`) VALUES
-- 系统配置
('system.app_name', 'AI自动化测试管理系统-测试', 'STRING', 1, 'test', '应用系统名称', 1, 1, 0, 1, 1, NOW()),
('system.app_version', '1.0.0', 'STRING', 1, 'test', '应用版本号', 1, 1, 0, 1, 2, NOW()),
('system.debug_mode', 'false', 'BOOLEAN', 1, 'test', '是否开启调试模式', 1, 1, 0, 1, 3, NOW()),
('system.max_upload_size', '10485760', 'INTEGER', 1, 'test', '最大上传文件大小(字节)', 1, 1, 0, 1, 4, NOW()),
('system.session_timeout', '7200', 'INTEGER', 1, 'test', '会话超时时间(秒)', 1, 1, 0, 1, 5, NOW()),

-- 数据库配置
('database.host', 'test-db.yourcompany.com', 'STRING', 2, 'test', '数据库主机地址', 1, 1, 0, 1, 1, NOW()),
('database.port', '3306', 'INTEGER', 2, 'test', '数据库端口', 1, 1, 0, 1, 2, NOW()),
('database.name', 'ai_test_management_test', 'STRING', 2, 'test', '数据库名称', 1, 1, 0, 1, 3, NOW()),
('database.username', 'test_user', 'STRING', 2, 'test', '数据库用户名', 1, 1, 0, 1, 4, NOW()),
('database.password', 'test_password_123', 'PASSWORD', 2, 'test', '数据库密码', 1, 1, 1, 1, 5, NOW()),

-- 缓存配置
('cache.redis_host', 'test-redis.yourcompany.com', 'STRING', 3, 'test', 'Redis主机地址', 1, 1, 0, 1, 1, NOW()),
('cache.redis_port', '6379', 'INTEGER', 3, 'test', 'Redis端口', 1, 1, 0, 1, 2, NOW()),
('cache.redis_password', 'test_redis_password', 'PASSWORD', 3, 'test', 'Redis密码', 0, 1, 1, 0, 3, NOW()),

-- 安全配置
('security.jwt_secret', 'test-environment-jwt-secret-key', 'PASSWORD', 4, 'test', 'JWT签名密钥', 1, 1, 1, 1, 1, NOW()),
('security.jwt_expire_hours', '12', 'INTEGER', 4, 'test', 'JWT过期时间(小时)', 1, 1, 0, 1, 2, NOW()),

-- 日志配置
('logging.level', 'INFO', 'STRING', 6, 'test', '日志级别', 1, 1, 0, 1, 1, NOW()),
('logging.retention_days', '14', 'INTEGER', 6, 'test', '日志保留天数', 1, 1, 0, 1, 4, NOW());

-- =====================================================
-- 5. 插入生产环境配置
-- =====================================================
INSERT INTO `sys_config` (`config_key`, `config_value`, `config_type`, `group_id`, `environment`, `description`, `is_core`, `is_enabled`, `is_encrypted`, `is_required`, `sort_order`, `created_at`) VALUES
-- 系统配置
('system.app_name', 'AI自动化测试管理系统', 'STRING', 1, 'prod', '应用系统名称', 1, 1, 0, 1, 1, NOW()),
('system.app_version', '1.0.0', 'STRING', 1, 'prod', '应用版本号', 1, 1, 0, 1, 2, NOW()),
('system.debug_mode', 'false', 'BOOLEAN', 1, 'prod', '是否开启调试模式', 1, 1, 0, 1, 3, NOW()),
('system.max_upload_size', '10485760', 'INTEGER', 1, 'prod', '最大上传文件大小(字节)', 1, 1, 0, 1, 4, NOW()),
('system.session_timeout', '7200', 'INTEGER', 1, 'prod', '会话超时时间(秒)', 1, 1, 0, 1, 5, NOW()),

-- 数据库配置
('database.host', 'prod-db.yourcompany.com', 'STRING', 2, 'prod', '数据库主机地址', 1, 1, 0, 1, 1, NOW()),
('database.port', '3306', 'INTEGER', 2, 'prod', '数据库端口', 1, 1, 0, 1, 2, NOW()),
('database.name', 'ai_test_management_prod', 'STRING', 2, 'prod', '数据库名称', 1, 1, 0, 1, 3, NOW()),
('database.username', 'prod_user', 'STRING', 2, 'prod', '数据库用户名', 1, 1, 0, 1, 4, NOW()),
('database.password', 'CHANGE_THIS_IN_PRODUCTION', 'PASSWORD', 2, 'prod', '数据库密码', 1, 1, 1, 1, 5, NOW()),

-- 缓存配置
('cache.redis_host', 'prod-redis.yourcompany.com', 'STRING', 3, 'prod', 'Redis主机地址', 1, 1, 0, 1, 1, NOW()),
('cache.redis_port', '6379', 'INTEGER', 3, 'prod', 'Redis端口', 1, 1, 0, 1, 2, NOW()),
('cache.redis_password', 'CHANGE_THIS_IN_PRODUCTION', 'PASSWORD', 3, 'prod', 'Redis密码', 0, 1, 1, 0, 3, NOW()),

-- 安全配置
('security.jwt_secret', 'CHANGE_THIS_TO_A_STRONG_SECRET_IN_PRODUCTION', 'PASSWORD', 4, 'prod', 'JWT签名密钥', 1, 1, 1, 1, 1, NOW()),
('security.jwt_expire_hours', '8', 'INTEGER', 4, 'prod', 'JWT过期时间(小时)', 1, 1, 0, 1, 2, NOW()),
('security.password_min_length', '8', 'INTEGER', 4, 'prod', '密码最小长度', 1, 1, 0, 1, 3, NOW()),
('security.max_login_attempts', '5', 'INTEGER', 4, 'prod', '最大登录尝试次数', 1, 1, 0, 1, 4, NOW()),
('security.account_lockout_duration', '1800', 'INTEGER', 4, 'prod', '账户锁定时长(秒)', 1, 1, 0, 1, 5, NOW()),

-- 日志配置
('logging.level', 'WARNING', 'STRING', 6, 'prod', '日志级别', 1, 1, 0, 1, 1, NOW()),
('logging.retention_days', '90', 'INTEGER', 6, 'prod', '日志保留天数', 1, 1, 0, 1, 4, NOW());

-- =====================================================
-- 6. 插入业务配置示例
-- =====================================================
INSERT INTO `sys_config` (`config_key`, `config_value`, `config_type`, `group_id`, `environment`, `description`, `is_core`, `is_enabled`, `is_encrypted`, `is_required`, `sort_order`, `created_at`) VALUES
-- 测试相关配置
('test.max_concurrent_tests', '5', 'INTEGER', 7, 'dev', '最大并发测试数量', 0, 1, 0, 0, 1, NOW()),
('test.default_timeout', '300', 'INTEGER', 7, 'dev', '默认测试超时时间(秒)', 0, 1, 0, 0, 2, NOW()),
('test.report_retention_days', '30', 'INTEGER', 7, 'dev', '测试报告保留天数', 0, 1, 0, 0, 3, NOW()),
('test.notification_webhook', 'https://hooks.slack.com/your-webhook-url', 'URL', 7, 'dev', '测试通知Webhook地址', 0, 1, 0, 0, 4, NOW()),

-- AI服务配置
('ai.openai_api_key', 'sk-your-openai-api-key', 'PASSWORD', 8, 'dev', 'OpenAI API密钥', 0, 1, 1, 0, 1, NOW()),
('ai.model_name', 'gpt-4', 'STRING', 8, 'dev', '默认AI模型名称', 0, 1, 0, 0, 2, NOW()),
('ai.max_tokens', '2048', 'INTEGER', 8, 'dev', '最大token数量', 0, 1, 0, 0, 3, NOW()),
('ai.temperature', '0.7', 'STRING', 8, 'dev', '模型温度参数', 0, 1, 0, 0, 4, NOW());

-- =====================================================
-- 7. 说明注释
-- =====================================================
/*
重要提示：
1. 所有密码配置（config_type = 'PASSWORD'）都应该在实际部署时修改为安全的值
2. 生产环境的密码配置（environment = 'prod'）必须更改默认值
3. JWT密钥应该使用足够复杂的随机字符串
4. 数据库和Redis密码应该使用强密码策略
5. 建议定期轮换密钥和密码
6. 敏感配置应该通过环境变量或安全的配置管理系统来管理

配置类型说明：
- STRING: 普通字符串配置
- INTEGER: 整数配置
- BOOLEAN: 布尔值配置（true/false）
- JSON: JSON格式配置
- PASSWORD: 密码类型配置（会加密存储）
- URL: 网址类型配置

环境说明：
- dev: 开发环境，用于开发和调试
- test: 测试环境，用于功能测试和集成测试
- prod: 生产环境，正式运行环境

分组说明：
- system: 系统核心配置
- database: 数据库相关配置
- cache: 缓存相关配置
- security: 安全相关配置
- email: 邮件服务配置
- logging: 日志相关配置
- business: 业务相关配置
- third_party: 第三方服务配置
*/