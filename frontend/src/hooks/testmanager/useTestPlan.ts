// @ts-nocheck
import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { testPlanService } from '../../services/testmanager/testPlanService'
import type {
  CreateTestPlanRequest,
  TestPlanFilters,
  UpdateTestPlanRequest,
} from '../../types/testmanager'
import { useToast } from '../useToast'

const getErrorMessage = (error: any, fallback: string) => (
  error?.response?.data?.message || error?.message || fallback
)

export const useTestPlans = (filters?: TestPlanFilters) => {
  return useQuery({
    queryKey: ['testPlans', filters],
    queryFn: () => testPlanService.getTestPlans(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export const useTestPlan = (id: number) => {
  return useQuery({
    queryKey: ['testPlan', id],
    queryFn: () => testPlanService.getTestPlan(id),
    enabled: Number.isFinite(id) && id > 0,
  })
}

export const useTestPlanProgress = (id: number) => {
  return useQuery({
    queryKey: ['testPlanProgress', id],
    queryFn: () => testPlanService.getTestPlanProgress(id),
    enabled: Number.isFinite(id) && id > 0,
    refetchInterval: 30000,
  })
}

export const useCreateTestPlan = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateTestPlanRequest) => testPlanService.createTestPlan(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testPlans'] })
      toast({ title: '成功', description: '测试计划创建成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({
        title: '错误',
        description: getErrorMessage(error, '创建测试计划失败'),
        variant: 'destructive',
      })
    },
  })
}

export const useUpdateTestPlan = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateTestPlanRequest }) =>
      testPlanService.updateTestPlan(id, data),
    onSuccess: (data) => {
      queryClient.setQueryData(['testPlan', data.id], data)
      queryClient.invalidateQueries({ queryKey: ['testPlans'] })
      queryClient.invalidateQueries({ queryKey: ['testPlan', data.id] })
      toast({ title: '成功', description: '测试计划更新成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({
        title: '错误',
        description: getErrorMessage(error, '更新测试计划失败'),
        variant: 'destructive',
      })
    },
  })
}

export const useDeleteTestPlan = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: number) => testPlanService.deleteTestPlan(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testPlans'] })
      toast({ title: '成功', description: '测试计划删除成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({
        title: '错误',
        description: getErrorMessage(error, '删除测试计划失败'),
        variant: 'destructive',
      })
    },
  })
}

export const useUpdateTestPlanStatus = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      testPlanService.updateTestPlanStatus(id, status),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['testPlans'] })
      queryClient.invalidateQueries({ queryKey: ['testPlan', data.id] })
      toast({ title: '成功', description: '测试计划状态更新成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({
        title: '错误',
        description: getErrorMessage(error, '更新状态失败'),
        variant: 'destructive',
      })
    },
  })
}

export const useDuplicateTestPlan = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, newName }: { id: number; newName: string }) =>
      testPlanService.duplicateTestPlan(id, newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testPlans'] })
      toast({ title: '成功', description: '测试计划复制成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({
        title: '错误',
        description: getErrorMessage(error, '复制测试计划失败'),
        variant: 'destructive',
      })
    },
  })
}

export const useTestPlanTemplates = () => {
  return useQuery({
    queryKey: ['testPlanTemplates'],
    queryFn: () => testPlanService.getTestPlanTemplates(),
    staleTime: 10 * 60 * 1000,
  })
}

export const useExportTestPlan = () => {
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, format }: { id: number; format: string }) =>
      testPlanService.exportTestPlan(id, format),
    onSuccess: (blob, variables) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `test-plan-${variables.id}.${variables.format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast({ title: '成功', description: '测试计划导出成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({
        title: '错误',
        description: getErrorMessage(error, '导出测试计划失败'),
        variant: 'destructive',
      })
    },
  })
}

export const useTestPlanManagement = () => {
  const [selectedPlans, setSelectedPlans] = useState<number[]>([])
  const [filters, setFilters] = useState<TestPlanFilters>({})
  const [searchTerm, setSearchTerm] = useState('')

  const handleSelectPlan = useCallback((id: number) => {
    setSelectedPlans((prev) =>
      prev.includes(id) ? prev.filter((planId) => planId !== id) : [...prev, id]
    )
  }, [])

  const handleSelectAllPlans = useCallback((planIds: number[]) => {
    setSelectedPlans((prev) => (prev.length === planIds.length ? [] : planIds))
  }, [])

  const handleClearSelection = useCallback(() => {
    setSelectedPlans([])
  }, [])

  const handleUpdateFilters = useCallback((newFilters: Partial<TestPlanFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  const handleSearch = useCallback((term: string) => {
    setSearchTerm(term)
    setFilters((prev) => ({ ...prev, search: term }))
  }, [])

  return {
    selectedPlans,
    filters,
    searchTerm,
    handleSelectPlan,
    handleSelectAllPlans,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
  }
}
