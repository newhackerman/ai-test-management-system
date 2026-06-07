/**
 * 提示词模板管理 Hook
 * 提供模板的状态管理和操作方法
 */
import { useState, useEffect, useCallback } from 'react';
import { useToast } from './useToast';
import { 
  PromptTemplate, 
  TemplateListResponse,
  TemplateSearchRequest,
  TemplateStatistics,
  promptTemplateService 
} from '@/services/prompt-template-service';

interface UsePromptTemplatesOptions {
  autoLoad?: boolean;
  pageSize?: number;
}

interface UsePromptTemplatesReturn {
  // 数据状态
  templates: PromptTemplate[];
  loading: boolean;
  error: string | null;
  
  // 分页信息
  currentPage: number;
  totalPages: number;
  totalCount: number;
  
  // 搜索和筛选
  searchQuery: string;
  selectedCategory: string;
  selectedVisibility: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  
  // 操作方法
  loadTemplates: () => Promise<void>;
  searchTemplates: (request: TemplateSearchRequest) => Promise<void>;
  getMyTemplates: (params?: any) => Promise<void>;
  createTemplate: (templateData: any) => Promise<PromptTemplate>;
  updateTemplate: (id: number, templateData: any) => Promise<PromptTemplate>;
  deleteTemplate: (id: number) => Promise<void>;
  renderTemplate: (id: number, context: Record<string, any>) => Promise<any>;
  recordUsage: (id: number, usageData: any) => Promise<void>;
  
  // 状态更新方法
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (category: string) => void;
  setSelectedVisibility: (visibility: string) => void;
  setSortBy: (field: string) => void;
  setSortOrder: (order: 'asc' | 'desc') => void;
  setCurrentPage: (page: number) => void;
  
  // 重置方法
  resetFilters: () => void;
  refresh: () => Promise<void>;
}

export function usePromptTemplates(options: UsePromptTemplatesOptions = {}): UsePromptTemplatesReturn {
  const { autoLoad = true, pageSize = 20 } = options;
  const { toast } = useToast();

  // 数据状态
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);

  // 搜索和筛选状态
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedVisibility, setSelectedVisibility] = useState('');
  const [sortBy, setSortBy] = useState('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // 加载模板列表
  const loadTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await promptTemplateService.getTemplates({
        query: searchQuery || undefined,
        category: selectedCategory || undefined,
        visibility: selectedVisibility || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page: currentPage,
        size: pageSize
      });

      setTemplates(response.templates);
      setTotalPages(response.pages);
      setTotalCount(response.total);
    } catch (err: any) {
      const errorMessage = err.message || '加载模板失败';
      setError(errorMessage);
      toast({
        title: '加载失败',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedCategory, selectedVisibility, sortBy, sortOrder, currentPage, pageSize, toast]);

  // 搜索模板
  const searchTemplates = useCallback(async (request: TemplateSearchRequest) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await promptTemplateService.searchTemplates(request);
      setTemplates(response.templates);
      setTotalPages(response.pages);
      setTotalCount(response.total);
    } catch (err: any) {
      const errorMessage = err.message || '搜索模板失败';
      setError(errorMessage);
      toast({
        title: '搜索失败',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // 获取用户模板
  const getMyTemplates = useCallback(async (params: any = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await promptTemplateService.getMyTemplates({
        ...params,
        page: currentPage,
        size: pageSize
      });

      setTemplates(response.templates);
      setTotalPages(response.pages);
      setTotalCount(response.total);
    } catch (err: any) {
      const errorMessage = err.message || '加载我的模板失败';
      setError(errorMessage);
      toast({
        title: '加载失败',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, toast]);

  // 创建模板
  const createTemplate = useCallback(async (templateData: any): Promise<PromptTemplate> => {
    try {
      const template = await promptTemplateService.createTemplate(templateData);
      
      toast({
        title: '创建成功',
        description: '模板已成功创建',
        variant: 'success'
      });
      
      // 刷新列表
      await loadTemplates();
      
      return template;
    } catch (err: any) {
      const errorMessage = err.message || '创建模板失败';
      toast({
        title: '创建失败',
        description: errorMessage,
        variant: 'destructive'
      });
      throw err;
    }
  }, [loadTemplates, toast]);

  // 更新模板
  const updateTemplate = useCallback(async (id: number, templateData: any): Promise<PromptTemplate> => {
    try {
      const template = await promptTemplateService.updateTemplate(id, templateData);
      
      toast({
        title: '更新成功',
        description: '模板已成功更新',
        variant: 'success'
      });
      
      // 更新本地状态
      setTemplates(prev => prev.map(t => t.id === id ? template : t));
      
      return template;
    } catch (err: any) {
      const errorMessage = err.message || '更新模板失败';
      toast({
        title: '更新失败',
        description: errorMessage,
        variant: 'destructive'
      });
      throw err;
    }
  }, [toast]);

  // 删除模板
  const deleteTemplate = useCallback(async (id: number): Promise<void> => {
    try {
      await promptTemplateService.deleteTemplate(id);
      
      toast({
        title: '删除成功',
        description: '模板已成功删除',
        variant: 'success'
      });
      
      // 更新本地状态
      setTemplates(prev => prev.filter(t => t.id !== id));
      setTotalCount(prev => prev - 1);
    } catch (err: any) {
      const errorMessage = err.message || '删除模板失败';
      toast({
        title: '删除失败',
        description: errorMessage,
        variant: 'destructive'
      });
      throw err;
    }
  }, [toast]);

  // 渲染模板
  const renderTemplate = useCallback(async (id: number, context: Record<string, any>) => {
    try {
      return await promptTemplateService.renderTemplate(id, context);
    } catch (err: any) {
      const errorMessage = err.message || '渲染模板失败';
      toast({
        title: '渲染失败',
        description: errorMessage,
        variant: 'destructive'
      });
      throw err;
    }
  }, [toast]);

  // 记录使用情况
  const recordUsage = useCallback(async (id: number, usageData: any): Promise<void> => {
    try {
      await promptTemplateService.recordUsage(id, usageData);
      
      // 更新本地使用计数
      setTemplates(prev => prev.map(t => 
        t.id === id ? { ...t, usage_count: t.usage_count + 1 } : t
      ));
    } catch (err: any) {
      console.error('Failed to record template usage:', err);
      // 不显示错误提示，因为这不是关键操作
    }
  }, []);

  // 重置筛选条件
  const resetFilters = useCallback(() => {
    setSearchQuery('');
    setSelectedCategory('');
    setSelectedVisibility('');
    setSortBy('updated_at');
    setSortOrder('desc');
    setCurrentPage(1);
  }, []);

  // 刷新数据
  const refresh = useCallback(async () => {
    await loadTemplates();
  }, [loadTemplates]);

  // 自动加载
  useEffect(() => {
    if (autoLoad) {
      loadTemplates();
    }
  }, [autoLoad, loadTemplates]);

  return {
    // 数据状态
    templates,
    loading,
    error,
    
    // 分页信息
    currentPage,
    totalPages,
    totalCount,
    
    // 搜索和筛选
    searchQuery,
    selectedCategory,
    selectedVisibility,
    sortBy,
    sortOrder,
    
    // 操作方法
    loadTemplates,
    searchTemplates,
    getMyTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    renderTemplate,
    recordUsage,
    
    // 状态更新方法
    setSearchQuery,
    setSelectedCategory,
    setSelectedVisibility,
    setSortBy,
    setSortOrder,
    setCurrentPage,
    
    // 重置方法
    resetFilters,
    refresh
  };
}

// 模板统计 Hook
export function useTemplateStatistics() {
  const [statistics, setStatistics] = useState<TemplateStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const loadStatistics = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const stats = await promptTemplateService.getStatistics();
      setStatistics(stats);
    } catch (err: any) {
      const errorMessage = err.message || '加载统计信息失败';
      setError(errorMessage);
      toast({
        title: '加载失败',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadStatistics();
  }, [loadStatistics]);

  return {
    statistics,
    loading,
    error,
    refresh: loadStatistics
  };
}

// 单个模板 Hook
export function usePromptTemplate(templateId: number | null) {
  const [template, setTemplate] = useState<PromptTemplate | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const loadTemplate = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    
    try {
      const templateData = await promptTemplateService.getTemplate(id);
      setTemplate(templateData);
    } catch (err: any) {
      const errorMessage = err.message || '加载模板失败';
      setError(errorMessage);
      toast({
        title: '加载失败',
        description: errorMessage,
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (templateId) {
      loadTemplate(templateId);
    } else {
      setTemplate(null);
      setError(null);
    }
  }, [templateId, loadTemplate]);

  return {
    template,
    loading,
    error,
    refresh: () => templateId ? loadTemplate(templateId) : Promise.resolve()
  };
}