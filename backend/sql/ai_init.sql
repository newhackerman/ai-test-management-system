-- =====================================================
-- AI助手模块完整初始化脚本 (ai_init.sql)
-- 版本: 2.0
-- 创建时间: 2024-09-07
-- 
-- 说明: 
-- 1. 基于AI助手模块任务文档的完整数据库初始化脚本
-- 2. 包含所有必需的表结构、索引、外键约束和基础数据
-- 3. 与业务模型保持一致，支持完整的AI助手功能
-- 4. 优化了索引设计，提升查询性能
-- 
-- 使用方法：
-- mysql -u root -p your_database_name < ai_init.sql
-- =====================================================

-- 设置字符集和基本配置
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
SET time_zone = '+08:00';

SELECT '开始AI助手模块数据库初始化...' AS message, NOW() AS start_time;

-- =====================================================
-- AI模型配置表 (ai_model_configs)
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_model_configs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `provider` varchar(50) NOT NULL COMMENT 'AI服务提供商',
  `model_name` varchar(100) NOT NULL COMMENT '模型名称',
  `display_name` varchar(200) NOT NULL COMMENT '显示名称',
  `description` text COMMENT '模型描述',
  `version` varchar(50) DEFAULT NULL COMMENT '模型版本',
  
  -- 连接配置
  `api_endpoint` varchar(500) DEFAULT NULL COMMENT 'API端点URL',
  `api_key` varchar(500) DEFAULT NULL COMMENT 'API密钥',
  `api_version` varchar(50) DEFAULT NULL COMMENT 'API版本',
  `headers` json COMMENT '自定义请求头配置',
  
  -- 模型参数
  `max_tokens` int(11) NOT NULL DEFAULT 4000 COMMENT '最大Token数',
  `temperature` decimal(3,2) NOT NULL DEFAULT 0.70 COMMENT '温度参数',
  `top_p` decimal(3,2) NOT NULL DEFAULT 1.00 COMMENT 'Top-p参数',
  `frequency_penalty` decimal(3,2) NOT NULL DEFAULT 0.00 COMMENT '频率惩罚',
  `presence_penalty` decimal(3,2) NOT NULL DEFAULT 0.00 COMMENT '存在惩罚',
  `stop_sequences` json COMMENT '停止序列配置',
  
  -- 状态和权限
  `is_enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  `is_default` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为默认模型',
  `is_public` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否公开可用',
  `priority` int(11) NOT NULL DEFAULT 50 COMMENT '优先级',
  
  -- 配额和限制
  `daily_quota` int(11) DEFAULT NULL COMMENT '每日请求配额',
  `monthly_quota` int(11) DEFAULT NULL COMMENT '每月请求配额',
  `user_daily_quota` int(11) DEFAULT 100 COMMENT '用户每日配额',
  `concurrent_limit` int(11) DEFAULT 10 COMMENT '并发限制',
  `rate_limit` int(11) DEFAULT 60 COMMENT '每分钟请求限制',
  
  -- 成本配置
  `cost_per_input_token` decimal(10,8) DEFAULT 0.00000000 COMMENT '输入Token成本',
  `cost_per_output_token` decimal(10,8) DEFAULT 0.00000000 COMMENT '输出Token成本',
  `cost_per_request` decimal(8,4) DEFAULT 0.0000 COMMENT '每请求固定成本',
  
  -- 能力标签
  `capabilities` json COMMENT '模型能力标签',
  `supported_languages` json COMMENT '支持的语言',
  `use_cases` json COMMENT '适用场景',
  `model_features` json COMMENT '模型特性标签',
  
  -- 健康状态和性能
  `health_status` enum('HEALTHY','DEGRADED','UNHEALTHY','UNKNOWN') DEFAULT 'UNKNOWN' COMMENT '健康状态',
  `last_health_check` datetime DEFAULT NULL COMMENT '最后健康检查时间',
  `avg_response_time` decimal(8,3) DEFAULT NULL COMMENT '平均响应时间',
  `success_rate` decimal(5,2) DEFAULT NULL COMMENT '成功率',
  
  -- 使用统计
  `total_requests` bigint(20) NOT NULL DEFAULT 0 COMMENT '总请求数',
  `total_tokens_used` bigint(20) NOT NULL DEFAULT 0 COMMENT '总Token使用量',
  `total_cost` decimal(12,4) NOT NULL DEFAULT 0.0000 COMMENT '总成本',
  `last_used_at` datetime DEFAULT NULL COMMENT '最后使用时间',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_provider_model` (`provider`, `model_name`),
  KEY `idx_provider` (`provider`),
  KEY `idx_enabled_public_priority` (`is_enabled`, `is_public`, `priority`),
  KEY `idx_health_status` (`health_status`),
  KEY `idx_is_default` (`is_default`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_last_used` (`last_used_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI模型配置表';

-- =====================================================
-- AI聊天会话表 (ai_chat_sessions)
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_chat_sessions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `title` varchar(200) NOT NULL DEFAULT '新对话' COMMENT '会话标题',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `project_id` bigint(20) DEFAULT NULL COMMENT '关联项目ID',
  `status` enum('ACTIVE','ARCHIVED','DELETED') NOT NULL DEFAULT 'ACTIVE' COMMENT '会话状态',
  `session_type` enum('CHAT','REQUIREMENT_ANALYSIS','SUGGESTION','TEST_GENERATION','REVIEW') DEFAULT 'CHAT' COMMENT '会话类型',
  
  -- AI配置
  `ai_provider` varchar(50) DEFAULT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) DEFAULT NULL COMMENT 'AI模型名称',
  `system_prompt` text COMMENT '系统提示词',
  `session_config` json COMMENT '会话配置参数',
  `temperature` decimal(3,2) DEFAULT NULL COMMENT '会话特定温度参数',
  
  -- 统计信息
  `message_count` int(11) NOT NULL DEFAULT 0 COMMENT '消息数量',
  `total_tokens` bigint(20) NOT NULL DEFAULT 0 COMMENT '总Token消耗',
  `total_cost` decimal(10,4) NOT NULL DEFAULT 0.0000 COMMENT '总成本',
  `last_activity_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '最后活动时间',
  
  -- 会话元数据
  `tags` json COMMENT '标签列表',
  `session_metadata` json COMMENT '会话元数据',
  `context_data` json COMMENT '上下文数据',
  
  -- 共享和访问控制
  `is_shared` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否共享',
  `share_token` varchar(64) DEFAULT NULL COMMENT '分享令牌',
  `share_expires_at` datetime DEFAULT NULL COMMENT '分享过期时间',
  `visibility` enum('PRIVATE','TEAM','PUBLIC') DEFAULT 'PRIVATE' COMMENT '可见性',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_project_id` (`project_id`),
  KEY `idx_status` (`status`),
  KEY `idx_session_type` (`session_type`),
  KEY `idx_ai_provider_model` (`ai_provider`, `ai_model`),
  KEY `idx_last_activity` (`last_activity_at`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_share_token` (`share_token`),
  KEY `idx_user_status_activity` (`user_id`, `status`, `last_activity_at`),
  CONSTRAINT `fk_ai_chat_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI聊天会话表';

-- =====================================================
-- AI聊天消息表 (ai_chat_messages)
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_chat_messages` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` bigint(20) NOT NULL COMMENT '会话ID',
  `role` enum('USER','ASSISTANT','SYSTEM') NOT NULL COMMENT '消息角色',
  `content` longtext NOT NULL COMMENT '消息内容',
  `content_type` enum('TEXT','MARKDOWN','CODE','IMAGE','FILE','JSON') DEFAULT 'TEXT' COMMENT '内容类型',
  
  -- AI相关信息
  `ai_provider` varchar(50) DEFAULT NULL COMMENT 'AI服务提供商',
  `ai_model` varchar(100) DEFAULT NULL COMMENT 'AI模型名称',
  `tokens_used` int(11) NOT NULL DEFAULT 0 COMMENT '消费的Token数',
  `cost` decimal(8,4) NOT NULL DEFAULT 0.0000 COMMENT '消息成本',
  `confidence_score` decimal(5,3) DEFAULT NULL COMMENT '置信度分数',
  `response_time` decimal(8,3) DEFAULT NULL COMMENT '响应时间',
  
  -- 消息状态和类型
  `message_type` enum('NORMAL','ERROR','SYSTEM','NOTIFICATION') DEFAULT 'NORMAL' COMMENT '消息类型',
  `is_streaming` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为流式消息',
  `is_error` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为错误消息',
  `error_code` varchar(50) DEFAULT NULL COMMENT '错误代码',
  `error_message` text COMMENT '错误详细信息',
  
  -- 消息关系和元数据
  `parent_message_id` bigint(20) DEFAULT NULL COMMENT '父消息ID',
  `thread_id` varchar(100) DEFAULT NULL COMMENT '线程ID',
  `message_metadata` json COMMENT '消息元数据',
  `attachments` json COMMENT '附件信息',
  
  -- 用户交互
  `user_rating` tinyint(4) DEFAULT NULL COMMENT '用户评分',
  `user_feedback` text COMMENT '用户反馈',
  `is_bookmarked` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否收藏',
  `is_regenerated` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否为重新生成',
  `regeneration_count` int(11) DEFAULT 0 COMMENT '重新生成次数',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  
  PRIMARY KEY (`id`),
  KEY `idx_session_id` (`session_id`),
  KEY `idx_role` (`role`),
  KEY `idx_content_type` (`content_type`),
  KEY `idx_ai_provider_model` (`ai_provider`, `ai_model`),
  KEY `idx_parent_message` (`parent_message_id`),
  KEY `idx_thread_id` (`thread_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_is_bookmarked` (`is_bookmarked`),
  KEY `idx_user_rating` (`user_rating`),
  KEY `idx_session_role_created` (`session_id`, `role`, `created_at`),
  CONSTRAINT `fk_ai_chat_messages_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ai_chat_messages_parent` FOREIGN KEY (`parent_message_id`) REFERENCES `ai_chat_messages` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI聊天消息表';

-- =====================================================
-- AI提示词模板表 (ai_prompt_templates)
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_prompt_templates` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(200) NOT NULL COMMENT '模板名称',
  `title` varchar(300) NOT NULL COMMENT '模板标题',
  `description` text COMMENT '模板描述',
  `content` longtext NOT NULL COMMENT '模板内容',
  `category` varchar(100) NOT NULL COMMENT '模板分类',
  `subcategory` varchar(100) DEFAULT NULL COMMENT '子分类',
  
  -- 模板配置
  `variables` json COMMENT '模板变量定义',
  `default_values` json COMMENT '变量默认值',
  `validation_rules` json COMMENT '变量验证规则',
  `example_context` json COMMENT '使用示例上下文',
  
  -- 适用性配置
  `supported_providers` json COMMENT '支持的AI提供商',
  `supported_models` json COMMENT '支持的模型',
  `use_cases` json COMMENT '使用场景标签',
  `tags` json COMMENT '标签列表',
  `language` varchar(10) DEFAULT 'zh-CN' COMMENT '模板语言',
  
  -- 权限和可见性
  `visibility` enum('PUBLIC','PRIVATE','TEAM','ORGANIZATION') DEFAULT 'PRIVATE' COMMENT '可见性',
  `owner_id` bigint(20) NOT NULL COMMENT '所有者ID',
  `team_id` bigint(20) DEFAULT NULL COMMENT '团队ID',
  `is_featured` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否精选',
  `is_verified` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否官方验证',
  `is_active` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
  
  -- 版本控制
  `version` varchar(20) NOT NULL DEFAULT '1.0.0' COMMENT '版本号',
  `parent_template_id` bigint(20) DEFAULT NULL COMMENT '父模板ID',
  `is_latest_version` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否为最新版本',
  `changelog` text COMMENT '版本更新日志',
  
  -- 使用统计
  `usage_count` int(11) NOT NULL DEFAULT 0 COMMENT '使用次数',
  `rating_avg` decimal(3,2) DEFAULT NULL COMMENT '平均评分',
  `rating_count` int(11) NOT NULL DEFAULT 0 COMMENT '评分次数',
  `last_used_at` datetime DEFAULT NULL COMMENT '最后使用时间',
  `download_count` int(11) DEFAULT 0 COMMENT '下载次数',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  
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
  KEY `idx_usage_rating` (`usage_count`, `rating_avg`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_ai_prompt_templates_parent` FOREIGN KEY (`parent_template_id`) REFERENCES `ai_prompt_templates` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI提示词模板表';

-- =====================================================
-- AI建议表 (ai_suggestions)
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_suggestions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '关联会话ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `project_id` bigint(20) DEFAULT NULL COMMENT '项目ID',
  `suggestion_type` enum('OPTIMIZATION','IMPROVEMENT','RISK_MITIGATION','BEST_PRACTICE','AUTOMATION','CODE_REVIEW') NOT NULL COMMENT '建议类型',
  `category` varchar(100) NOT NULL COMMENT '建议分类',
  `subcategory` varchar(100) DEFAULT NULL COMMENT '子分类',
  
  -- 建议内容
  `title` varchar(300) NOT NULL COMMENT '建议标题',
  `description` text NOT NULL COMMENT '建议详细描述',
  `rationale` text COMMENT '建议理由和分析',
  `expected_benefit` text COMMENT '预期收益说明',
  `implementation_guide` text COMMENT '实施指南',
  `estimated_effort` varchar(100) COMMENT '预估工作量',
  `estimated_impact` varchar(100) COMMENT '预估影响程度',
  
  -- 优先级和评分
  `priority` enum('LOW','MEDIUM','HIGH','CRITICAL') DEFAULT 'MEDIUM' COMMENT '优先级',
  `status` enum('PENDING','ACCEPTED','REJECTED','IMPLEMENTED','CANCELLED','IN_PROGRESS') DEFAULT 'PENDING' COMMENT '处理状态',
  `confidence_score` decimal(5,3) DEFAULT NULL COMMENT '置信度分数',
  `impact_score` decimal(5,3) DEFAULT NULL COMMENT '影响分数',
  `feasibility_score` decimal(5,3) DEFAULT NULL COMMENT '可行性分数',
  
  -- 上下文和分析数据
  `context_data` json COMMENT '上下文数据',
  `analysis_data` json COMMENT '分析结果数据',
  `metrics_before` json COMMENT '实施前指标快照',
  `metrics_after` json COMMENT '实施后指标对比',
  `risk_assessment` json COMMENT '风险评估',
  
  -- 关联信息
  `related_requirements` json COMMENT '相关需求ID列表',
  `related_test_cases` json COMMENT '相关测试用例ID列表',
  `related_issues` json COMMENT '相关问题ID列表',
  `related_suggestions` json COMMENT '相关建议ID列表',
  
  -- 用户反馈和处理
  `user_rating` tinyint(4) DEFAULT NULL COMMENT '用户评分',
  `user_feedback` text COMMENT '用户反馈',
  `implementation_notes` text COMMENT '实施备注',
  `rejection_reason` text COMMENT '拒绝原因',
  `assigned_to` bigint(20) DEFAULT NULL COMMENT '指派给用户ID',
  
  -- 时间信息
  `suggested_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '建议生成时间',
  `accepted_at` datetime DEFAULT NULL COMMENT '接受时间',
  `implemented_at` datetime DEFAULT NULL COMMENT '实施完成时间',
  `expires_at` datetime DEFAULT NULL COMMENT '建议过期时间',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  
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
  KEY `idx_assigned_to` (`assigned_to`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_user_status_priority` (`user_id`, `status`, `priority`),
  CONSTRAINT `fk_ai_suggestions_session` FOREIGN KEY (`session_id`) REFERENCES `ai_chat_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI智能建议表';

-- =====================================================
-- AI需求分析表 (ai_requirements_analysis)
-- =====================================================

CREATE TABLE IF NOT EXISTS `ai_requirements_analysis` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` bigint(20) DEFAULT NULL COMMENT '关联会话ID',
  `user_id` bigint(20) NOT NULL COMMENT '用户ID',
  `project_id` bigint(20) DEFAULT NULL COMMENT '项目ID',
  `analysis_name` varchar(200) NOT NULL COMMENT '分析任务名称',
  `analysis_type` enum('QUALITY','COVERAGE','COMPLETENESS','CONSISTENCY','TRACEABILITY','FEASIBILITY') NOT NULL COMMENT '分析类型',
  
  -- 分析结果评分
  `overall_score` decimal(5,3) DEFAULT NULL COMMENT '总体评分',
  `completeness_score` decimal(5,3) DEFAULT NULL COMMENT '完整性评分',
  `clarity_score` decimal(5,3) DEFAULT NULL COMMENT '清晰度评分',
  `consistency_score` decimal(5,3) DEFAULT NULL COMMENT '一致性评分',
  `testability_score` decimal(5,3) DEFAULT NULL COMMENT '可测试性评分',
  `feasibility_score` decimal(5,3) DEFAULT NULL COMMENT '可行性评分',
  
  -- 分析详情
  `analysis_summary` text COMMENT '分析结果摘要',
  `key_findings` json COMMENT '关键发现列表',
  `recommendations` json COMMENT '改进建议列表',
  `risk_assessment` json COMMENT '风险评估结果',
  `improvement_plan` json COMMENT '改进计划',
  
  -- 需求统计
  `total_requirements` int(11) DEFAULT 0 COMMENT '需求总数',
  `analyzed_requirements` int(11) DEFAULT 0 COMMENT '已分析需求数',
  `problematic_requirements` json COMMENT '问题需求详情',
  `missing_requirements` json COMMENT '缺失需求分析',
  `duplicate_requirements` json COMMENT '重复需求检测',
  `orphan_requirements` json COMMENT '孤立需求检测',
  
  -- 覆盖度分析
  `functional_coverage` json COMMENT '功能需求覆盖度',
  `nonfunctional_coverage` json COMMENT '非功能需求覆盖度',
  `test_coverage_mapping` json COMMENT '测试覆盖度映射',
  `requirement_traceability` json COMMENT '需求可追溯性分析',
  
  -- 质量指标
  `quality_metrics` json COMMENT '质量度量指标',
  `compliance_check` json COMMENT '合规性检查结果',
  `standards_adherence` json COMMENT '标准遵循度',
  
  -- 分析状态和进度
  `status` enum('PENDING','IN_PROGRESS','COMPLETED','FAILED','CANCELLED') DEFAULT 'PENDING' COMMENT '分析状态',
  `progress` int(11) NOT NULL DEFAULT 0 COMMENT '分析进度',
  `error_message` text COMMENT '错误信息',
  `warning_messages` json COMMENT '警告信息列表',
  
  -- 配置参数
  `analysis_config` json COMMENT '分析配置参数',
  `ai_provider` varchar(50) DEFAULT NULL COMMENT '使用的AI提供商',
  `ai_model` varchar(100) DEFAULT NULL COMMENT '使用的AI模型',
  
  -- 时间信息
  `started_at` datetime DEFAULT NULL COMMENT '分析开始时间',
  `completed_at` datetime DEFAULT NULL COMMENT '分析完成时间',
  `analysis_duration` int(11) DEFAULT NULL COMMENT '分析耗时',
  
  -- 基础审计字段
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_by` bigint(20) DEFAULT NULL COMMENT '创建人ID',
  `updated_by` bigint(20) DEFAULT NULL COMMENT '更新人ID',
  `deleted_at` datetime DEFAULT NULL COMMENT '软删除时间',
  
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
-- AI使用统计表 (ai_usage_stats)
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
  `success_count` int(11)