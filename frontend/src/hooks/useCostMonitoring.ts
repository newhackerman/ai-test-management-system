import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  costMonitoringService, 
  DashboardData, 
  TrendsData, 
  StatisticsData,
  BudgetUsageData,
  QuotaUsageData,
  Alert,
  Budget,
  Quota
} from '@/services/cost-monitoring-service';
import { useToast } from '@/hooks/useToast';

export const useCostMonitoring = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Dashboard data query
  const useDashboardData = (period: string = 'daily') => {
    return useQuery({
      queryKey: ['cost-monitoring', 'dashboard', period],
      queryFn: () => costMonitoringService.getDashboardData(period),
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
    });
  };

  // Cost trends query
  const useCostTrends = (days: number = 30, provider?: string, userId?: number) => {
    return useQuery({
      queryKey: ['cost-monitoring', 'trends', days, provider, userId],
      queryFn: () => costMonitoringService.getCostTrends(days, provider, userId),
      staleTime: 10 * 60 * 1000, // 10 minutes
    });
  };

  // Usage statistics query
  const useUsageStatistics = (period: string = 'daily', groupBy: string = 'provider') => {
    return useQuery({
      queryKey: ['cost-monitoring', 'statistics', period, groupBy],
      queryFn: () => costMonitoringService.getUsageStatistics(period, groupBy),
      staleTime: 5 * 60 * 1000, // 5 minutes
    });
  };

  // Budget usage query
  const useBudgetUsage = (budgetId?: string) => {
    return useQuery({
      queryKey: ['cost-monitoring', 'budget-usage', budgetId],
      queryFn: () => costMonitoringService.getBudgetUsage(budgetId),
      staleTime: 2 * 60 * 1000, // 2 minutes
      refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
    });
  };

  // Quota usage query
  const useQuotaUsage = (quotaId?: string) => {
    return useQuery({
      queryKey: ['cost-monitoring', 'quota-usage', quotaId],
      queryFn: () => costMonitoringService.getQuotaUsage(quotaId),
      staleTime: 2 * 60 * 1000, // 2 minutes
      refetchInterval: 2 * 60 * 1000, // Auto-refresh every 2 minutes
    });
  };

  // Cost alerts query
  const useCostAlerts = (level?: string, limit: number = 100) => {
    return useQuery({
      queryKey: ['cost-monitoring', 'alerts', level, limit],
      queryFn: () => costMonitoringService.getCostAlerts(level, limit),
      staleTime: 1 * 60 * 1000, // 1 minute
      refetchInterval: 1 * 60 * 1000, // Auto-refresh every minute
    });
  };

  // Budgets query
  const useBudgets = () => {
    return useQuery({
      queryKey: ['cost-monitoring', 'budgets'],
      queryFn: () => costMonitoringService.getBudgets(),
      staleTime: 10 * 60 * 1000, // 10 minutes
    });
  };

  // Quotas query
  const useQuotas = () => {
    return useQuery({
      queryKey: ['cost-monitoring', 'quotas'],
      queryFn: () => costMonitoringService.getQuotas(),
      staleTime: 10 * 60 * 1000, // 10 minutes
    });
  };

  // Create budget mutation
  const useCreateBudget = () => {
    return useMutation({
      mutationFn: (budgetData: Partial<Budget>) => 
        costMonitoringService.createBudget(budgetData),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'budgets'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'budget-usage'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'dashboard'] });
        toast({
          title: "成功",
          description: "预算配置创建成功",
        });
      },
      onError: (error: any) => {
        toast({
          title: "错误",
          description: error.message || "创建预算配置失败",
          variant: "destructive",
        });
      },
    });
  };

  // Create quota mutation
  const useCreateQuota = () => {
    return useMutation({
      mutationFn: (quotaData: Partial<Quota>) => 
        costMonitoringService.createQuota(quotaData),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'quotas'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'quota-usage'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'dashboard'] });
        toast({
          title: "成功",
          description: "配额配置创建成功",
        });
      },
      onError: (error: any) => {
        toast({
          title: "错误",
          description: error.message || "创建配额配置失败",
          variant: "destructive",
        });
      },
    });
  };

  // Delete budget mutation
  const useDeleteBudget = () => {
    return useMutation({
      mutationFn: (budgetId: string) => 
        costMonitoringService.deleteBudget(budgetId),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'budgets'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'budget-usage'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'dashboard'] });
        toast({
          title: "成功",
          description: "预算配置删除成功",
        });
      },
      onError: (error: any) => {
        toast({
          title: "错误",
          description: error.message || "删除预算配置失败",
          variant: "destructive",
        });
      },
    });
  };

  // Delete quota mutation
  const useDeleteQuota = () => {
    return useMutation({
      mutationFn: (quotaId: string) => 
        costMonitoringService.deleteQuota(quotaId),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'quotas'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'quota-usage'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'dashboard'] });
        toast({
          title: "成功",
          description: "配额配置删除成功",
        });
      },
      onError: (error: any) => {
        toast({
          title: "错误",
          description: error.message || "删除配额配置失败",
          variant: "destructive",
        });
      },
    });
  };

  // Check cost limits mutation
  const useCheckCostLimits = () => {
    return useMutation({
      mutationFn: (checkData: {
        provider: string;
        estimated_cost: number;
        estimated_tokens?: number;
        user_id?: number;
      }) => costMonitoringService.checkCostLimits(checkData),
    });
  };

  // Record usage mutation
  const useRecordUsage = () => {
    return useMutation({
      mutationFn: (usageData: {
        provider: string;
        user_id?: number;
        input_tokens: number;
        output_tokens: number;
        cost: number;
        response_time: number;
        success?: boolean;
      }) => costMonitoringService.recordUsage(usageData),
      onSuccess: () => {
        // Invalidate relevant queries to refresh data
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'dashboard'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'trends'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'statistics'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'budget-usage'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'quota-usage'] });
      },
    });
  };

  // Clear alerts mutation
  const useClearAlerts = () => {
    return useMutation({
      mutationFn: (before?: string) => 
        costMonitoringService.clearAlerts(before),
      onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'alerts'] });
        queryClient.invalidateQueries({ queryKey: ['cost-monitoring', 'dashboard'] });
        toast({
          title: "成功",
          description: `成功清除 ${data.cleared_count} 条告警记录`,
        });
      },
      onError: (error: any) => {
        toast({
          title: "错误",
          description: error.message || "清除告警失败",
          variant: "destructive",
        });
      },
    });
  };

  // Refresh all data
  const refreshAllData = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['cost-monitoring'] });
  }, [queryClient]);

  return {
    // Queries
    useDashboardData,
    useCostTrends,
    useUsageStatistics,
    useBudgetUsage,
    useQuotaUsage,
    useCostAlerts,
    useBudgets,
    useQuotas,
    
    // Mutations
    useCreateBudget,
    useCreateQuota,
    useDeleteBudget,
    useDeleteQuota,
    useCheckCostLimits,
    useRecordUsage,
    useClearAlerts,
    
    // Utilities
    refreshAllData,
  };
};

// Individual hooks for specific use cases
export const useDashboardData = (period: string = 'daily') => {
  const { useDashboardData } = useCostMonitoring();
  return useDashboardData(period);
};

export const useCostTrends = (days: number = 30, provider?: string, userId?: number) => {
  const { useCostTrends } = useCostMonitoring();
  return useCostTrends(days, provider, userId);
};

export const useUsageStatistics = (period: string = 'daily', groupBy: string = 'provider') => {
  const { useUsageStatistics } = useCostMonitoring();
  return useUsageStatistics(period, groupBy);
};

export const useBudgetUsage = (budgetId?: string) => {
  const { useBudgetUsage } = useCostMonitoring();
  return useBudgetUsage(budgetId);
};

export const useQuotaUsage = (quotaId?: string) => {
  const { useQuotaUsage } = useCostMonitoring();
  return useQuotaUsage(quotaId);
};

export const useCostAlerts = (level?: string, limit: number = 100) => {
  const { useCostAlerts } = useCostMonitoring();
  return useCostAlerts(level, limit);
};

export const useBudgets = () => {
  const { useBudgets } = useCostMonitoring();
  return useBudgets();
};

export const useQuotas = () => {
  const { useQuotas } = useCostMonitoring();
  return useQuotas();
};