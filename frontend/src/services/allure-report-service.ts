/**
 * Allure报告服务
 * 
 * 提供Allure测试报告的生成、管理和查看功能
 */

import { apiClient } from '@/lib/api-client';

const unwrapApiResponse = <T>(response: unknown): T => {
  const payload = response as ApiResponse<T> | { data?: ApiResponse<T> | T };
  if (payload && typeof payload === 'object' && 'success' in payload && 'data' in payload) {
    return (payload as ApiResponse<T>).data;
  }

  const nested = (payload as { data?: ApiResponse<T> | T })?.data;
  if (nested && typeof nested === 'object' && 'success' in nested && 'data' in nested) {
    return (nested as ApiResponse<T>).data;
  }

  return nested as T;
};

export interface TestExecutionData {
  test_case_id: string;
  test_name: string;
  status: string;
  start_time: string;
  end_time: string;
  description?: string;
  error_message?: string;
  error_trace?: string;
  attachments?: Array<{
    name: string;
    content: string;
    type: string;
  }>;
  steps?: Array<{
    name: string;
    status: string;
    start_time: string;
    end_time: string;
  }>;
  labels?: Record<string, string>;
  links?: Array<{
    name: string;
    url: string;
    type: string;
  }>;
  environment?: string;
}

export interface AllureReportRequest {
  report_name: string;
  project_id?: number;
  test_plan_id?: number;
  test_execution_ids: number[];
  suite_name?: string;
  environment?: string;
  include_attachments?: boolean;
  auto_serve?: boolean;
  serve_port?: number;
}

export interface AllureReportFromDataRequest {
  report_name: string;
  test_executions: TestExecutionData[];
  project_id?: number;
  suite_name?: string;
  auto_serve?: boolean;
  serve_port?: number;
}

export interface AllureReportResponse {
  report_id: string;
  report_name: string;
  report_path: string;
  report_url?: string;
  status: string;
  generation_time: number;
  file_size: number;
  test_count: number;
  passed_count: number;
  failed_count: number;
  skipped_count: number;
  error_message?: string;
  created_at: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

class AllureReportService {
  private baseUrl = '/api/v1/reports/allure';

  /**
   * 生成Allure报告
   */
  async generateReport(request: AllureReportRequest): Promise<AllureReportResponse> {
    const response = await apiClient.post<ApiResponse<AllureReportResponse>>(
      `${this.baseUrl}/generate`,
      request
    );
    return unwrapApiResponse<AllureReportResponse>(response);
  }

  /**
   * 从测试数据生成Allure报告
   */
  async generateReportFromData(request: AllureReportFromDataRequest): Promise<AllureReportResponse> {
    const response = await apiClient.post<ApiResponse<AllureReportResponse>>(
      `${this.baseUrl}/generate-from-data`,
      request
    );
    return unwrapApiResponse<AllureReportResponse>(response);
  }

  /**
   * 获取Allure报告信息
   */
  async getReport(reportId: string): Promise<AllureReportResponse> {
    const response = await apiClient.get<ApiResponse<AllureReportResponse>>(
      `${this.baseUrl}/${reportId}`
    );
    return unwrapApiResponse<AllureReportResponse>(response);
  }

  /**
   * 启动Allure报告服务
   */
  async serveReport(reportId: string, port?: number): Promise<{ service_url: string }> {
    const response = await apiClient.post<ApiResponse<{ service_url: string }>>(
      `${this.baseUrl}/${reportId}/serve`,
      port ?? null
    );
    return unwrapApiResponse<{ service_url: string }>(response);
  }

  /**
   * 获取Allure报告列表
   */
  async listReports(): Promise<AllureReportResponse[]> {
    const response = await apiClient.get<ApiResponse<AllureReportResponse[]>>(
      this.baseUrl
    );
    return unwrapApiResponse<AllureReportResponse[]>(response) || [];
  }

  /**
   * 删除Allure报告
   */
  async deleteReport(reportId: string): Promise<boolean> {
    const response = await apiClient.delete<ApiResponse<boolean>>(
      `${this.baseUrl}/${reportId}`
    );
    return unwrapApiResponse<boolean>(response);
  }

}

export const allureReportService = new AllureReportService();
export default allureReportService;
