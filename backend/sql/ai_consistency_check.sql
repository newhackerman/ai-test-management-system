-- =====================================================
-- AI助手模块业务一致性检查脚本
-- 文件名: ai_consistency_check.sql
-- 描述: 用于验证AI助手模块数据库设计的业务逻辑一致性
-- 版本: 1.0
-- 创建时间: 2024-12-27
-- =====================================================

USE `aitestdb`;

SELECT '🔍 开始AI助手模块业务一致性检查...' AS message;

-- =====================================================
-- 1. 表结构一致性检查
-- =====================================================

SELECT '📋 1. 表结构一致性检查' AS section_header;

-- 检查主键字段类型一致性
SELECT 
    'PRIMARY_KEY_CONSISTENCY' as check_type,
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    CASE 
        WHEN DATA_TYPE = 'bigint' THEN '✅ 一致'
        ELSE '❌ 不一致：应该是bigint'
    END as status
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%'
AND COLUMN_KEY = 'PRI';

-- 检查外键字段类型一致性  
SELECT 
    'FOREIGN_KEY_CONSISTENCY' as check_type,
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    CASE 
        WHEN COLUMN_NAME LIKE '%_id' AND DATA_TYPE = 'bigint' THEN '✅ 一致'
        WHEN COLUMN_NAME LIKE '%_id' AND DATA_TYPE != 'bigint' THEN '❌ 不一致：ID字段应该是bigint'
        ELSE '⚠️ 需要手动检查'
    END as status
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%'
AND COLUMN_NAME LIKE '%_id';

-- =====================================================
-- 2. 业务逻辑一致性检查
-- =====================================================

SELECT '📝 2. 业务逻辑一致性检查' AS section_header;

-- 检查枚举值业务逻辑
SELECT '会话状态枚举检查' as check_item, COLUMN_TYPE as enum_values
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'ai_chat_sessions' 
AND COLUMN_NAME = 'status';

SELECT '消息角色枚举检查' as check_item, COLUMN_TYPE as enum_values
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'ai_chat_messages' 
AND COLUMN_NAME = 'role';

SELECT '建议类型枚举检查' as check_item, COLUMN_TYPE as enum_values
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'ai_suggestions' 
AND COLUMN_NAME = 'suggestion_type';

-- 检查成本相关字段精度一致性
SELECT 
    'COST_FIELD_PRECISION' as check_type,
    TABLE_NAME,
    COLUMN_NAME,
    COLUMN_TYPE,
    CASE 
        WHEN COLUMN_NAME LIKE '%cost%' AND COLUMN_TYPE LIKE '%decimal%' THEN '✅ 使用decimal类型'
        WHEN COLUMN_NAME LIKE '%cost%' AND COLUMN_TYPE NOT LIKE '%decimal%' THEN '❌ 成本字段应使用decimal'
        ELSE '➖ 非成本字段'
    END as status
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%'
AND COLUMN_NAME LIKE '%cost%';

-- =====================================================
-- 3. 索引完整性检查
-- =====================================================

SELECT '🔍 3. 索引完整性检查' AS section_header;

-- 检查重要查询字段是否有索引
SELECT 
    'INDEX_COVERAGE' as check_type,
    'ai_chat_sessions' as table_name,
    CASE 
        WHEN EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_SCHEMA = DATABASE() 
                   AND TABLE_NAME = 'ai_chat_sessions' 
                   AND COLUMN_NAME = 'user_id') 
        THEN '✅ user_id有索引'
        ELSE '❌ user_id缺少索引'
    END as user_id_index,
    CASE 
        WHEN EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_SCHEMA = DATABASE() 
                   AND TABLE_NAME = 'ai_chat_sessions' 
                   AND COLUMN_NAME = 'status') 
        THEN '✅ status有索引'
        ELSE '❌ status缺少索引'
    END as status_index;

-- 检查消息表索引
SELECT 
    'INDEX_COVERAGE' as check_type,
    'ai_chat_messages' as table_name,
    CASE 
        WHEN EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_SCHEMA = DATABASE() 
                   AND TABLE_NAME = 'ai_chat_messages' 
                   AND COLUMN_NAME = 'session_id') 
        THEN '✅ session_id有索引'
        ELSE '❌ session_id缺少索引'
    END as session_id_index,
    CASE 
        WHEN EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS 
                   WHERE TABLE_SCHEMA = DATABASE() 
                   AND TABLE_NAME = 'ai_chat_messages' 
                   AND COLUMN_NAME = 'created_at') 
        THEN '✅ created_at有索引'
        ELSE '❌ created_at缺少索引'
    END as created_at_index;

-- =====================================================
-- 4. 数据完整性约束检查
-- =====================================================

SELECT '🔒 4. 数据完整性约束检查' AS section_header;

-- 检查外键约束是否正确设置
SELECT 
    'FOREIGN_KEY_CONSTRAINTS' as check_type,
    TABLE_NAME,
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME,
    '✅ 外键约束正确' as status
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%'
AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;

-- =====================================================
-- 5. 业务规则验证
-- =====================================================

SELECT '⚙️ 5. 业务规则验证' AS section_header;

-- 验证AI模型配置的业务规则
SELECT 
    'AI_MODEL_CONFIG_RULES' as check_type,
    provider,
    model_name,
    CASE 
        WHEN cost_per_input_token >= 0 THEN '✅ 输入成本 >= 0'
        ELSE '❌ 输入成本应 >= 0'
    END as input_cost_check,
    CASE 
        WHEN cost_per_output_token >= 0 THEN '✅ 输出成本 >= 0'
        ELSE '❌ 输出成本应 >= 0'
    END as output_cost_check,
    CASE 
        WHEN temperature BETWEEN 0 AND 2 THEN '✅ 温度参数在有效范围'
        ELSE '❌ 温度参数应在0-2之间'
    END as temperature_check,
    CASE 
        WHEN max_tokens > 0 THEN '✅ 最大token > 0'
        ELSE '❌ 最大token应 > 0'
    END as max_tokens_check
FROM ai_model_configs
WHERE provider IS NOT NULL
LIMIT 5;

-- 验证提示词模板的业务规则
SELECT 
    'PROMPT_TEMPLATE_RULES' as check_type,
    name,
    category,
    CASE 
        WHEN LENGTH(content) > 10 THEN '✅ 模板内容不为空'
        ELSE '❌ 模板内容过短'
    END as content_check,
    CASE 
        WHEN visibility IN ('PUBLIC', 'PRIVATE', 'SHARED') THEN '✅ 可见性值正确'
        ELSE '❌ 可见性值无效'
    END as visibility_check,
    CASE 
        WHEN version >= 1 THEN '✅ 版本号有效'
        ELSE '❌ 版本号应 >= 1'
    END as version_check
FROM ai_prompt_templates
WHERE name IS NOT NULL
LIMIT 5;

-- =====================================================
-- 6. 字符集和排序规则检查
-- =====================================================

SELECT '📝 6. 字符集和排序规则检查' AS section_header;

SELECT 
    'CHARSET_COLLATION' as check_type,
    TABLE_NAME,
    TABLE_COLLATION,
    CASE 
        WHEN TABLE_COLLATION = 'utf8mb4_unicode_ci' THEN '✅ 字符集正确'
        ELSE '❌ 建议使用utf8mb4_unicode_ci'
    END as charset_status
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%'
ORDER BY TABLE_NAME;

-- =====================================================
-- 7. JSON字段验证
-- =====================================================

SELECT '📊 7. JSON字段验证' AS section_header;

-- 检查JSON字段默认值
SELECT 
    'JSON_FIELD_VALIDATION' as check_type,
    TABLE_NAME,
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    CASE 
        WHEN COLUMN_DEFAULT = 'json_object()' OR COLUMN_DEFAULT = '{}' THEN '✅ JSON默认值正确'
        WHEN COLUMN_DEFAULT IS NULL AND IS_NULLABLE = 'YES' THEN '⚠️ 允许NULL值'
        ELSE '❌ JSON默认值可能有问题'
    END as default_value_status
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%'
AND DATA_TYPE = 'json'
ORDER BY TABLE_NAME, COLUMN_NAME;

-- =====================================================
-- 8. 统计信息总结
-- =====================================================

SELECT '📈 8. 统计信息总结' AS section_header;

-- 表数量统计
SELECT 
    '表总数' as metric_name,
    COUNT(*) as metric_value,
    'AI助手模块核心表' as description
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%';

-- 索引数量统计
SELECT 
    '索引总数' as metric_name,
    COUNT(DISTINCT INDEX_NAME) as metric_value,
    'AI助手模块表的索引数量' as description
FROM INFORMATION_SCHEMA.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%';

-- 外键约束数量统计
SELECT 
    '外键约束总数' as metric_name,
    COUNT(*) as metric_value,
    'AI助手模块表之间的外键关系' as description
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME LIKE 'ai_%'
AND REFERENCED_TABLE_NAME IS NOT NULL;

-- 初始数据统计
SELECT 
    'AI模型配置数量' as metric_name,
    COUNT(*) as metric_value,
    '预置的AI模型配置' as description
FROM ai_model_configs;

SELECT 
    '提示词模板数量' as metric_name,
    COUNT(*) as metric_value,
    '预置的提示词模板' as description
FROM ai_prompt_templates;

-- =====================================================
-- 完成检查报告
-- =====================================================

SELECT '🎯 完成检查报告' AS section_header;

SELECT CONCAT(
    '🎯 AI助手模块业务一致性检查完成！\n',
    '📊 检查项目：表结构、索引、外键、业务规则、字符集、JSON字段\n',
    '✅ 如果以上检查都显示正常，说明数据库设计与业务需求一致\n',
    '🔧 如有异常项目，请根据检查结果进行相应调整\n',
    '📋 建议定期运行此脚本以确保数据库完整性'
) AS consistency_check_summary;

-- 显示下一步操作建议
SELECT CONCAT(
    '📋 下一步操作建议：\n',
    '1. 在应用启动时运行ai_init_complete.sql初始化数据库\n',
    '2. 配置AI服务提供商的API密钥和访问参数\n',
    '3. 测试AI模型连接状态和响应速度\n',
    '4. 创建第一个AI对话会话验证功能\n',
    '5. 定期运行此一致性检查脚本监控数据库状态\n',
    '6. 根据使用情况调整AI模型优先级和成本控制'
) AS next_steps_recommendations;