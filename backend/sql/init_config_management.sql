-- =====================================================
-- AI自动化测试管理系统 - 配置管理模块完整初始化脚本
-- 版本: 1.0
-- 创建时间: 2024-12-19
-- 
-- 使用说明：
-- 1. 在MySQL中执行此脚本来初始化配置管理模块
-- 2. 确保数据库已创建并有足够权限
-- 3. 生产环境部署前请修改所有默认密码
-- 
-- 执行方式：
-- mysql -u root -p your_database_name < init_config_management.sql
-- =====================================================

-- 检查MySQL版本和字符集
SELECT VERSION() as mysql_version;

-- 设置字符集和时区
SET NAMES utf8mb4;
SET time_zone = '+08:00';
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 第一部分：创建表结构
-- =====================================================
SOURCE config_tables.sql;

-- =====================================================
-- 第二部分：插入基础数据
-- =====================================================
SOURCE config_data.sql;

-- =====================================================
-- 第三部分：验证和检查
-- =====================================================

-- 检查表结构
SHOW TABLES LIKE 'sys_config%';
SHOW TABLES LIKE 'sys_environment%';

-- 检查数据是否插入成功
SELECT COUNT(*) as environment_count FROM sys_environment;
SELECT COUNT(*) as group_count FROM sys_config_group;
SELECT COUNT(*) as config_count FROM sys_config;

-- 检查各环境配置数量
SELECT environment, COUNT(*) as config_count 
FROM sys_config 
GROUP BY environment 
ORDER BY environment;

-- 检查各分组配置数量
SELECT g.group_name, g.group_code, COUNT(c.id) as config_count
FROM sys_config_group g
LEFT JOIN sys_config c ON g.id = c.group_id
GROUP BY g.id, g.group_name, g.group_code
ORDER BY g.sort_order;

-- =====================================================
-- 第四部分：创建视图（可选）
-- =====================================================

-- 配置详情视图
CREATE OR REPLACE VIEW v_config_detail AS
SELECT 
    c.id,
    c.config_key,
    c.config_value,
    c.config_type,
    c.environment,
    g.group_name,
    g.group_code,
    c.description,
    c.is_core,
    c.is_enabled,
    c.is_encrypted,
    c.is_required,
    c.created_at,
    c.updated_at
FROM sys_config c
LEFT JOIN sys_config_group g ON c.group_id = g.id
WHERE c.deleted_at IS NULL;

-- 环境配置统计视图
CREATE OR REPLACE VIEW v_environment_stats AS
SELECT 
    e.env_code,
    e.env_name,
    COUNT(c.id) as total_configs,
    SUM(CASE WHEN c.is_enabled = 1 THEN 1 ELSE 0 END) as enabled_configs,
    SUM(CASE WHEN c.is_core = 1 THEN 1 ELSE 0 END) as core_configs,
    SUM(CASE WHEN c.is_encrypted = 1 THEN 1 ELSE 0 END) as encrypted_configs
FROM sys_environment e
LEFT JOIN sys_config c ON e.env_code = c.environment AND c.deleted_at IS NULL
WHERE e.deleted_at IS NULL
GROUP BY e.id, e.env_code, e.env_name
ORDER BY e.sort_order;

-- 分组配置统计视图
CREATE OR REPLACE VIEW v_group_stats AS
SELECT 
    g.id as group_id,
    g.group_name,
    g.group_code,
    COUNT(c.id) as total_configs,
    SUM(CASE WHEN c.environment = 'dev' THEN 1 ELSE 0 END) as dev_configs,
    SUM(CASE WHEN c.environment = 'test' THEN 1 ELSE 0 END) as test_configs,
    SUM(CASE WHEN c.environment = 'prod' THEN 1 ELSE 0 END) as prod_configs
FROM sys_config_group g
LEFT JOIN sys_config c ON g.id = c.group_id AND c.deleted_at IS NULL
WHERE g.deleted_at IS NULL
GROUP BY g.id, g.group_name, g.group_code
ORDER BY g.sort_order;

-- =====================================================
-- 第五部分：创建存储过程（可选）
-- =====================================================

DELIMITER //

-- 配置查询存储过程
CREATE PROCEDURE GetConfigByKeyAndEnv(
    IN p_config_key VARCHAR(200),
    IN p_environment VARCHAR(10)
)
BEGIN
    SELECT 
        c.id,
        c.config_key,
        c.config_value,
        c.config_type,
        c.environment,
        c.description,
        c.is_encrypted,
        g.group_name,
        g.group_code
    FROM sys_config c
    LEFT JOIN sys_config_group g ON c.group_id = g.id
    WHERE c.config_key = p_config_key 
    AND c.environment = p_environment
    AND c.deleted_at IS NULL
    AND c.is_enabled = 1;
END//

-- 环境配置同步存储过程
CREATE PROCEDURE SyncConfigBetweenEnv(
    IN p_source_env VARCHAR(10),
    IN p_target_env VARCHAR(10),
    IN p_config_key VARCHAR(200)
)
BEGIN
    DECLARE v_config_value TEXT;
    DECLARE v_config_type VARCHAR(20);
    DECLARE v_group_id BIGINT;
    DECLARE v_description TEXT;
    DECLARE v_is_core TINYINT;
    DECLARE v_is_encrypted TINYINT;
    DECLARE v_is_required TINYINT;
    DECLARE v_sort_order INT;
    
    -- 获取源环境配置
    SELECT config_value, config_type, group_id, description, is_core, is_encrypted, is_required, sort_order
    INTO v_config_value, v_config_type, v_group_id, v_description, v_is_core, v_is_encrypted, v_is_required, v_sort_order
    FROM sys_config
    WHERE config_key = p_config_key AND environment = p_source_env AND deleted_at IS NULL;
    
    -- 检查目标环境是否已存在该配置
    IF EXISTS (SELECT 1 FROM sys_config WHERE config_key = p_config_key AND environment = p_target_env AND deleted_at IS NULL) THEN
        -- 更新现有配置
        UPDATE sys_config 
        SET config_value = v_config_value,
            config_type = v_config_type,
            description = v_description,
            updated_at = NOW()
        WHERE config_key = p_config_key AND environment = p_target_env AND deleted_at IS NULL;
    ELSE
        -- 创建新配置
        INSERT INTO sys_config (
            config_key, config_value, config_type, group_id, environment,
            description, is_core, is_enabled, is_encrypted, is_required, sort_order,
            created_at, updated_at
        ) VALUES (
            p_config_key, v_config_value, v_config_type, v_group_id, p_target_env,
            v_description, v_is_core, 1, v_is_encrypted, v_is_required, v_sort_order,
            NOW(), NOW()
        );
    END IF;
END//

DELIMITER ;

-- =====================================================
-- 第六部分：设置权限和安全
-- =====================================================

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示初始化完成信息
SELECT '配置管理模块初始化完成！' as message;
SELECT NOW() as completed_at;

-- 显示统计信息
SELECT 
    (SELECT COUNT(*) FROM sys_environment) as environments,
    (SELECT COUNT(*) FROM sys_config_group) as groups,
    (SELECT COUNT(*) FROM sys_config) as configs,
    (SELECT COUNT(DISTINCT config_key) FROM sys_config) as unique_keys;

-- =====================================================
-- 部署后检查清单
-- =====================================================
/*
部署后必须检查的安全事项：

1. 修改所有生产环境密码配置：
   - database.password (生产数据库密码)
   - cache.redis_password (生产Redis密码)
   - security.jwt_secret (JWT签名密钥)

2. 配置环境变量：
   - CONFIG_ENCRYPTION_KEY: 配置加密密钥
   - DATABASE_URL: 数据库连接URL
   - REDIS_URL: Redis连接URL

3. 验证表权限：
   - 确保应用用户有足够的表操作权限
   - 检查外键约束是否正常工作

4. 测试配置功能：
   - 测试配置的增删改查
   - 测试配置加密解密
   - 测试环境间配置同步

5. 监控设置：
   - 配置变更审计日志
   - 配置访问频率监控
   - 敏感配置访问告警

6. 备份策略：
   - 定期备份配置数据
   - 配置变更前自动备份
   - 测试恢复流程
*/