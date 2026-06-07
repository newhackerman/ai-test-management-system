/**
 * AI模型配置服务
 */
import { api } from './api';
import {
  AIModelConfig,
  AIModelConfigCreate,
  AIModelConfigUpdate,
  AIModelConfigList,
  AIProviderStats,
  AIModelHealthCheck,
  AIModelTestRequest,
  AIModelTestResponse,
  BatchHealthCheckResponse,
  AIProvider,
  AIModelConfigFilters
} from '../types/aiModelConfig';

export class AIModelConfigService {
  private baseUrl = '/api/ai-model-config';

  /**
   * 创建AI模型配置
   */
  async createModelConfig(data: AIModelConfigCreate): Promise<AIModelConfig> {
    return await api.post(this.baseUrl, data);
  }

  /**
   * 获取AI模型配置列表
   */
  async getModelConfigs(params?: {
    provider?: AIProvider;
    enabled_only?: boolean;
    public_only?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<AIModelConfigList> {
    return await api.get(this.baseUrl, { params });
  }

  /**
   * 获取AI服务提供商统计信息
   */
  async getProviderStats(): Promise<AIProviderStats[]> {
    return await api.get(`${this.baseUrl}/stats`);
  }

  /**
   * 获取单个AI模型配置
   */
  async getModelConfig(id: number): Promise<AIModelConfig> {
    return await api.get(`${this.baseUrl}/${id}`);
  }

  /**
   * 更新AI模型配置
   */
  async updateModelConfig(id: number, data: AIModelConfigUpdate): Promise<AIModelConfig> {
    return await api.put(`${this.baseUrl}/${id}`, data);
  }

  /**
   * 删除AI模型配置
   */
  async deleteModelConfig(id: number): Promise<void> {
    await api.delete(`${this.baseUrl}/${id}`);
  }

  /**
   * 检查AI模型健康状态
   */
  async healthCheckModel(id: number): Promise<AIModelHealthCheck> {
    return await api.post(`${this.baseUrl}/${id}/health-check`);
  }

  /**
   * 批量健康检查
   */
  async batchHealthCheck(): Promise<BatchHealthCheckResponse> {
    return await api.post(`${this.baseUrl}/batch-health-check`);
  }

  /**
   * 测试AI模型
   */
  async testModel(id: number, testRequest: AIModelTestRequest): Promise<AIModelTestResponse> {
    return await api.post(`${this.baseUrl}/${id}/test`, testRequest);
  }

  /**
   * 切换模型启用/禁用状态
   */
  async toggleModelStatus(id: number): Promise<AIModelConfig> {
    return await api.post(`${this.baseUrl}/${id}/toggle`);
  }

  /**
   * 设置为默认模型
   */
  async setDefaultModel(id: number): Promise<AIModelConfig> {
    return await api.post(`${this.baseUrl}/${id}/set-default`);
  }

  /**
   * 搜索和过滤模型配置
   */
  async searchModelConfigs(filters: AIModelConfigFilters, page = 1, pageSize = 20): Promise<AIModelConfigList> {
    const params = {
      ...filters,
      skip: (page - 1) * pageSize,
      limit: pageSize
    };

    return this.getModelConfigs(params);
  }
}

// 导出单例实例
export const aiModelConfigService = new AIModelConfigService();