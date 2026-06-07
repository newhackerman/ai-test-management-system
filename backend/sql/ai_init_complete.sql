-- =====================================================
-- AI助手模块完整初始化脚本 (ai_init_complete.sql)
-- 版本: 2.0
-- 创建时间: 2024-09-07
-- 说明: 基于AI助手模块任务文档的完整数据库初始化脚本
-- =====================================================

-- 设置字符集和基本配置
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
SET time_zone = '+08:00';

SELECT '开始AI助手模块数据库初始化...' AS message, NOW() AS start_time;

-- =====================================================
-- AI使用统计表 - 完整版本
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_usage_stats` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '会话ID',
  `ai_provider` varchar(50) NOT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) NOT NULL COMMENT 'AI模型名称',
  `operation_type` enum('CHAT','SUGGESTION','ANALYSIS','TEMPLATE','COMPLETION','OTHER') NOT NULL COMMENT '操作类型',
  
  -- 使用量统计
  `request_count` int(11) NOT NULL DEFAULT 1 COMMENT '请求次数',
  `input_tokens` bigint(20) NOT NULL DEFAULT 0 COMMENT '输入Token数',
  `output_tokens` bigint(20) NOT NULL DEFAULT 0 COMMENT '输出Token数',
  `total_tokens` bigint(20) NOT NULL DEFAULT 0 COMMENT '总Token数',
  
  -- 成本统计
  `input_cost` decimal(10,6) NOT NULL DEFAULT 0.000000 COMMENT '输入成本',
  `output_cost` decimal(10,6) NOT NULL DEFAULT 0.000000 COMMENT '输出成本',
  `total_cost` decimal(10,6) NOT NULL DEFAULT 0.000000 COMMENT '总成本',
  
  -- 性能统计
  `avg_response_time` decimal(8,3) DEFAULT NULL COMMENT '平均响应时间',
  `min_response_time` decimal(8,3) DEFAULT NULL COMMENT '最快响应时间',
  `max_response_time` decimal(8,3) DEFAULT NULL COMMENT '最慢响应时间',
  `success_count` int(11) NOT NULL DEFAULT 0 COMMENT '成功次数',
  `error_count` int(11) NOT NULL DEFAULT 0 COMMENT '错误次数',
  `timeout_count` int(11) NOT NULL DEFAULT 0 COMMENT '超时次数',
  `success_rate` decimal(5,2) DEFAULT NULL COMMENT '成功率',
  
  -- 时间维度
  `stat_date` date NOT NULL COMMENT '统计日期',
  `stat_hour` tinyint(4) DEFAULT NULL COMMENT '统计小时',
  `stat_period` enum('HOURLY','DAILY','WEEKLY','MONTHLY') DEFAULT 'DAILY' COMMENT '统计周期',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_provider_model_date_hour_op` (`user_id`, `ai_provider`, `ai_model`, `stat_date`, `stat_hour`, `operation_type`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_ai_provider` (`ai_provider`),
  KEY `idx_ai_model` (`ai_model`),
  KEY `idx_operation_type` (`operation_type`),
  KEY `idx_stat_date` (`stat_date`),
  KEY `idx_stat_period` (`stat_period`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI使用统计表';

-- =====================================================
-- AI模板使用记录表
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_template_usage` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `template_id` bigint(20) NOT NULL COMMENT '模板ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '会话ID',
  `ai_provider` varchar(50) DEFAULT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) DEFAULT NULL COMMENT 'AI模型名称',
  
  -- 使用上下文
  `use_case` varchar(200) DEFAULT NULL COMMENT '使用场景',
  `context_data` json COMMENT '上下文数据',
  `variables_data` json COMMENT '变量数据',
  `rendered_content` longtext COMMENT '渲染后的内容',
  
  -- 使用结果
  `is_successful` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否成功使用',
  `error_message` text COMMENT '错误信息',
  `execution_time` decimal(8,3) DEFAULT NULL COMMENT '执行时间',
  `tokens_used` int(11) DEFAULT 0 COMMENT '使用的Token数',
  `cost` decimal(8,4) DEFAULT 0.0000 COMMENT '使用成本',
  
  -- 用户反馈
  `user_rating` tinyint(4) DEFAULT NULL COMMENT '用户评分',
  `user_feedback` text COMMENT '用户反馈',
  `improvement_suggestions` text COMMENT '改进建议',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_template_id` (`template_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_ai_provider` (`ai_provider`),
  KEY `idx_use_case` (`use_case`),
  KEY `idx_is_successful` (`is_successful`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI模板使用记录表';

-- =====================================================
-- AI操作日志表
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_operation_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '会话ID',
  `operation_type` varchar(50) NOT NULL COMMENT '操作类型',
  `operation_name` varchar(100) NOT NULL COMMENT '操作名称',
  `target_type` varchar(50) DEFAULT NULL COMMENT '目标类型',
  `target_id` bigint(20) DEFAULT NULL COMMENT '目标ID',
  
  -- 操作详情
  `operation_data` json COMMENT '操作数据',
  `request_data` json COMMENT '请求数据',
  `response_data` json COMMENT '响应数据',
  `error_data` json COMMENT '错误数据',
  
  -- 操作结果
  `status` enum('SUCCESS','FAILED','TIMEOUT','CANCELLED') NOT NULL COMMENT '操作状态',
  `error_code` varchar(50) DEFAULT NULL COMMENT '错误代码',
  `error_message` text COMMENT '错误信息',
  
  -- 性能指标
  `execution_time` decimal(8,3) DEFAULT NULL COMMENT '执行时间',
  `ai_provider` varchar(50) DEFAULT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) DEFAULT NULL COMMENT 'AI模型名称',
  `tokens_used` int(11) DEFAULT 0 COMMENT '消耗Token数',
  `cost` decimal(8,4) DEFAULT 0.0000 COMMENT '操作成本',
  
  -- 环境信息
  `ip_address` varchar(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` varchar(500) DEFAULT NULL COMMENT '用户代理',
  `client_info` json COMMENT '客户端信息',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_operation_type` (`operation_type`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI操作日志表';

-- =====================================================
-- AI文件存储表
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_file_storage` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '关联会话ID',
  `file_name` varchar(255) NOT NULL COMMENT '原始文件名',
  `file_path` varchar(500) NOT NULL COMMENT '文件存储路径',
  `file_size` bigint(20) NOT NULL DEFAULT 0 COMMENT '文件大小',
  `file_type` varchar(100) NOT NULL COMMENT '文件类型',
  `mime_type` varchar(100) DEFAULT NULL COMMENT 'MIME类型',
  `file_hash` varchar(64) DEFAULT NULL COMMENT '文件哈希值',
  
  -- 文件分类和用途
  `category` varchar(50) DEFAULT 'GENERAL' COMMENT '文件分类',
  `purpose` varchar(100) DEFAULT NULL COMMENT '用途说明',
  `description` text COMMENT '文件描述',
  
  -- 处理状态
  `status` enum('UPLOADED','PROCESSING','PROCESSED','FAILED','DELETED') DEFAULT 'UPLOADED' COMMENT '处理状态',
  `processing_result` json COMMENT '处理结果',
  `error_message` text COMMENT '错误信息',
  
  -- 访问控制
  `is_public` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否公开',
  `access_token` varchar(64) DEFAULT NULL COMMENT '访问令牌',
  `expires_at` datetime DEFAULT NULL COMMENT '过期时间',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_file_hash` (`file_hash`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_access_token` (`access_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI文件存储表';

-- =====================================================
-- 插入基础AI模型配置数据
-- =====================================================

INSERT INTO `ai_model_configs` (
  `provider`, `model_name`, `display_name`, `description`, `max_tokens`, `temperature`, 
  `is_enabled`, `is_default`, `priority`, `cost_per_input_token`, `cost_per_output_token`,
  `capabilities`, `supported_languages`, `use_cases`, `health_status`
) VALUES 
-- OpenAI模型配置
('openai', 'gpt-4o', 'GPT-4 Omni', '最新的GPT-4模型，支持多模态输入', 4096, 0.70, 1, 1, 90, 0.00001500, 0.00003000, 
 JSON_ARRAY('chat', 'completion', 'analysis', 'multimodal'), JSON_ARRAY('zh-CN', 'en'), JSON_ARRAY('chat', 'suggestion', 'analysis'), 'HEALTHY'),
 
('openai', 'gpt-4-turbo', 'GPT-4 Turbo', '高性能的GPT-4模型，更快的响应速度', 4096, 0.70, 1, 0, 85, 0.00001000, 0.00002000,
 JSON_ARRAY('chat', 'completion', 'analysis'), JSON_ARRAY('zh-CN', 'en'), JSON_ARRAY('chat', 'suggestion', 'analysis'), 'HEALTHY'),
 
('openai', 'gpt-3.5-turbo', 'GPT-3.5 Turbo', '经济实用的GPT模型，适合一般对话', 4096, 0.70, 1, 0, 70, 0.00000050, 0.00000150,
 JSON_ARRAY('chat', 'completion'), JSON_ARRAY('zh-CN', 'en'), JSON_ARRAY('chat'), 'HEALTHY'),

-- Anthropic模型配置
('anthropic', 'claude-3-opus', 'Claude 3 Opus', 'Anthropic最强大的模型，擅长复杂推理', 4096, 0.70, 1, 0, 95, 0.00001500, 0.00007500,
 JSON_ARRAY('chat', 'analysis', 'reasoning'), JSON_ARRAY('zh-CN', 'en'), JSON_ARRAY('chat', 'suggestion', 'analysis'), 'HEALTHY'),
 
('anthropic', 'claude-3-sonnet', 'Claude 3 Sonnet', '平衡性能和成本的Claude模型', 4096, 0.70, 1, 0, 80, 0.00000300, 0.00001500,
 JSON_ARRAY('chat', 'analysis'), JSON_ARRAY('zh-CN', 'en'), JSON_ARRAY('chat', 'suggestion'), 'HEALTHY'),

-- 百度文心模型配置
('baidu', 'ernie-4.0', '文心一言4.0', '百度最新的大语言模型，中文能力强', 4096, 0.70, 1, 0, 75, 0.00001200, 0.00001200,
 JSON_ARRAY('chat', 'completion'), JSON_ARRAY('zh-CN'), JSON_ARRAY('chat'), 'HEALTHY'),
 
('baidu', 'ernie-3.5', '文心一言3.5', '高性价比的中文大模型', 4096, 0.70, 1, 0, 65, 0.00000800, 0.00000800,
 JSON_ARRAY('chat', 'completion'), JSON_ARRAY('zh-CN'), JSON_ARRAY('chat'), 'HEALTHY'),

-- 阿里通义模型配置
('aliyun', 'qwen-max', '通义千问Max', '阿里云通义千问最强模型', 4096, 0.70, 1, 0, 78, 0.00001000, 0.00001000,
 JSON_ARRAY('chat', 'completion', 'analysis'), JSON_ARRAY('zh-CN', 'en'), JSON_ARRAY('chat', 'suggestion'), 'HEALTHY'),
 
('aliyun', 'qwen-plus', '通义千问Plus', '通义千问增强版模型', 4096, 0.70, 1, 0, 72, 0.00000800, 0.00000800,
 JSON_ARRAY('chat', 'completion'), JSON_ARRAY('zh-CN'), JSON_ARRAY('chat'), 'HEALTHY');

-- =====================================================
-- 插入基础提示词模板数据
-- =====================================================

INSERT INTO `ai_prompt_templates` (
  `name`, `title`, `description`, `content`, `category`, `subcategory`, 
  `visibility`, `owner_id`, `is_featured`, `is_verified`,
  `variables`, `use_cases`, `tags`
) VALUES 
-- 需求分析模板
('requirement_analysis', '需求分析专家', '分析软件需求的完整性、清晰度和可行性', 
 '你是一位经验丰富的需求分析专家。请分析以下需求：\n\n{requirement_text}\n\n请从以下维度进行分析：\n1. 完整性：需求是否完整描述了所需功能\n2. 清晰度：需求描述是否清晰明确\n3. 可行性：技术实现的可行性评估\n4. 可测试性：是否可以设计有效的测试用例\n\n请给出具体的改进建议。',
 'ANALYSIS', 'REQUIREMENT', 'PUBLIC', 1, 1, 1,
 JSON_OBJECT('requirement_text', JSON_OBJECT('type', 'text', 'required', true, 'description', '待分析的需求文本')),
 JSON_ARRAY('analysis', 'requirement'), JSON_ARRAY('需求分析', '质量评估')),

-- 代码审查模板
('code_review', '代码审查助手', '协助进行代码质量审查和改进建议', 
 '你是一位资深的代码审查专家。请审查以下代码：\n\n```{language}\n{code}\n```\n\n请从以下方面进行审查：\n1. 代码质量：可读性、可维护性\n2. 性能优化：潜在的性能问题\n3. 安全性：安全漏洞和风险\n4. 最佳实践：是否遵循行业标准\n\n请提供具体的改进建议和示例代码。',
 'DEVELOPMENT', 'CODE_REVIEW', 'PUBLIC', 1, 1, 1,
 JSON_OBJECT('code', JSON_OBJECT('type', 'textarea', 'required', true), 'language', JSON_OBJECT('type', 'select', 'options', JSON_ARRAY('python', 'javascript', 'java', 'go'), 'default', 'python')),
 JSON_ARRAY('development', 'review'), JSON_ARRAY('代码审查', '质量优化')),

-- 测试用例生成模板
('test_case_generation', '测试用例生成器', '基于需求自动生成测试用例', 
 '你是一位测试专家。基于以下需求生成全面的测试用例：\n\n{requirement}\n\n请生成以下类型的测试用例：\n1. 正常功能测试\n2. 边界值测试\n3. 异常情况测试\n4. 性能测试（如需要）\n\n每个测试用例请包含：测试步骤、预期结果、测试数据。',
 'TESTING', 'TEST_CASE', 'PUBLIC', 1, 1, 1,
 JSON_OBJECT('requirement', JSON_OBJECT('type', 'textarea', 'required', true, 'description', '需求描述')),
 JSON_ARRAY('testing', 'automation'), JSON_ARRAY('测试用例', '自动生成')),

-- 项目建议模板
('project_suggestion', '项目优化建议', '分析项目状况并提供改进建议', 
 '作为项目管理顾问，请分析当前项目状况：\n\n项目信息：{project_info}\n当前问题：{current_issues}\n\n请提供：\n1. 问题根因分析\n2. 改进建议和优先级\n3. 实施计划建议\n4. 风险评估\n\n建议要具体可执行，并考虑资源约束。',
 'MANAGEMENT', 'OPTIMIZATION', 'PUBLIC', 1, 1, 1,
 JSON_OBJECT('project_info', JSON_OBJECT('type', 'textarea', 'required', true), 'current_issues', JSON_OBJECT('type', 'textarea', 'required', false)),
 JSON_ARRAY('management', 'suggestion'), JSON_ARRAY('项目管理', '优化建议'));

-- =====================================================
-- 创建视图和存储过程
-- =====================================================

-- AI使用统计汇总视图
CREATE OR REPLACE VIEW `v_ai_usage_summary` AS
SELECT 
  user_id,
  ai_provider,
  ai_model,
  operation_type,
  DATE(stat_date) as usage_date,
  SUM(request_count) as total_requests,
  SUM(total_tokens) as total_tokens,
  SUM(total_cost) as total_cost,
  AVG(success_rate) as avg_success_rate,
  AVG(avg_response_time) as avg_response_time
FROM ai_usage_stats
WHERE stat_period = 'DAILY'
GROUP BY user_id, ai_provider, ai_model, operation_type, DATE(stat_date);

-- 模型性能统计视图
CREATE OR REPLACE VIEW `v_model_performance` AS
SELECT 
  provider,
  model_name,
  display_name,
  is_enabled,
  health_status,
  total_requests,
  total_tokens_used,
  total_cost,
  avg_response_time,
  success_rate,
  last_used_at,
  created_at
FROM ai_model_configs
WHERE deleted_at IS NULL
ORDER BY total_requests DESC;

-- =====================================================
-- 创建存储过程
-- =====================================================

DELIMITER //

-- 记录AI使用统计
CREATE PROCEDURE `RecordAIUsage`(
  IN p_user_id BIGINT,
  IN p_session_id BIGINT,
  IN p_ai_provider VARCHAR(50),
  IN p_ai_model VARCHAR(100),
  IN p_operation_type VARCHAR(20),
  IN p_input_tokens INT,
  IN p_output_tokens INT,
  IN p_total_cost DECIMAL(10,6),
  IN p_response_time DECIMAL(8,3),
  IN p_is_success BOOLEAN
)
BEGIN
  DECLARE v_stat_date DATE DEFAULT CURDATE();
  DECLARE v_total_tokens INT DEFAULT p_input_tokens + p_output_tokens;
  DECLARE v_success_count INT DEFAULT IF(p_is_success, 1, 0);
  DECLARE v_error_count INT DEFAULT IF(p_is_success, 0, 1);
  
  -- 插入或更新每日统计
  INSERT INTO ai_usage_stats (
    user_id, session_id, ai_provider, ai_model, operation_type,
    request_count, input_tokens, output_tokens, total_tokens,
    input_cost, output_cost, total_cost, 
    avg_response_time, min_response_time, max_response_time,
    success_count, error_count, stat_date, stat_period
  ) VALUES (
    p_user_id, p_session_id, p_ai_provider, p_ai_model, p_operation_type,
    1, p_input_tokens, p_output_tokens, v_total_tokens,
    0, 0, p_total_cost,
    p_response_time, p_response_time, p_response_time,
    v_success_count, v_error_count, v_stat_date, 'DAILY'
  ) ON DUPLICATE KEY UPDATE
    request_count = request_count + 1,
    input_tokens = input_tokens + p_input_tokens,
    output_tokens = output_tokens + p_output_tokens,
    total_tokens = total_tokens + v_total_tokens,
    total_cost = total_cost + p_total_cost,
    avg_response_time = (avg_response_time * request_count + p_response_time) / (request_count + 1),
    min_response_time = LEAST(IFNULL(min_response_time, p_response_time), p_response_time),
    max_response_time = GREATEST(IFNULL(max_response_time, p_response_time), p_response_time),
    success_count = success_count + v_success_count,
    error_count = error_count + v_error_count,
    success_rate = (success_count + v_success_count) * 100.0 / (request_count + 1),
    updated_at = NOW();
END//

-- 获取用户AI使用统计
CREATE PROCEDURE `GetUserAIStats`(
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
    AVG(avg_response_time) as avg_response_time,
    MIN(stat_date) as first_use_date,
    MAX(stat_date) as last_use_date
  FROM ai_usage_stats
  WHERE user_id = p_user_id
    AND stat_date BETWEEN p_start_date AND p_end_date
    AND stat_period = 'DAILY'
  GROUP BY ai_provider, ai_model, operation_type
  ORDER BY total_cost DESC, total_requests DESC;
END//

-- 清理过期数据
CREATE PROCEDURE `CleanupExpiredData`(
  IN p_days_to_keep INT DEFAULT 90
)
BEGIN
  DECLARE v_cutoff_date DATETIME DEFAULT DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY);
  
  -- 软删除过期的已删除会话
  UPDATE ai_chat_sessions 
  SET deleted_at = NOW()
  WHERE status = 'DELETED' 
    AND updated_at < v_cutoff_date
    AND deleted_at IS NULL;
  
  -- 清理过期的使用统计
  DELETE FROM ai_usage_stats 
  WHERE stat_date < DATE_SUB(CURDATE(), INTERVAL 365 DAY);
  
  -- 清理过期的模板使用记录
  DELETE FROM ai_template_usage 
  WHERE created_at < DATE_SUB(NOW(), INTERVAL 180 DAY);
  
  -- 清理过期的操作日志
  DELETE FROM ai_operation_logs 
  WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);
  
  SELECT 
    'cleanup_completed' as status,
    v_cutoff_date as cutoff_date,
    NOW() as cleanup_time;
END//

DELIMITER ;

-- =====================================================
-- 创建索引优化
-- =====================================================

-- 复合索引优化
ALTER TABLE `ai_chat_sessions` ADD INDEX `idx_user_status_activity` (`user_id`, `status`, `last_activity_at`);
ALTER TABLE `ai_chat_messages` ADD INDEX `idx_session_role_created` (`session_id`, `role`, `created_at`);
ALTER TABLE `ai_suggestions` ADD INDEX `idx_user_status_priority` (`user_id`, `status`, `priority`);
ALTER TABLE `ai_requirements_analysis` ADD INDEX `idx_user_type_status` (`user_id`, `analysis_type`, `status`);

-- =====================================================
-- 添加外键约束
-- =====================================================

-- 恢复外键检查并添加约束
SET FOREIGN_KEY_CHECKS = 1;

-- AI会话表外键
ALTER TABLE `ai_chat_sessions` 
ADD CONSTRAINT `fk_ai_chat_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

-- AI消息表外键
ALTER TABLE `ai_chat_messages` 
ADD CONSTRAINT `fk_ai_chat_messages_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE CASCADE,
ADD CONSTRAINT `fk_ai_chat_messages_parent` FOREIGN KEY (`parent_message_id`) REFERENCES `ai_chat_messages` (`id`) ON DELETE SET NULL;

-- AI建议表外键
ALTER TABLE `ai_suggestions` 
ADD CONSTRAINT `fk_ai_suggestions_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL;

-- AI需求分析表外键
ALTER TABLE `ai_requirements_analysis` 
ADD CONSTRAINT `fk_ai_requirements_analysis_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL;

-- AI模板使用记录外键
ALTER TABLE `ai_template_usage` 
ADD CONSTRAINT `fk_ai_template_usage_template` FOREIGN KEY (`template_id`) REFERENCES `ai_prompt_templates` (`id`) ON DELETE CASCADE,
ADD CONSTRAINT `fk_ai_template_usage_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL;

-- AI使用统计外键
ALTER TABLE `ai_usage_stats` 
ADD CONSTRAINT `fk_ai_usage_stats_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL;

-- AI文件存储外键
ALTER TABLE `ai_file_storage` 
ADD CONSTRAINT `fk_ai_file_storage_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL;

-- =====================================================
-- 验证和统计信息
-- =====================================================

-- 显示初始化完成信息
SELECT '✅ AI助手模块数据库初始化完成！' AS message, NOW() AS completed_at;

-- 统计信息
SELECT 
    'ai_model_configs