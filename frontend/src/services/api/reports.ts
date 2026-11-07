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
  source_filter?: string;
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
  generateReport: (data: GenerateReportRequest) =>
    apiClient.post('/reports/generate', data).then((response) => response.data),

  importReport: (formData: FormData) =>
    apiClient.post('/reports/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }).then((response) => response.data),

  getUnifiedReports: (params: UnifiedReportsParams) =>
    apiClient.get('/reports/unified', { params }).then((response) => response.data),

  getImportedReports: (params: ImportedReportsParams) =>
    apiClient.get('/reports/imported', { params }).then((response) => response.data),

  getImportedReportDetails: (importId: string) =>
    apiClient.get(`/reports/imported/${importId}`).then((response) => response.data),

  getImportedReportTestResults: (importId: string, params: TestResultsParams) =>
    apiClient.get(`/reports/imported/${importId}/test-results`, { params }).then((response) => response.data),

  downloadReport: (reportId: string, format: string) =>
    apiClient.get(`/reports/download/${reportId}/${format}`, {
      responseType: 'blob',
    }).then((response) => response.data),

  downloadImportedReport: (importId: string) =>
    apiClient.get(`/reports/imported/${importId}/download`, {
      responseType: 'blob',
    }).then((response) => response.data),

  previewReport: (reportId: string, format: string) =>
    apiClient.get(`/reports/preview/${reportId}/${format}`, {
      responseType: 'text',
    }).then((response) => response.data),

  deleteGeneratedReport: (reportId: string) =>
    apiClient.delete(`/reports/generated/${reportId}`).then((response) => response.data),

  deleteImportedReport: (importId: string) =>
    apiClient.delete(`/reports/imported/${importId}`).then((response) => response.data),

  getSupportedFormats: () =>
    apiClient.get('/reports/formats').then((response) => response.data),

  getAnalytics: (days: number = 30) =>
    apiClient.get('/reports/analytics', { params: { days } }).then((response) => response.data),
};
