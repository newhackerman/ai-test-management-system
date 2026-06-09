// @ts-nocheck
import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AutomationExecutionRequest,
  CompleteExecutionRequest,
  ExecutionFilters,
  StartExecutionRequest,
  executionService,
} from '../../services/testmanager/executionService'
import { useToast } from '../useToast'

const getErrorMessage = (error: any, fallback: string) => (
  error?.response?.data?.detail ||
  error?.response?.data?.message ||
  error?.message ||
  fallback
)

export const useExecutions = (filters?: ExecutionFilters) => {
  return useQuery({
    queryKey: ['executions', filters],
    queryFn: () => executionService.getExecutions(filters),
    staleTime: 30 * 1000,
  })
}

export const useExecution = (id: number) => {
  return useQuery({
    queryKey: ['execution', id],
    queryFn: () => executionService.getExecution(id),
    enabled: Number.isFinite(id) && id > 0,
    refetchInterval: 5000,
  })
}

export const useExecutionLogs = (id: number) => {
  return useQuery({
    queryKey: ['executionLogs', id],
    queryFn: () => executionService.getExecutionLogs(id),
    enabled: Number.isFinite(id) && id > 0,
    refetchInterval: 2000,
  })
}

export const useExecutionStatistics = (filters?: ExecutionFilters) => {
  return useQuery({
    queryKey: ['executionStatistics', filters],
    queryFn: () => executionService.getExecutionStatistics(filters),
    staleTime: 60 * 1000,
  })
}

export const useStartManualExecution = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: StartExecutionRequest) => executionService.startManualExecution(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['executions'] })
      toast({ title: '成功', description: '测试执行已开始', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '开始执行失败'), variant: 'destructive' })
    },
  })
}

export const useCompleteExecution = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: CompleteExecutionRequest }) =>
      executionService.completeExecution(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['executions'] })
      queryClient.invalidateQueries({ queryKey: ['execution', data.id] })
      toast({ title: '成功', description: '测试执行已完成', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '完成执行失败'), variant: 'destructive' })
    },
  })
}

const useExecutionAction = (action: (id: number) => Promise<any>, successText: string, errorText: string) => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: number) => action(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['executions'] })
      if (data?.id) queryClient.invalidateQueries({ queryKey: ['execution', data.id] })
      toast({ title: '成功', description: successText, variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, errorText), variant: 'destructive' })
    },
  })
}

export const usePauseExecution = () =>
  useExecutionAction((id) => executionService.pauseExecution(id), '测试执行已暂停', '暂停执行失败')

export const useResumeExecution = () =>
  useExecutionAction((id) => executionService.resumeExecution(id), '测试执行已恢复', '恢复执行失败')

export const useCancelExecution = () =>
  useExecutionAction((id) => executionService.cancelExecution(id), '测试执行已取消', '取消执行失败')

export const useStartAutomationExecution = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: AutomationExecutionRequest) => executionService.startAutomationExecution(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['executions'] })
      queryClient.invalidateQueries({ queryKey: ['executionStatistics'] })
      toast({ title: '成功', description: '自动化执行已创建', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '启动自动化执行失败'), variant: 'destructive' })
    },
  })
}

export const useAutomationExecutionStatus = (executionId?: string) => {
  return useQuery({
    queryKey: ['automationExecution', executionId],
    queryFn: () => executionService.getAutomationExecutionStatus(executionId!),
    enabled: Boolean(executionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'RUNNING' || status === 'PENDING' ? 3000 : false
    },
  })
}

export const useCancelAutomationExecution = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (executionId: string) => executionService.cancelAutomationExecution(executionId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['automationExecution', data.execution_id] })
      queryClient.invalidateQueries({ queryKey: ['executions'] })
      queryClient.invalidateQueries({ queryKey: ['executionStatistics'] })
      toast({ title: '成功', description: '自动化执行已取消', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '取消自动化执行失败'), variant: 'destructive' })
    },
  })
}

export const useUploadScreenshot = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => executionService.uploadScreenshot(id, file),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['execution', variables.id] })
      toast({ title: '成功', description: '截图上传成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '截图上传失败'), variant: 'destructive' })
    },
  })
}

export const useUploadVideo = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => executionService.uploadVideo(id, file),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['execution', variables.id] })
      toast({ title: '成功', description: '执行录像上传成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '执行录像上传失败'), variant: 'destructive' })
    },
  })
}

export const useExecutionManagement = () => {
  const [selectedExecutions, setSelectedExecutions] = useState<number[]>([])
  const [filters, setFilters] = useState<ExecutionFilters>({})
  const [searchTerm, setSearchTerm] = useState('')

  const handleSelectExecution = useCallback((id: number) => {
    setSelectedExecutions((prev) =>
      prev.includes(id) ? prev.filter((executionId) => executionId !== id) : [...prev, id]
    )
  }, [])

  const handleSelectAllExecutions = useCallback((executionIds: number[]) => {
    setSelectedExecutions((prev) => (prev.length === executionIds.length ? [] : executionIds))
  }, [])

  const handleClearSelection = useCallback(() => setSelectedExecutions([]), [])

  const handleUpdateFilters = useCallback((newFilters: Partial<ExecutionFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  const handleSearch = useCallback((term: string) => {
    setSearchTerm(term)
    setFilters((prev) => ({ ...prev, search: term }))
  }, [])

  return {
    selectedExecutions,
    filters,
    searchTerm,
    handleSelectExecution,
    handleSelectAllExecutions,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
  }
}
