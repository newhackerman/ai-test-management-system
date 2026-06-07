-- =====================================================
-- AI助手模块数据库表结构脚本
-- 版本: 1.0
-- 创建时间: 2024-12-19
-- 说明: AI助手模块相关的表结构定义
-- =====================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. AI聊天会话表 (ai_chat_sessions)
-- =====================================================
CREATE TABLE IF NOT EXISTS `ai_chat_sessions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `title` varchar(200) NOT NULL COMMENT '会话标题',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `status` enum('ACTIVE','ARCHIVED','DELETED') NOT NULL DEFAULT 'ACTIVE' COMMENT '会话状态',
  
  -- 会话配置
  `ai_provider` varchar(50) DEFAULT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) DEFAULT NULL COMMENT 'AI模型名称',
  `system_prompt` text COMMENT '系统提示词',
  `session_config` json COMMENT '会话配置参数',
  
  -- 统计信息
  `message_count` int(11) NOT NULL DEFAULT 0 COMMENT '消息数量',
  `total_tokens` int(11) NOT NULL DEFAULT 0 COMMENT '总Token数',
  `total_cost` decimal(10,4) NOT NULL DEFAULT 0.0000 COMMENT '总成本',
  `last_activity_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '最后活动时间',
  
  -- 会话元数据
  `tags` json COMMENT '标签列表',
  `session_metadata` json COMMENT '会话元数据',
  `is_shared` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否共享',
  `share_token` varchar(64) DEFAULT NULL COMMENT '分享令牌',
  `expires_at` datetime DEFAULT NULL COMMENT '过期时间',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_ai_provider` (`ai_provider`),
  KEY `idx_ai_model` (`ai_model`),
  KEY `idx_last_activity` (`last_activity_at`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_share_token` (`share_token`),
  KEY `idx_expires_at` (`expires_at`),
  CONSTRAINT `fk_ai_chat_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI聊天会话表';

-- =====================================================
-- 2. AI聊天消息表 (ai_chat_messages)
-- =====================================================
CREATE TABLE IF NOT EXISTS `ai_chat_messages` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` bigint(20) NOT NULL COMMENT '会话ID',
  `role` enum('USER','ASSISTANT','SYSTEM') NOT NULL COMMENT '消息角色',
  `content` longtext NOT NULL COMMENT '消息内容',
  `content_type` enum('TEXT','MARKDOWN','CODE','IMAGE','FILE') NOT NULL DEFAULT 'TEXT' COMMENT '内容类型',
  
  -- AI相关信息
  `ai_provider` varchar(50) DEFAULT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) DEFAULT NULL COMMENT 'AI模型名称',
  `tokens_used` int(11) NOT NULL DEFAULT 0 COMMENT '使用的Token数',
  `cost` decimal(8,4) NOT NULL DEFAULT 0.0000 COMMENT '消息成本',
  `confidence_score` float DEFAULT NULL COMMENT '置信度分数',
  `response_time` float DEFAULT NULL COMMENT '响应时间(秒)',
  
  -- 消息状态
  `is_streaming` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为流式消息',
  `is_error` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为错误消息',
  `error_code` varchar(50) DEFAULT NULL COMMENT '错误代码',
  `error_message` text COMMENT '错误信息',
  
  -- 消息元数据
  `message_metadata` json COMMENT '消息元数据',
  `parent_message_id` bigint(20) DEFAULT NULL COMMENT '父消息ID',
  `thread_id` varchar(100) DEFAULT NULL COMMENT '线程ID',
  
  -- 用户交互
  `user_rating` tinyint(4) DEFAULT NULL COMMENT '用户评分（1-5）',
  `user_feedback` text COMMENT '用户反馈',
  `is_bookmarked` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否收藏',
  `is_regenerated` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否重新生成',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_role` (`role`),
  KEY `idx_content_type` (`content_type`),
  KEY `idx_ai_provider` (`ai_provider`),
  KEY `idx_ai_model` (`ai_model`),
  KEY `idx_parent_message` (`parent_message_id`),
  KEY `idx_thread_id` (`thread_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_is_bookmarked` (`is_bookmarked`),
  CONSTRAINT `fk_ai_chat_messages_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ai_chat_messages_parent` FOREIGN KEY (`parent_message_id`) REFERENCES `ai_chat_messages` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI聊天消息表';

-- =====================================================
-- 3. AI模型配置表 (ai_model_configs)
-- =====================================================
CREATE TABLE IF NOT EXISTS `ai_model_configs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `provider` varchar(50) NOT NULL COMMENT 'AI服务提供商',
  `model_name` varchar(100) NOT NULL COMMENT '模型名称',
  `display_name` varchar(200) NOT NULL COMMENT '显示名称',
  `description` text COMMENT '模型描述',
  `version` varchar(50) DEFAULT NULL COMMENT '模型版本',
  
  -- 配置信息
  `api_endpoint` varchar(500) DEFAULT NULL COMMENT 'API端点',
  `api_key` varchar(500) DEFAULT NULL COMMENT 'API密钥',
  `api_version` varchar(50) DEFAULT NULL COMMENT 'API版本',
  `headers` json COMMENT '请求头配置',
  
  -- 模型参数
  `max_tokens` int(11) NOT NULL DEFAULT 4000 COMMENT '最大Token数',
  `temperature` float NOT NULL DEFAULT 0.7 COMMENT '温度参数',
  `top_p` float NOT NULL DEFAULT 1.0 COMMENT 'Top-p参数',
  `frequency_penalty` float NOT NULL DEFAULT 0.0 COMMENT '频率惩罚',
  `presence_penalty` float NOT NULL DEFAULT 0.0 COMMENT '存在惩罚',
  `stop_sequences` json COMMENT '停止序列',
  
  -- 状态和限制
  `is_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `is_default` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为默认模型',
  `is_public` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否公开可用',
  `priority` int(11) NOT NULL DEFAULT 0 COMMENT '优先级',
  
  -- 配额限制
  `daily_quota` int(11) DEFAULT NULL COMMENT '每日配额',
  `monthly_quota` int(11) DEFAULT NULL COMMENT '每月配额',
  `user_daily_quota` int(11) DEFAULT NULL COMMENT '用户每日配额',
  `concurrent_limit` int(11) DEFAULT 10 COMMENT '并发限制',
  
  -- 成本配置
  `cost_per_input_token` decimal(10,8) DEFAULT NULL COMMENT '输入Token成本',
  `cost_per_output_token` decimal(10,8) DEFAULT NULL COMMENT '输出Token成本',
  `cost_per_request` decimal(8,4) DEFAULT NULL COMMENT '每请求成本',
  
  -- 能力标签
  `capabilities` json COMMENT '模型能力标签',
  `supported_languages` json COMMENT '支持的语言',
  `use_cases` json COMMENT '适用场景',
  `model_features` json COMMENT '模型特性',
  
  -- 性能指标
  `avg_response_time` float DEFAULT NULL COMMENT '平均响应时间（秒）',
  `success_rate` float DEFAULT NULL COMMENT '成功率',
  `last_health_check` datetime DEFAULT NULL COMMENT '最后健康检查时间',
  `health_status` enum('HEALTHY','DEGRADED','UNHEALTHY','UNKNOWN') DEFAULT 'UNKNOWN' COMMENT '健康状态',
  
  -- 使用统计
  `total_requests` bigint(20) NOT NULL DEFAULT 0 COMMENT '总请求数',
  `total_tokens_used` bigint(20) NOT NULL DEFAULT 0 COMMENT '总Token使用量',
  `total_cost` decimal(12,4) NOT NULL DEFAULT 0.0000 COMMENT '总成本',
  `last_used_at` datetime DEFAULT NULL COMMENT '最后使用时间',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_provider_model` (`provider`, `model_name`),
  KEY `idx_provider` (`provider`),
  KEY `idx_is_enabled` (`is_enabled`),
  KEY `idx_is_default` (`is_default`),
  KEY `idx_is_public` (`is_public`),
  KEY `idx_priority` (`priority`),
  KEY `idx_health_status` (`health_status`),
  KEY `idx_last_health_check` (`last_health_check`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI模型配置表';

-- =====================================================
-- 4. AI提示词模板表 (ai_prompt_templates)
-- =====================================================
CREATE TABLE IF NOT EXISTS `ai_prompt_templates` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(200) NOT NULL COMMENT '模板名称',
  `title` varchar(300) NOT NULL COMMENT '模板标题',
  `description` text COMMENT '模板描述',
  `content` longtext NOT NULL COMMENT '模板内容',
  `category` varchar(100) DEFAULT NULL COMMENT '模板分类',
  `subcategory` varchar(100) DEFAULT NULL COMMENT '子分类',
  
  -- 模板配置
  `variables` json COMMENT '模板变量定义',
  `default_values` json COMMENT '默认值',
  `validation_rules` json COMMENT '验证规则',
  `example_context` json COMMENT '示例上下文',
  
  -- 适用性
  `supported_providers` json COMMENT '支持的AI提供商',
  `supported_models` json COMMENT '支持的模型',
  `use_cases` json COMMENT '使用场景',
  `tags` json COMMENT '标签',
  
  -- 权限和可见性
  `visibility` enum('PUBLIC','PRIVATE','TEAM','ORGANIZATION') NOT NULL DEFAULT 'PRIVATE' COMMENT '可见性',
  `owner_id` bigint(20) NOT NULL COMMENT '所有者ID',
  `team_id` bigint(20) DEFAULT NULL COMMENT '团队ID',
  `is_featured` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否精选',
  `is_verified` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否已验证',
  
  -- 版本控制
  `version` varchar(20) NOT NULL DEFAULT '1.0.0' COMMENT '版本号',
  `parent_template_id` bigint(20) DEFAULT NULL COMMENT '父模板ID',
  `is_latest_version` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否最新版本',
  
  -- 使用统计
  `usage_count` int(11) NOT NULL DEFAULT 0 COMMENT '使用次数',
  `rating_avg` float DEFAULT NULL COMMENT '平均评分',
  `rating_count` int(11) NOT NULL DEFAULT 0 COMMENT '评分次数',
  `last_used_at` datetime DEFAULT NULL COMMENT '最后使用时间',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name_owner` (`name`, `owner_id`),
  KEY `idx_category` (`category`),
  KEY `idx_subcategory` (`subcategory`),
  KEY `idx_visibility` (`visibility`),
  KEY `idx_owner_id` (`owner_id`),
  KEY `idx_team_id` (`team_id`),
  KEY `idx_is_featured` (`is_featured`),
  KEY `idx_is_verified` (`is_verified`),
  KEY `idx_parent_template` (`parent_template_id`),
  KEY `idx_usage_count` (`usage_count`),
  KEY `idx_rating_avg` (`rating_avg`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_ai_prompt_templates_parent` FOREIGN KEY (`parent_template_id`) REFERENCES `ai_prompt_templates` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI提示词模板表';

-- =====================================================
-- 5. AI建议表 (ai_suggestions)
-- =====================================================
CREATE TABLE IF NOT EXISTS `ai_suggestions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '关联会话ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `project_id` bigint(20) DEFAULT NULL COMMENT '项目ID',
  `suggestion_type` enum('OPTIMIZATION','IMPROVEMENT','RISK_MITIGATION','BEST_PRACTICE','AUTOMATION') NOT NULL COMMENT '建议类型',
  `category` varchar(100) NOT NULL COMMENT '建议分类',
  `subcategory` varchar(100) DEFAULT NULL COMMENT '子分类',
  
  -- 建议内容
  `title` varchar(300) NOT NULL COMMENT '建议标题',
  `description` text NOT NULL COMMENT '建议描述',
  `rationale` text COMMENT '建议理由',
  `expected_benefit` text COMMENT '预期收益',
  `implementation_guide` text COMMENT '实施指南',
  `estimated_effort` varchar(100) COMMENT '预估工作量',
  
  -- 优先级和状态
  `priority` enum('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM' COMMENT '优先级',
  `status` enum('PENDING','ACCEPTED','REJECTED','IMPLEMENTED','CANCELLED') NOT NULL DEFAULT 'PENDING' COMMENT '状态',
  `confidence_score` float DEFAULT NULL COMMENT '置信度分数',
  `impact_score` float DEFAULT NULL COMMENT '影响分数',
  
  -- 上下文信息
  `context_data` json COMMENT '上下文数据',
  `analysis_data` json COMMENT '分析数据',
  `metrics_before` json COMMENT '实施前指标',
  `metrics_after` json COMMENT '实施后指标',
  
  -- 用户反馈
  `user_rating` tinyint(4) DEFAULT NULL COMMENT '用户评分（1-5）',
  `user_feedback` text COMMENT '用户反馈',
  `implementation_notes` text COMMENT '实施备注',
  
  -- 关联信息
  `related_requirements` json COMMENT '相关需求ID列表',
  `related_test_cases` json COMMENT '相关测试用例ID列表',
  `related_issues` json COMMENT '相关问题ID列表',
  
  -- 时间信息
  `suggested_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '建议时间',
  `accepted_at` datetime DEFAULT NULL COMMENT '接受时间',
  `implemented_at` datetime DEFAULT NULL COMMENT '实施时间',
  `expires_at` datetime DEFAULT NULL COMMENT '过期时间',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_suggestion_type` (`suggestion_type`),
  KEY `idx_category` (`category`),
  KEY `idx_priority` (`priority`),
  KEY `idx_status` (`status`),
  KEY `idx_confidence_score` (`confidence_score`),
  KEY `idx_suggested_at` (`suggested_at`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_ai_suggestions_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI建议表';

-- =====================================================
-- 6. AI需求分析表 (ai_requirements_analysis)
-- =====================================================
CREATE TABLE IF NOT EXISTS `ai_requirements_analysis` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '关联会话ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `project_id` bigint(20) DEFAULT NULL COMMENT '项目ID',
  `analysis_name` varchar(200) NOT NULL COMMENT '分析名称',
  `analysis_type` enum('QUALITY','COVERAGE','COMPLETENESS','CONSISTENCY','TRACEABILITY') NOT NULL COMMENT '分析类型',
  
  -- 分析结果
  `overall_score` float DEFAULT NULL COMMENT '总体评分',
  `completeness_score` float DEFAULT NULL COMMENT '完整性评分',
  `clarity_score` float DEFAULT NULL COMMENT '清晰度评分',
  `consistency_score` float DEFAULT NULL COMMENT '一致性评分',
  `testability_score` float DEFAULT NULL COMMENT '可测试性评分',
  
  -- 分析详情
  `analysis_summary` text COMMENT '分析摘要',
  `key_findings` json COMMENT '关键发现',
  `recommendations` json COMMENT '改进建议',
  `risk_assessment` json COMMENT '风险评估',
  
  -- 问题识别
  `total_requirements` int(11) DEFAULT 0 COMMENT '需求总数',
  `problematic_requirements` json COMMENT '问题需求列表',
  `missing_requirements` json COMMENT '缺失需求列表',
  `duplicate_requirements` json COMMENT '重复需求列表',
  
  -- 覆盖度分析
  `functional_coverage` json COMMENT '功能覆盖度分析',
  `nonfunctional_coverage` json COMMENT '非功能需求覆盖度',
  `test_coverage_mapping` json COMMENT '测试覆盖度映射',
  
  -- 分析状态
  `status` enum('PENDING','IN_PROGRESS','COMPLETED','FAILED') NOT NULL DEFAULT 'PENDING' COMMENT '分析状态',
  `progress` int(11) NOT NULL DEFAULT 0 COMMENT '分析进度（0-100）',
  `error_message` text COMMENT '错误信息',
  
  -- 时间信息
  `started_at` datetime DEFAULT NULL COMMENT '开始时间',
  `completed_at` datetime DEFAULT NULL COMMENT '完成时间',
  `analysis_duration` int(11) DEFAULT NULL COMMENT '分析耗时（秒）',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_analysis_type` (`analysis_type`),
  KEY `idx_status` (`status`),
  KEY `idx_overall_score` (`overall_score`),
  KEY `idx_started_at` (`started_at`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_ai_requirements_analysis_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI需求分析表';

-- =====================================================
-- 7. AI使用统计表 (ai_usage_stats)
-- =====================================================
CREATE TABLE IF NOT EXISTS `ai_usage_stats` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '会话ID',
  `ai_provider` varchar(50) NOT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) NOT NULL COMMENT 'AI模型名称',
  `operation_type` enum('CHAT','SUGGESTION','ANALYSIS','TEMPLATE','OTHER') NOT NULL COMMENT '操作类型',
  
  -- 使用量统计
  `request_count` int(11) NOT NULL DEFAULT 1 COMMENT '请求次数',
  `input_tokens` int(11) NOT NULL DEFAULT 0 COMMENT '输入Token数',
  `output_tokens` int(11) NOT NULL DEFAULT 0 COMMENT '输出Token数',
  `total_tokens` int(11) NOT NULL DEFAULT 0 COMMENT '总Token数',
  
  -- 成本统计
  `input_cost` decimal(8,4) NOT NULL DEFAULT 0.0000 COMMENT '输入成本',
  `output_cost` decimal(8,4) NOT NULL DEFAULT 0.0000 COMMENT '输出成本',
  `total_cost` decimal(8,4) NOT NULL DEFAULT 0.0000 COMMENT '总成本',
  
  -- 性能统计
  `avg_response_time` float DEFAULT NULL COMMENT '平均响应时间（秒）',
  `success_count` int(11) NOT NULL DEFAULT 0 COMMENT '成功次数',
  `error_count` int(11) NOT NULL DEFAULT 0 COMMENT '错误次数',
  `success_rate` float DEFAULT NULL COMMENT '成功率',
  
  -- 时间维度
  `stat_date` date NOT NULL COMMENT '统计日期',
  `stat_hour` tinyint(4) DEFAULT NULL COMMENT '统计小时（0-23）',
  `stat_period` enum('HOURLY','DAILY','WEEKLY','MONTHLY') NOT NULL DEFAULT 'DAILY' COMMENT '统计周期',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_provider_model_date_hour` (`user_id`, `ai_provider`, `ai_model`, `stat_date`, `stat_hour`, `operation_type`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_ai_provider` (`ai_provider`),
  KEY `idx_ai_model` (`ai_model`),
  KEY `idx_operation_type` (`operation_type`),
  KEY `idx_stat_date` (`stat_date`),
  KEY `idx_stat_period` (`stat_period`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_ai_usage_stats_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI使用统计表';

-- =====================================================
-- 8. AI模板使用记录表 (ai_template_usage)
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
  `rendered_content` longtext COMMENT '渲染后内容',
  
  -- 使用结果
  `is_successful` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否成功',
  `error_message` text COMMENT '错误信息',
  `execution_time` float DEFAULT NULL COMMENT '执行时间（秒）',
  
  -- 用户反馈
  `user_rating` tinyint(4) DEFAULT NULL COMMENT '用户评分（1-5）',
  `user_feedback` text COMMENT '用户反馈',
  
  -- 基础字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_template_id` (`template_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_ai_provider` (`ai_provider`),
  KEY `idx_use_case` (`use_case`),
  KEY `idx_is_successful` (`is_successful`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_ai_template_usage_template` FOREIGN KEY (`template_id`) REFERENCES `ai_prompt_templates` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ai_template_usage_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI模板使用记录表';

-- =====================================================
-- 索引优化
-- =====================================================

-- 会话相关索引优化
ALTER TABLE `ai_chat_sessions` ADD INDEX `idx_user_status_activity` (`user_id`, `status`, `last_activity_at`);
ALTER TABLE `ai_chat_sessions` ADD INDEX `idx_provider_model_created` (`ai_provider`, `ai_model`, `created_at`);

-- 消息相关索引优化
ALTER TABLE `ai_chat_messages` ADD INDEX `idx_session_role_created` (`session_id`, `role`, `created_at`);
ALTER TABLE `ai_chat_messages` ADD INDEX `idx_provider_model_created` (`ai_provider`, `ai_model`, `created_at`);
ALTER TABLE `ai_chat_messages` ADD INDEX `idx_bookmarked_user` (`is_bookmarked`, `created_at`);

-- 模型配置索引优化
ALTER TABLE `ai_model_configs` ADD INDEX `idx_enabled_public_priority` (`is_enabled`, `is_public`, `priority`);
ALTER TABLE `ai_model_configs` ADD INDEX `idx_provider_enabled` (`provider`, `is_enabled`);

-- 模板相关索引优化
ALTER TABLE `ai_prompt_templates` ADD INDEX `idx_category_visibility_featured` (`category`, `visibility`, `is_featured`);
ALTER TABLE `ai_prompt_templates` ADD INDEX `idx_owner_visibility_created` (`owner_id`, `visibility`, `created_at`);
ALTER TABLE `ai_prompt_templates` ADD INDEX `idx_usage_rating` (`usage_count`, `rating_avg`);

-- 建议相关索引优化
ALTER TABLE `ai_suggestions` ADD INDEX `idx_user_status_priority` (`user_id`, `status`, `priority`);
ALTER TABLE `ai_suggestions` ADD INDEX `idx_type_category_created` (`suggestion_type`, `category`, `created_at`);
ALTER TABLE `ai_suggestions` ADD INDEX `idx_project_status_suggested` (`project_id`, `status`, `suggested_at`);

-- 分析相关索引优化
ALTER TABLE `ai_requirements_analysis` ADD INDEX `idx_user_type_status` (`user_id`, `analysis_type`, `status`);
ALTER TABLE `ai_requirements_analysis` ADD INDEX `idx_project_type_completed` (`project_id`, `analysis_type`, `completed_at`);

-- 统计相关索引优化
ALTER TABLE `ai_usage_stats` ADD INDEX `idx_date_provider_model` (`stat_date`, `ai_provider`, `ai_model`);
ALTER TABLE `ai_usage_stats` ADD INDEX `idx_user_date_period` (`user_id`, `stat_date`, `stat_period`);

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;