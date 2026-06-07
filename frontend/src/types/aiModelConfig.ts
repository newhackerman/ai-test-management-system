/**
 * AI模型配置相关类型定义
 */

export enum AIProvider {
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  BAIDU_WENXIN = 'baidu_wenxin',
  ALIYUN_TONGYI = 'aliyun_tongyi',
  GOOGLE_GEMINI = 'google_gemini',
  ZHIPU_CHATGLM = 'zhipu_chatglm',
  XUNFEI_XINGHUO = 'xunfei_xinghuo',
  CUSTOM = 'custom'
}

export enum HealthStatus {
  HEALTHY = 'HEALTHY',
  UNHEALTHY = 'UNHEALTHY',
  UNKNOWN = 'UNKNOWN',
  ERROR = 'ERROR'
}

export interface AIModelConfig {
  id: number;
  provider: AIProvider;
  model_name: string;
  display_name: string;
  description?: string;
  version?: string;
  
  // 配置信息
  api_endpoint?: string;
  api_key?: string;
  api_version?: string;
  headers?: Record<string, any>;
  
  // 模型参数
  max_tokens: number;
  temperature: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  stop_sequences?: string[];
  
  // 状态和限制
  is_enabled: boolean;
  is_default: boolean;
  is_public: boolean;
  priority: number;
  
  // 配额限制
  daily_quota?: number;
  monthly_quota?: number;
  user_daily_quota?: number;
  concurrent_limit: number;
  
  // 成本配置
  cost_per_input_token?: number;
  cost_per_output_token?: number;
  cost_per_request?: number;
  
  // 能力标签
  capabilities?: string[];
  supported_languages?: string[];
  use_cases?: string[];
  model_features?: Record<string, any>;
  
  // 性能指标
  avg_response_time?: number;
  success_rate?: number;
  last_health_check?: string;
  health_status?: HealthStatus;
  
  // 使用统计
  total_requests: number;
  total_tokens_used: number;
  total_cost: number;
  last_used_at?: string;
  
  // 时间戳
  created_at: string;
  updated_at: string;
}

export interface AIModelConfigCreate {
  provider: AIProvider;
  model_name: string;
  display_name: string;
  description?: string;
  version?: string;
  
  // 配置信息
  api_endpoint?: string;
  api_key?: string;
  api_version?: string;
  headers?: Record<string, any>;
  
  // 模型参数
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  stop_sequences?: string[];
  
  // 状态和限制
  is_enabled?: boolean;
  is_default?: boolean;
  is_public?: boolean;
  priority?: number;
  
  // 配额限制
  daily_quota?: number;
  monthly_quota?: number;
  user_daily_quota?: number;
  concurrent_limit?: number;
  
  // 成本配置
  cost_per_input_token?: number;
  cost_per_output_token?: number;
  cost_per_request?: number;
  
  // 能力标签
  capabilities?: string[];
  supported_languages?: string[];
  use_cases?: string[];
  model_features?: Record<string, any>;
}

export interface AIModelConfigUpdate {
  display_name?: string;
  description?: string;
  version?: string;
  
  // 配置信息
  api_endpoint?: string;
  api_key?: string;
  api_version?: string;
  headers?: Record<string, any>;
  
  // 模型参数
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  stop_sequences?: string[];
  
  // 状态和限制
  is_enabled?: boolean;
  is_default?: boolean;
  is_public?: boolean;
  priority?: number;
  
  // 配额限制
  daily_quota?: number;
  monthly_quota?: number;
  user_daily_quota?: number;
  concurrent_limit?: number;
  
  // 成本配置
  cost_per_input_token?: number;
  cost_per_output_token?: number;
  cost_per_request?: number;
  
  // 能力标签
  capabilities?: string[];
  supported_languages?: string[];
  use_cases?: string[];
  model_features?: Record<string, any>;
}

export interface AIModelConfigList {
  items: AIModelConfig[];
  total: number;
  skip: number;
  limit: number;
}

export interface AIProviderStats {
  provider: string;
  total_models: number;
  enabled_models: number;
  default_models: number;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_response_time: number;
}

export interface AIModelHealthCheck {
  status: HealthStatus;
  response_time?: number;
  error?: string;
  checked_at: string;
}

export interface AIModelTestRequest {
  test_message: string;
  use_custom_params?: boolean;
  custom_temperature?: number;
  custom_max_tokens?: number;
}

export interface AIModelTestResponse {
  success: boolean;
  response_text?: string;
  response_time: number;
  tokens_used?: number;
  cost?: number;
  error?: string;
  tested_at: string;
}

export interface BatchHealthCheckResponse {
  total: number;
  healthy: number;
  unhealthy: number;
  unknown: number;
  details: Array<{
    config_id: number;
    provider: string;
    model_name: string;
    status: string;
    response_time?: number;
    error?: string;
  }>;
  checked_at: string;
}

// 表单相关类型
export interface AIModelConfigFormData extends Omit<AIModelConfigCreate, 'capabilities' | 'supported_languages' | 'use_cases'> {
  capabilities: string;
  supported_languages: string;
  use_cases: string;
}

// 过滤器类型
export interface AIModelConfigFilters {
  provider?: AIProvider;
  enabled_only?: boolean;
  public_only?: boolean;
  search?: string;
}

// 排序类型
export interface AIModelConfigSort {
  field: keyof AIModelConfig;
  direction: 'asc' | 'desc';
}