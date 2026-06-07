import { useState, useCallback } from 'react';
import { message } from 'antd';
import { reportsApi } from '../services/api/reports';

interface UnifiedReport {
  id: string;
  name: string;
  type: 'generated' | 'imported';
  format: string;
  size: number;
  created_at: string;
  status: string;
  summary?: any;
}

interface ImportedReport {
  import_id: string;
  file_name: string;
  file_type: string;
  source_type: string;
  report_title?: string;
  summary_stats?: any;
  test_results_count: number;
  import_time: string;
}

interface Pagination {
  current: number;
  pageSize: number;
  total: number;
}

interface Filters {
  search?: string;
  report_type?: string;
  format_filter?: string;
}

interface SupportedFormats {
  generation_formats: string[];
  import_formats: string[];
  source_types: string[];
  report_types: string[];
}

export const useReports = () => {
  const [unifiedReports, setUnifiedReports] = useState<UnifiedReport[]>([]);
  const [importedReports, setImportedReports] = useState<ImportedReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState<Pagination>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [filters, setFilters] = useState<Filters>({});
  const [supportedFormats, setSupportedFormats] = useState<SupportedFormats>({
    generation_formats: [],
    import_formats: [],
    source_types: [],
    report_types: [],
  });
  const [analytics, setAnalytics] = useState<any>(null);

  // 获取统一报告列表
  const fetchUnifiedReports = useCallback(async (params?: any) => {
    setLoading(true);
    try {
      const response = await reportsApi.getUnifiedReports({
        page: pagination.current,
        page_size: pagination.pageSize,
        ...filters,
        ...params,
      });

      if (response.success) {
        setUnifiedReports(response.data);
        setPagination({
          current: response.page,
          pageSize: response.page_size,
          total: response.total,
        });
      }
    } catch (error) {
      console.error('Failed to fetch unified reports:', error);
      message.error('获取报告列表失败');
    } finally {
      setLoading(false);
    }
  }, [pagination.current, pagination.pageSize, filters]);

  // 获取导入报告列表
  const fetchImportedReports = useCallback(async (params?: any) => {
    setLoading(true);
    try {
      const response = await reportsApi.getImportedReports({
        page: 1,
        page_size: 50,
        ...params,
      });

      if (response.success) {
        setImportedReports(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch imported reports:', error);
      message.error('获取导入报告列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 导入报告
  const importReport = useCallback(async (formData: FormData) => {
    setLoading(true);
    try {
      const response = await reportsApi.importReport(formData);
      
      if (response.success) {
        message.success('报告导入成功');
        return response.data;
      } else {
        throw new Error(response.message || '导入失败');
      }
    } catch (error) {
      console.error('Failed to import report:', error);
      message.error('导入报告失败');
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // 生成报告
  const generateReport = useCallback(async (reportData: any) => {
    setLoading(true);
    try {
      const response = await reportsApi.generateReport(reportData);
      
      if (response.success) {
        message.success('报告生成成功');
        return response.data;
      } else {
        throw new Error(response.message || '生成失败');
      }
    } catch (error) {
      console.error('Failed to generate report:', error);
      message.error('生成报告失败');
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // 下载报告
  const downloadReport = useCallback(async (reportId: string, format: string) => {
    try {
      const response = await reportsApi.downloadReport(reportId, format);
      
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${reportId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      message.success('报告下载成功');
    } catch (error) {
      console.error('Failed to download report:', error);
      message.error('下载报告失败');
      throw error;
    }
  }, []);

  // 删除导入的报告
  const deleteImportedReport = useCallback(async (importId: string) => {
    setLoading(true);
    try {
      const response = await reportsApi.deleteImportedReport(importId);
      
      if (response.success) {
        message.success('报告删除成功');
        return true;
      } else {
        throw new Error(response.message || '删除失败');
      }
    } catch (error) {
      console.error('Failed to delete imported report:', error);
      message.error('删除报告失败');
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  // 获取导入报告详情
  const getImportedReportDetails = useCallback(async (importId: string) => {
    try {
      const response = await reportsApi.getImportedReportDetails(importId);
      
      if (response.success) {
        return response.data;
      } else {
        throw new Error(response.message || '获取详情失败');
      }
    } catch (error) {
      console.error('Failed to get imported report details:', error);
      message.error('获取报告详情失败');
      throw error;
    }
  }, []);

  // 获取导入报告的测试结果
  const getImportedReportTestResults = useCallback(async (
    importId: string,
    params: { page: number; page_size: number; status_filter?: string }
  ) => {
    try {
      const response = await reportsApi.getImportedReportTestResults(importId, params);
      
      if (response.success) {
        return response;
      } else {
        throw new Error(response.message || '获取测试结果失败');
      }
    } catch (error) {
      console.error('Failed to get test results:', error);
      message.error('获取测试结果失败');
      throw error;
    }
  }, []);

  // 获取支持的格式
  const fetchSupportedFormats = useCallback(async () => {
    try {
      const response = await reportsApi.getSupportedFormats();
      
      if (response.success) {
        setSupportedFormats(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch supported formats:', error);
    }
  }, []);

  // 获取分析数据
  const fetchAnalytics = useCallback(async (days: number = 30) => {
    try {
      const response = await reportsApi.getAnalytics(days);
      
      if (response.success) {
        setAnalytics(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    }
  }, []);

  // 更新过滤器
  const updateFilters = useCallback((newFilters: Partial<Filters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  // 更新分页
  const updatePagination = useCallback((newPagination: Partial<Pagination>) => {
    setPagination(prev => ({ ...prev, ...newPagination }));
  }, []);

  return {
    // 状态
    unifiedReports,
    importedReports,
    loading,
    pagination,
    filters,
    supportedFormats,
    analytics,

    // 方法
    fetchUnifiedReports,
    fetchImportedReports,
    importReport,
    generateReport,
    downloadReport,
    deleteImportedReport,
    getImportedReportDetails,
    getImportedReportTestResults,
    fetchSupportedFormats,
    fetchAnalytics,
    updateFilters,
    updatePagination,
  };
};
