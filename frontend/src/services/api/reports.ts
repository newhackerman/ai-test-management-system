import { apiClient } from './client';

export interface GenerateReportRequest {
  report_name: string;
  report_type: string;
  formats: string[];
  template_name?: string;
  include_charts?: boolean;
  include_details?: boolean;
  include_attachments?: boolean;
  custom_fields?: Record<string, any>;
  branding?: Record<string, string>;
  title: string;
  summary: Record<string, any>;
  sections: Array<Record<string, any>>;
  charts?: Array<Record<string, any>>;
  metadata?: Record<string, any>;
}

export interface UnifiedReportsParams {
  page?: number;
  page_size?: number;
  report_type?: string;
  format_filter?: string;
  test_plan_id?: number;
  search?: string;
}

export interface ImportedReportsParams {
  page?: number;
  page_size?: number;
  source_type?: string;
  search?: string;
}

export interface TestResultsParams {
  page: number;
  page_size: number;
  status_filter?: string;
}

export const reportsApi = {
  // 生成报告
  generateReport: (data: GenerateReportRequest) =>
    apiClient.post('/reports/generate', data).then(response => response.data),

  // 导入报告
  importReport: (formData: FormData) =>
    apiClient.post('/reports/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then(response => response.data),

  // 获取统一报告列表
  getUnifiedReports: (params: UnifiedReportsParams) =>
    apiClient.get('/reports/unified', { params }).then(response => response.data),

  // 获取导入报告列表
  getImportedReports: (params: ImportedReportsParams) =>
    apiClient.get('/reports/imported', { params }).then(response => response.data),

  // 获取导入报告详情
  getImportedReportDetails: (importId: string) =>
    apiClient.get(`/reports/imported/${importId}`).then(response => response.data),

  // 获取导入报告的测试结果
  getImportedReportTestResults: (importId: string, params: TestResultsParams) =>
    apiClient.get(`/reports/imported/${importId}/test-results`, { params }).then(response => response.data),

  // 下载报告
  downloadReport: (reportId: string, format: string) =>
    apiClient.get(`/reports/download/${reportId}/${format}`, {
      responseType: 'blob',
    }).then(response => response.data),

  // 删除导入的报告
  deleteImportedReport: (importId: string) =>
    apiClient.delete(`/reports/imported/${importId}`).then(response => response.data),

  // 获取支持的格式
  getSupportedFormats: () =>
    apiClient.get('/reports/formats').then(response => response.data),

  // 获取分析数据
  getAnalytics: (days: number = 30) =>
    apiClient.get('/reports/analytics', { params: { days } }).then(response => response.data),
};
