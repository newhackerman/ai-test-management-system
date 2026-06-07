-- =====================================================
-- AI助手模块基础数据脚本
-- 版本: 1.0
-- 创建时间: 2024-12-19
-- 说明: AI助手模块的基础数据和配置
-- =====================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- 1. 插入默认AI模型配置
-- =====================================================

-- OpenAI模型配置
INSERT INTO `ai_model_configs` (
    `provider`, `model_name`, `display_name`, `description`, `version`,
    `api_endpoint`, `max_tokens`, `temperature`, `top_p`, `frequency_penalty`, `presence_penalty`,
    `is_enabled`, `is_default`, `is_public`, `priority`,
    `daily_quota`, `monthly_quota`, `user_daily_quota`, `concurrent_limit`,
    `cost_per_input_token`, `cost_per_output_token`,
    `capabilities`, `supported_languages`, `use_cases`, `model_features`,
    `created_at`, `updated_at`
) VALUES 
-- GPT-4 Turbo
('openai', 'gpt-4-turbo', 'GPT-4 Turbo', '最新的GPT-4模型，具有更强的推理能力和更大的上下文窗口', '2024-04',
 'https://api.openai.com/v1/chat/completions', 128000, 0.7, 1.0, 0.0, 0.0,
 1, 1, 1, 100,
 10000, 300000, 1000, 10,
 0.00001000, 0.00003000,
 JSON_ARRAY('reasoning', 'coding', 'analysis', 'writing', 'math'),
 JSON_ARRAY('zh', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'ru'),
 JSON_ARRAY('complex_analysis', 'code_generation', 'document_writing', 'problem_solving'),
 JSON_OBJECT('context_window', 128000, 'multimodal', false, 'function_calling', true),
 NOW(), NOW()),

-- GPT-4
('openai', 'gpt-4', 'GPT-4', '高质量的大语言模型，适合复杂任务', '2024-03',
 'https://api.openai.com/v1/chat/completions', 8192, 0.7, 1.0, 0.0, 0.0,
 1, 0, 1, 90,
 8000, 240000, 800, 8,
 0.00003000, 0.00006000,
 JSON_ARRAY('reasoning', 'coding', 'analysis', 'writing'),
 JSON_ARRAY('zh', 'en', 'ja', 'ko', 'fr', 'de', 'es'),
 JSON_ARRAY('professional_writing', 'code_review', 'complex_reasoning'),
 JSON_OBJECT('context_window', 8192, 'multimodal', false, 'function_calling', true),
 NOW(), NOW()),

-- GPT-3.5 Turbo
('openai', 'gpt-3.5-turbo', 'GPT-3.5 Turbo', '快速响应的通用模型，适合日常对话', '2024-01',
 'https://api.openai.com/v1/chat/completions', 16385, 0.7, 1.0, 0.0, 0.0,
 1, 0, 1, 70,
 20000, 600000, 2000, 20,
 0.00000050, 0.00000150,
 JSON_ARRAY('conversation', 'qa', 'simple_coding', 'translation'),
 JSON_ARRAY('zh', 'en', 'ja', 'ko', 'fr', 'de', 'es'),
 JSON_ARRAY('daily_chat', 'quick_qa', 'simple_tasks'),
 JSON_OBJECT('context_window', 16385, 'multimodal', false, 'function_calling', true),
 NOW(), NOW()),

-- Anthropic Claude模型配置
('anthropic', 'claude-3-opus', 'Claude-3 Opus', 'Anthropic最强大的模型，擅长复杂推理和长文本处理', '2024-02',
 'https://api.anthropic.com/v1/messages', 200000, 0.7, 1.0, 0.0, 0.0,
 1, 0, 1, 95,
 5000, 150000, 500, 5,
 0.00001500, 0.00007500,
 JSON_ARRAY('reasoning', 'analysis', 'writing', 'research'),
 JSON_ARRAY('zh', 'en', 'ja', 'ko', 'fr', 'de'),
 JSON_ARRAY('academic_research', 'document_analysis', 'creative_writing'),
 JSON_OBJECT('context_window', 200000, 'multimodal', true, 'function_calling', false),
 NOW(), NOW()),

('anthropic', 'claude-3-sonnet', 'Claude-3 Sonnet', '平衡性能和成本的Claude模型', '2024-02',
 'https://api.anthropic.com/v1/messages', 200000, 0.7, 1.0, 0.0, 0.0,
 1, 0, 1, 80,
 8000, 240000, 800, 8,
 0.00000300, 0.00001500,
 JSON_ARRAY('conversation', 'coding', 'analysis', 'writing'),
 JSON_ARRAY('zh', 'en', 'ja', 'ko', 'fr'),
 JSON_ARRAY('code_review', 'content_creation', 'data_analysis'),
 JSON_OBJECT('context_window', 200000, 'multimodal', true, 'function_calling', false),
 NOW(), NOW()),

('anthropic', 'claude-3-haiku', 'Claude-3 Haiku', '快速响应的轻量级Claude模型', '2024-02',
 'https://api.anthropic.com/v1/messages', 200000, 0.7, 1.0, 0.0, 0.0,
 1, 0, 1, 60,
 15000, 450000, 1500, 15,
 0.00000025, 0.00000125,
 JSON_ARRAY('conversation', 'qa', 'simple_tasks'),
 JSON_ARRAY('zh', 'en', 'ja', 'ko'),
 JSON_ARRAY('quick_qa', 'simple_chat', 'basic_tasks'),
 JSON_OBJECT('context_window', 200000, 'multimodal', true, 'function_calling', false),
 NOW(), NOW()),

-- 百度文心一言
('baidu', 'ernie-4.0-turbo', '文心一言4.0 Turbo', '百度最新的大语言模型，中文理解能力强', '4.0',
 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro', 8192, 0.7, 1.0, 0.0, 0.0,
 1, 0, 1, 85,
 12000, 360000, 1200, 12,
 0.00000800, 0.00002000,
 JSON_ARRAY('chinese_understanding', 'conversation', 'writing', 'analysis'),
 JSON_ARRAY('zh', 'en'),
 JSON_ARRAY('chinese_content', 'local_culture', 'business_analysis'),
 JSON_OBJECT('context_window', 8192, 'multimodal', false, 'chinese_optimized', true),
 NOW(), NOW()),

-- 阿里通义千问
('aliyun', 'qwen-turbo', '通义千问-Turbo', '阿里云的大语言模型，适合企业级应用', '2024-01',
 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation', 8192, 0.7, 1.0, 0.0, 0.0,
 1, 0, 1, 75,
 15000, 450000, 1500, 15,
 0.00000200, 0.00000600,
 JSON_ARRAY('conversation', 'analysis', 'coding', 'translation'),
 JSON_ARRAY('zh', 'en'),
 JSON_ARRAY('enterprise_service', 'business_analysis', 'content_generation'),
 JSON_OBJECT('context_window', 8192, 'multimodal', false, 'enterprise_grade', true),
 NOW(), NOW());

-- =====================================================
-- 2. 插入默认提示词模板
-- =====================================================

-- 通用对话模板
INSERT INTO `ai_prompt_templates` (
    `name`, `title`, `description`, `content`, `category`, `subcategory`,
    `variables`, `default_values`, `use_cases`, `tags`,
    `visibility`, `owner_id`, `is_featured`, `is_verified`,
    `created_at`, `updated_at`
) VALUES 
-- 通用助手模板
('general_assistant', '通用AI助手', '适用于日常对话和问答的通用模板', 
 '你是一个专业的AI助手，请根据用户的问题提供准确、有用的回答。\n\n用户问题：{user_question}\n\n请提供详细的回答，如果需要可以包含步骤说明。',
 'general', 'conversation',
 JSON_ARRAY('user_question'),
 JSON_OBJECT('user_question', '请输入您的问题'),
 JSON_ARRAY('daily_chat', 'qa', 'general_help'),
 JSON_ARRAY('通用', '对话', '问答'),
 'PUBLIC', 1, 1, 1,
 NOW(), NOW()),

-- 代码生成模板
('code_generator', '代码生成助手', '用于生成各种编程语言代码的模板',
 '你是一个专业的编程助手，请根据以下要求生成高质量的代码：\n\n编程语言：{language}\n功能描述：{description}\n特殊要求：{requirements}\n\n请提供：\n1. 完整的代码实现\n2. 代码注释说明\n3. 使用示例\n4. 注意事项',
 'coding', 'generation',
 JSON_ARRAY('language', 'description', 'requirements'),
 JSON_OBJECT('language', 'Python', 'description', '请描述需要实现的功能', 'requirements', '无特殊要求'),
 JSON_ARRAY('code_generation', 'programming', 'development'),
 JSON_ARRAY('编程', '代码生成', '开发'),
 'PUBLIC', 1, 1, 1,
 NOW(), NOW()),

-- 测试用例生成模板
('test_case_generator', '测试用例生成器', '根据需求生成详细测试用例的模板',
 '你是一个专业的测试工程师，请根据以下需求生成完整的测试用例：\n\n需求描述：{requirement}\n功能模块：{module}\n测试类型：{test_type}\n\n请生成包含以下内容的测试用例：\n1. 测试用例标题\n2. 前置条件\n3. 测试步骤\n4. 预期结果\n5. 边界值测试\n6. 异常场景测试',
 'testing', 'test_case',
 JSON_ARRAY('requirement', 'module', 'test_type'),
 JSON_OBJECT('requirement', '请输入需求描述', 'module', '请输入功能模块', 'test_type', '功能测试'),
 JSON_ARRAY('test_generation', 'qa', 'testing'),
 JSON_ARRAY('测试', '用例生成', '质量保证'),
 'PUBLIC', 1, 1, 1,
 NOW(), NOW()),

-- 需求分析模板
('requirement_analyzer', '需求分析助手', '分析和优化需求文档的模板',
 '你是一个专业的需求分析师，请对以下需求进行详细分析：\n\n需求内容：{requirement_content}\n分析维度：{analysis_dimensions}\n\n请从以下角度进行分析：\n1. 需求完整性评估\n2. 需求清晰度分析\n3. 可行性评估\n4. 风险识别\n5. 改进建议\n\n请提供结构化的分析报告。',
 'analysis', 'requirement',
 JSON_ARRAY('requirement_content', 'analysis_dimensions'),
 JSON_OBJECT('requirement_content', '请输入需求内容', 'analysis_dimensions', '完整性,清晰度,可行性'),
 JSON_ARRAY('requirement_analysis', 'business_analysis', 'project_management'),
 JSON_ARRAY('需求分析', '业务分析', '项目管理'),
 'PUBLIC', 1, 1, 1,
 NOW(), NOW()),

-- 文档写作模板
('document_writer', '技术文档写作助手', '用于生成各类技术文档的模板',
 '你是一个专业的技术文档写作专家，请根据以下信息生成高质量的技术文档：\n\n文档类型：{doc_type}\n主题：{topic}\n目标读者：{audience}\n详细要求：{requirements}\n\n请生成包含以下结构的文档：\n1. 概述\n2. 详细内容\n3. 示例说明\n4. 注意事项\n5. 参考资料\n\n请确保文档结构清晰、内容准确、易于理解。',
 'writing', 'documentation',
 JSON_ARRAY('doc_type', 'topic', 'audience', 'requirements'),
 JSON_OBJECT('doc_type', 'API文档', 'topic', '请输入文档主题', 'audience', '开发人员', 'requirements', '请输入具体要求'),
 JSON_ARRAY('documentation', 'technical_writing', 'knowledge_management'),
 JSON_ARRAY('文档写作', '技术文档', '知识管理'),
 'PUBLIC', 1, 1, 1,
 NOW(), NOW()),

-- 代码审查模板
('code_reviewer', '代码审查助手', '用于代码质量审查和改进建议的模板',
 '你是一个资深的代码审查专家，请对以下代码进行全面审查：\n\n编程语言：{language}\n代码内容：\n```{language}\n{code_content}\n```\n\n审查重点：{review_focus}\n\n请从以下方面进行审查：\n1. 代码质量和规范\n2. 性能优化建议\n3. 安全性检查\n4. 可维护性评估\n5. 最佳实践建议\n\n请提供具体的改进建议和修改后的代码示例。',
 'coding', 'review',
 JSON_ARRAY('language', 'code_content', 'review_focus'),
 JSON_OBJECT('language', 'python', 'code_content', '请粘贴需要审查的代码', 'review_focus', '代码质量,性能,安全性'),
 JSON_ARRAY('code_review', 'quality_assurance', 'best_practices'),
 JSON_ARRAY('代码审查', '质量保证', '最佳实践'),
 'PUBLIC', 1, 1, 1,
 NOW(), NOW());

-- =====================================================
-- 3. 创建示例会话和消息（用于演示）
-- =====================================================

-- 注意：这里假设用户ID为1的用户存在，实际部署时需要根据实际用户数据调整
-- 如果没有用户数据，可以注释掉这部分

/*
-- 创建示例会话
INSERT INTO `ai_chat_sessions` (
    `title`, `user_id`, `status`, `ai_provider`, `ai_model`,
    `message_count`, `total_tokens`, `last_activity_at`,
    `created_at`, `updated_at`
) VALUES 
('AI助手功能测试', 1, 'ACTIVE', 'openai', 'gpt-4-turbo',
 2, 150, NOW(),
 NOW(), NOW()),
 
('代码生成示例', 1, 'ACTIVE', 'openai', 'gpt-3.5-turbo',
 4, 320, NOW(),
 NOW(), NOW());

-- 创建示例消息
INSERT INTO `ai_chat_messages` (
    `session_id`, `role`, `content`, `content_type`,
    `ai_provider`, `ai_model`, `tokens_used`,
    `created_at`, `updated_at`
) VALUES 
-- 第一个会话的消息
(1, 'USER', '你好，请介绍一下AI助手的主要功能', 'TEXT',
 NULL, NULL, 0,
 NOW(), NOW()),
 
(1, 'ASSISTANT', '您好！我是AI助手，主要功能包括：\n\n1. **智能对话**：提供自然语言交互\n2. **代码生成**：根据需求生成各种编程语言代码\n3. **测试用例生成**：自动生成测试用例\n4. **需求分析**：分析和优化需求文档\n5. **文档写作**：生成技术文档\n6. **代码审查**：提供代码质量改进建议\n\n有什么具体需要帮助的吗？', 'MARKDOWN',
 'openai', 'gpt-4-turbo', 150,
 NOW(), NOW()),

-- 第二个会话的消息
(2, 'USER', '请帮我生成一个Python函数，用于计算斐波那契数列', 'TEXT',
 NULL, NULL, 0,
 NOW(), NOW()),
 
(2, 'ASSISTANT', '好的，我来为您生成一个计算斐波那契数列的Python函数：\n\n```python\ndef fibonacci(n):\n    """\n    计算斐波那契数列的第n项\n    \n    Args:\n        n (int): 要计算的项数（从0开始）\n    \n    Returns:\n        int: 斐波那契数列的第n项\n    \n    Raises:\n        ValueError: 当n为负数时抛出异常\n    """\n    if n < 0:\n        raise ValueError("n必须为非负整数")\n    elif n <= 1:\n        return n\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)\n\n# 使用示例\nif __name__ == "__main__":\n    # 计算前10项斐波那契数列\n    for i in range(10):\n        print(f"fibonacci({i}) = {fibonacci(i)}")\n```\n\n这个函数使用递归方法实现，简洁易懂。如果需要处理大数值，建议使用动态规划优化版本。', 'MARKDOWN',
 'openai', 'gpt-3.5-turbo', 180,
 NOW(), NOW());
*/

-- =====================================================
-- 4. 插入AI使用统计示例数据
-- =====================================================

-- 注意：这里创建的是示例统计数据，实际使用中应该由系统自动生成

/*
INSERT INTO `ai_usage_stats` (
    `user_id`, `ai_provider`, `ai_model`, `operation_type`,
    `request_count`, `input_tokens`, `output_tokens`, `total_tokens`,
    `input_cost`, `output_cost`, `total_cost`,
    `success_count`, `error_count`, `success_rate`,
    `stat_date`, `stat_period`,
    `created_at`, `updated_at`
) VALUES 
-- 今日统计数据
(1, 'openai', 'gpt-4-turbo', 'CHAT',
 5, 200, 800, 1000,
 0.0020, 0.0240, 0.0260,
 5, 0, 1.0,
 CURDATE(), 'DAILY',
 NOW(), NOW()),

(1, 'openai', 'gpt-3.5-turbo', 'CHAT',
 10, 500, 1500, 2000,
 0.0025, 0.0225, 0.0250,
 10, 0, 1.0,
 CURDATE(), 'DAILY',
 NOW(), NOW()),

(1, 'anthropic', 'claude-3-sonnet', 'ANALYSIS',
 3, 300, 900, 1200,
 0.0009, 0.0135, 0.0144,
 3, 0, 1.0,
 CURDATE(), 'DAILY',
 NOW(), NOW());
*/

-- =====================================================
-- 5. 更新模型健康状态
-- =====================================================

-- 将所有模型标记为健康状态
UPDATE `ai_model_configs` 
SET `health_status` = 'HEALTHY', 
    `last_health_check` = NOW()
WHERE `is_enabled` = 1;

-- =====================================================
-- 验证数据插入
-- =====================================================

-- 检查插入的数据
SELECT 'AI模型配置' as table_name, COUNT(*) as record_count FROM ai_model_configs
UNION ALL
SELECT 'AI提示词模板' as table_name, COUNT(*) as record_count FROM ai_prompt_templates;

-- 显示各提供商的模型数量
SELECT provider, COUNT(*) as model_count, 
       SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled_count
FROM ai_model_configs 
GROUP BY provider;

-- 显示模板分类统计
SELECT category, COUNT(*) as template_count
FROM ai_prompt_templates 
GROUP BY category;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 显示初始化完成信息
SELECT 'AI助手模块基础数据初始化完成！' as message;
SELECT NOW() as completed_at;