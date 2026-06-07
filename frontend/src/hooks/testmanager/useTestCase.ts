// @ts-nocheck
import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { testCaseService } from '../../services/testmanager/testCaseService'
import type {
  AutomationConfig,
  CreateTestCaseRequest,
  TestCaseFilters,
  TestCaseGenerationConfig,
  UpdateTestCaseRequest,
} from '../../types/testmanager'
import { useToast } from '../useToast'

const getErrorMessage = (error: any, fallback: string) => (
  error?.response?.data?.message || error?.message || fallback
)

export const useTestCases = (filters?: TestCaseFilters) => {
  return useQuery({
    queryKey: ['testCases', filters],
    queryFn: () => testCaseService.getTestCases(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export const useTestCase = (id: number) => {
  return useQuery({
    queryKey: ['testCase', id],
    queryFn: () => testCaseService.getTestCase(id),
    enabled: Number.isFinite(id) && id > 0,
  })
}

export const useCreateTestCase = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateTestCaseRequest) => testCaseService.createTestCase(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      toast({ title: '成功', description: '测试用例创建成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '创建测试用例失败'), variant: 'destructive' })
    },
  })
}

export const useUpdateTestCase = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateTestCaseRequest }) =>
      testCaseService.updateTestCase(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      queryClient.invalidateQueries({ queryKey: ['testCase', data.id] })
      toast({ title: '成功', description: '测试用例更新成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '更新测试用例失败'), variant: 'destructive' })
    },
  })
}

export const useDeleteTestCase = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: number) => testCaseService.deleteTestCase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      toast({ title: '成功', description: '测试用例删除成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '删除测试用例失败'), variant: 'destructive' })
    },
  })
}

export const useDuplicateTestCase = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, newTitle }: { id: number; newTitle: string }) =>
      testCaseService.duplicateTestCase(id, newTitle),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      toast({ title: '成功', description: '测试用例复制成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '复制测试用例失败'), variant: 'destructive' })
    },
  })
}

export const useGenerateTestCases = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (config: TestCaseGenerationConfig) => testCaseService.generateTestCases(config),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      toast({ title: '成功', description: `成功生成 ${data.length} 个测试用例`, variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, 'AI 生成测试用例失败'), variant: 'destructive' })
    },
  })
}

export const useGenerateAutomationScript = () => {
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ testCaseId, config }: { testCaseId: number; config: AutomationConfig }) =>
      testCaseService.generateAutomationScript(testCaseId, config),
    onSuccess: () => {
      toast({ title: '成功', description: '自动化脚本生成成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '生成自动化脚本失败'), variant: 'destructive' })
    },
  })
}

export const useBatchUpdateTestCases = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ ids, data }: { ids: number[]; data: Partial<UpdateTestCaseRequest> }) =>
      testCaseService.batchUpdateTestCases(ids, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      toast({ title: '成功', description: '批量更新成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '批量更新失败'), variant: 'destructive' })
    },
  })
}

export const useBatchDeleteTestCases = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (ids: number[]) => testCaseService.batchDeleteTestCases(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      toast({ title: '成功', description: '批量删除成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '批量删除失败'), variant: 'destructive' })
    },
  })
}

export const useExportTestCases = () => {
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ filters, format }: { filters?: TestCaseFilters; format: string }) =>
      testCaseService.exportTestCases(filters, format),
    onSuccess: (blob, variables) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `test-cases.${variables.format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast({ title: '成功', description: '测试用例导出成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '导出测试用例失败'), variant: 'destructive' })
    },
  })
}

export const useImportTestCases = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ file, testPlanId }: { file: File; testPlanId?: number }) =>
      testCaseService.importTestCases(file, testPlanId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['testCases'] })
      toast({
        title: '导入完成',
        description: `成功导入 ${result?.success_count || 0} 个用例，失败 ${result?.failed_count || 0} 个`,
        variant: result?.failed_count > 0 ? 'destructive' : 'success',
      })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '导入测试用例失败'), variant: 'destructive' })
    },
  })
}

export const useTestCaseManagement = () => {
  const [selectedCases, setSelectedCases] = useState<number[]>([])
  const [filters, setFilters] = useState<TestCaseFilters>({})
  const [searchTerm, setSearchTerm] = useState('')

  const handleSelectCase = useCallback((id: number) => {
    setSelectedCases((prev) =>
      prev.includes(id) ? prev.filter((caseId) => caseId !== id) : [...prev, id]
    )
  }, [])

  const handleSelectAllCases = useCallback((caseIds: number[]) => {
    setSelectedCases((prev) => (prev.length === caseIds.length ? [] : caseIds))
  }, [])

  const handleClearSelection = useCallback(() => {
    setSelectedCases([])
  }, [])

  const handleUpdateFilters = useCallback((newFilters: Partial<TestCaseFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  const handleSearch = useCallback((term: string) => {
    setSearchTerm(term)
    setFilters((prev) => ({ ...prev, search: term }))
  }, [])

  return {
    selectedCases,
    filters,
    searchTerm,
    handleSelectCase,
    handleSelectAllCases,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
  }
}
