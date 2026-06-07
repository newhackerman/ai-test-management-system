-- =====================================================
-- AI助手模块完整初始化脚本
-- 版本: 1.0
-- 创建时间: 2024-12-19
-- 
-- 使用说明：
-- 1. 在MySQL中执行此脚本来初始化AI助手模块
-- 2. 确保数据库已创建并有足够权限
-- 3. 确保用户表(users)已存在
-- 4. 生产环境部署前请修改所有API密钥
-- 
-- 执行方式：
-- mysql -u root -p your_database_name < init_ai_assistant.sql
-- =====================================================

-- 检查MySQL版本和字符集
SELECT VERSION() as mysql_version;
SELECT @@character_set_database as db_charset;

-- 设置字符集和时区
SET NAMES utf8mb4;
SET time_zone = '+08:00';
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 第一部分：创建表结构
-- =====================================================

-- 执行表结构创建脚本
SOURCE ai_assistant_tables.sql;

-- =====================================================
-- 第二部分：插入基础数据
-- =====================================================

-- 执行基础数据插入脚本
SOURCE ai_assistant_data.sql;

-- =====================================================
-- 第三部分：验证和检查
-- =====================================================

-- 检查表结构是否创建成功
SHOW TABLES LIKE 'ai_%';

-- 检查数据是否插入成功
SELECT 
    'ai_model_configs' as table_name, 
    COUNT(*) as record_count,
    SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled_count
FROM ai_model_configs
UNION ALL
SELECT 
    'ai_prompt_templates' as table_name, 
    COUNT(*) as record_count,
    SUM(CASE WHEN visibility = 'PUBLIC' THEN 1 ELSE 0 END) as public_count
FROM ai_prompt_templates
UNION ALL
SELECT 
    'ai_chat_sessions' as table_name, 
    COUNT(*) as record_count,
    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_count
FROM ai_chat_sessions
UNION ALL
SELECT 
    'ai_chat_messages' as table_name, 
    COUNT(*) as record_count,
    0 as other_count
FROM ai_chat_messages;

-- 检查各AI提供商的模型配置
SELECT 
    provider,
    COUNT(*) as total_models,
    SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled_models,
    SUM(CASE WHEN is_default = 1 THEN 1 ELSE 0 END) as default_models,
    AVG(priority) as avg_priority
FROM ai_model_configs 
GROUP BY provider 
ORDER BY avg_priority DESC;

-- 检查提示词模板分类
SELECT 
    category,
    subcategory,
    COUNT(*) as template_count,
    SUM(CASE WHEN is_featured = 1 THEN 1 ELSE 0 END) as featured_count
FROM ai_prompt_templates 
GROUP BY category, subcategory 
ORDER BY category, subcategory;

-- =====================================================
-- 第四部分：创建视图（可选）
-- =====================================================

-- AI模型配置详情视图
CREATE OR REPLACE VIEW v_ai_model_detail AS
SELECT 
    id,
    provider,
    model_name,
    display_name,
    description,
    is_enabled,
    is_default,
    is_public,
    priority,
    max_tokens,
    temperature,
    daily_quota,
    monthly_quota,
    cost_per_input_token,
    cost_per_output_token,
    health_status,
    last_health_check,
    total_requests,
    total_tokens_used,
    total_cost,
    created_at,
    updated_at
FROM ai_model_configs
WHERE deleted_at IS NULL;

-- AI会话统计视图
CREATE OR REPLACE VIEW v_ai_session_stats AS
SELECT 
    s.id,
    s.title,
    s.user_id,
    s.status,
    s.ai_provider,
    s.ai_model,
    s.message_count,
    s.total_tokens,
    s.total_cost,
    s.last_activity_at,
    s.created_at,
    COUNT(m.id) as actual_message_count,
    SUM(m.tokens_used) as actual_tokens_used,
    SUM(m.cost) as actual_cost
FROM ai_chat_sessions s
LEFT JOIN ai_chat_messages m ON s.id = m.session_id AND m.deleted_at IS NULL
WHERE s.deleted_at IS NULL
GROUP BY s.id;

-- AI使用统计汇总视图
CREATE OR REPLACE VIEW v_ai_usage_summary AS
SELECT 
    user_id,
    ai_provider,
    ai_model,
    operation_type,
    stat_date,
    SUM(request_count) as total_requests,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost) as total_cost,
    AVG(success_rate) as avg_success_rate
FROM ai_usage_stats
GROUP BY user_id, ai_provider, ai_model, operation_type, stat_date;

-- 提示词模板使用统计视图
CREATE OR REPLACE VIEW v_template_usage_stats AS
SELECT 
    t.id,
    t.name,
    t.title,
    t.category,
    t.subcategory,
    t.visibility,
    t.owner_id,
    t.usage_count,
    t.rating_avg,
    t.rating_count,
    COUNT(u.id) as actual_usage_count,
    AVG(u.user_rating) as actual_rating_avg
FROM ai_prompt_templates t
LEFT JOIN ai_template_usage u ON t.id = u.template_id
WHERE t.deleted_at IS NULL
GROUP BY t.id;

-- =====================================================
-- 第五部分：创建存储过程（可选）
-- =====================================================

DELIMITER //

-- 获取用户可用的AI模型
CREATE PROCEDURE GetAvailableModels(
    IN p_user_id BIGINT,
    IN p_provider VARCHAR(50)
)
BEGIN
    SELECT 
        id,
        provider,
        model_name,
        display_name,
        description,
        max_tokens,
        temperature,
        is_default,
        priority,
        health_status,
        user_daily_quota,
        cost_per_input_token,
        cost_per_output_token
    FROM ai_model_configs
    WHERE is_enabled = 1 
    AND is_public = 1
    AND (p_provider IS NULL OR provider = p_provider)
    AND health_status IN ('HEALTHY', 'DEGRADED')
    AND deleted_at IS NULL
    ORDER BY is_default DESC, priority DESC, provider, model_name;
END//

-- 记录AI使用统计
CREATE PROCEDURE RecordAIUsage(
    IN p_user_id BIGINT,
    IN p_session_id BIGINT,
    IN p_ai_provider VARCHAR(50),
    IN p_ai_model VARCHAR(100),
    IN p_operation_type VARCHAR(20),
    IN p_input_tokens INT,
    IN p_output_tokens INT,
    IN p_total_cost DECIMAL(8,4)
)
BEGIN
    DECLARE v_stat_date DATE DEFAULT CURDATE();
    DECLARE v_total_tokens INT DEFAULT p_input_tokens + p_output_tokens;
    
    -- 插入或更新每日统计
    INSERT INTO ai_usage_stats (
        user_id, session_id, ai_provider, ai_model, operation_type,
        request_count, input_tokens, output_tokens, total_tokens,
        total_cost, success_count, stat_date, stat_period,
        created_at, updated_at
    ) VALUES (
        p_user_id, p_session_id, p_ai_provider, p_ai_model, p_operation_type,
        1, p_input_tokens, p_output_tokens, v_total_tokens,
        p_total_cost, 1, v_stat_date, 'DAILY',
        NOW(), NOW()
    ) ON DUPLICATE KEY UPDATE
        request_count = request_count + 1,
        input_tokens = input_tokens + p_input_tokens,
        output_tokens = output_tokens + p_output_tokens,
        total_tokens = total_tokens + v_total_tokens,
        total_cost = total_cost + p_total_cost,
        success_count = success_count + 1,
        updated_at = NOW();
        
    -- 更新模型配置统计
    UPDATE ai_model_configs 
    SET total_requests = total_requests + 1,
        total_tokens_used = total_tokens_used + v_total_tokens,
        total_cost = total_cost + p_total_cost,
        last_used_at = NOW()
    WHERE provider = p_ai_provider 
    AND model_name = p_ai_model;
END//

-- 获取用户AI使用统计
CREATE PROCEDURE GetUserAIStats(
    IN p_user_id BIGINT,
    IN p_start_date DATE,
    IN p_end_date DATE
)
BEGIN
    SELECT 
        ai_provider,
        ai_model,
        operation_type,
        SUM(request_count) as total_requests,
        SUM(total_tokens) as total_tokens,
        SUM(total_cost) as total_cost,
        AVG(success_rate) as avg_success_rate,
        MIN(stat_date) as first_use_date,
        MAX(stat_date) as last_use_date
    FROM ai_usage_stats
    WHERE user_id = p_user_id
    AND stat_date BETWEEN p_start_date AND p_end_date
    GROUP BY ai_provider, ai_model, operation_type
    ORDER BY total_cost DESC, total_requests DESC;
END//

-- 清理过期数据
CREATE PROCEDURE CleanupExpiredData(
    IN p_days_to_keep INT DEFAULT 90
)
BEGIN
    DECLARE v_cutoff_date DATE DEFAULT DATE_SUB(CURDATE(), INTERVAL p_days_to_keep DAY);
    
    -- 清理过期的会话（软删除）
    UPDATE ai_chat_sessions 
    SET deleted_at = NOW()
    WHERE status = 'DELETED' 
    AND updated_at < v_cutoff_date
    AND deleted_at IS NULL;
    
    -- 清理过期的使用统计（硬删除）
    DELETE FROM ai_usage_stats 
    WHERE stat_date < DATE_SUB(CURDATE(), INTERVAL 365 DAY);
    
    -- 清理过期的模板使用记录
    DELETE FROM ai_template_usage 
    WHERE created_at < DATE_SUB(NOW(), INTERVAL 180 DAY);
    
    SELECT 
        'cleanup_completed' as status,
        v_cutoff_date as cutoff_date,
        NOW() as cleanup_time;
END//

DELIMITER ;

-- =====================================================
-- 第六部分：设置权限和安全
-- =====================================================

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- 第七部分：性能优化建议
-- =====================================================

-- 分析表以优化查询性能
ANALYZE TABLE ai_chat_sessions;
ANALYZE TABLE ai_chat_messages;
ANALYZE TABLE ai_model_configs;
ANALYZE TABLE ai_prompt_templates;
ANALYZE TABLE ai_suggestions;
ANALYZE TABLE ai_requirements_analysis;
ANALYZE TABLE ai_usage_stats;

-- =====================================================
-- 完成信息显示
-- =====================================================

-- 显示初始化完成信息
SELECT 'AI助手模块初始化完成！' as message;
SELECT NOW() as completed_at;

-- 显示统计信息
SELECT 
    (SELECT COUNT(*) FROM ai_model_configs WHERE is_enabled = 1) as enabled_models,
    (SELECT COUNT(*) FROM ai_prompt_templates WHERE visibility = 'PUBLIC') as public_templates,
    (SELECT COUNT(*) FROM ai_chat_sessions) as total_sessions,
    (SELECT COUNT(*) FROM ai_chat_messages) as total_messages;

-- 显示各提供商模型统计
SELECT 
    provider,
    COUNT(*) as model_count,
    SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled_count,
    SUM(CASE WHEN health_status = 'HEALTHY' THEN 1 ELSE 0 END) as healthy_count
FROM ai_model_configs 
GROUP BY provider
ORDER BY provider;

-- =====================================================
-- 部署后检查清单
-- =====================================================
/*
部署后必须检查的事项：

1. 安全配置：
   - 修改所有AI模型的API密钥
   - 设置合适的配额限制
   - 配置访问权限

2. 环境变量：
   - OPENAI_API_KEY: OpenAI API密钥
   - ANTHROPIC_API_KEY: Anthropic API密钥
   - BAIDU_API_KEY: 百度API密钥
   - ALIYUN_API_KEY: 阿里云API密钥

3. 数据库优化：
   - 根据实际使用情况调整索引
   - 设置合适的连接池大小
   - 配置定期备份策略

4. 监控设置：
   - AI使用量监控
   - 成本控制告警
   - 性能指标监控
   - 错误率监控

5. 功能测试：
   - 测试各AI模型连接
   - 测试会话创建和消息发送
   - 测试模板使用功能
   - 测试统计数据收集

6. 性能优化：
   - 配置Redis缓存
   - 设置合适的超时时间
   - 优化数据库查询
   - 配置负载均衡

7. 数据管理：
   - 设置数据保留策略
   - 配置自动清理任务
   - 建立数据备份机制
   - 测试数据恢复流程
*/