// @ts-nocheck
import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { defectService } from '../../services/testmanager/defectService'
import type { CreateDefectRequest, DefectFilters, UpdateDefectRequest } from '../../types/testmanager'
import { useToast } from '../useToast'

const getErrorMessage = (error: any, fallback: string) => (
  error?.response?.data?.message || error?.message || fallback
)

export const useDefects = (filters?: DefectFilters) => {
  return useQuery({
    queryKey: ['defects', filters],
    queryFn: () => defectService.getDefects(filters),
    staleTime: 30 * 1000,
  })
}

export const useDefect = (id: number) => {
  return useQuery({
    queryKey: ['defect', id],
    queryFn: () => defectService.getDefect(id),
    enabled: Number.isFinite(id) && id > 0,
  })
}

export const useDefectStatistics = (filters?: DefectFilters) => {
  return useQuery({
    queryKey: ['defectStatistics', filters],
    queryFn: () => defectService.getDefectStatistics(filters),
    staleTime: 60 * 1000,
  })
}

export const useDefectTrends = (timeRange = '30d') => {
  return useQuery({
    queryKey: ['defectTrends', timeRange],
    queryFn: () => defectService.getDefectTrends(timeRange),
    staleTime: 5 * 60 * 1000,
  })
}

export const useDefectTrendsWithFilters = (timeRange = '30d', filters?: DefectFilters) => {
  return useQuery({
    queryKey: ['defectTrends', timeRange, filters],
    queryFn: () => defectService.getDefectTrendsWithFilters(timeRange, filters),
    staleTime: 5 * 60 * 1000,
  })
}

export const useDefectComments = (id?: number) => {
  return useQuery({
    queryKey: ['defectComments', id],
    queryFn: () => defectService.getComments(id!),
    enabled: Number.isFinite(id) && Number(id) > 0,
    staleTime: 30 * 1000,
  })
}

export const useCreateDefect = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateDefectRequest) => defectService.createDefect(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defects'] })
      toast({ title: '成功', description: '缺陷创建成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '创建缺陷失败'), variant: 'destructive' })
    },
  })
}

export const useUpdateDefect = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateDefectRequest }) => defectService.updateDefect(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['defects'] })
      queryClient.invalidateQueries({ queryKey: ['defect', data.id] })
      toast({ title: '成功', description: '缺陷更新成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '更新缺陷失败'), variant: 'destructive' })
    },
  })
}

export const useDeleteDefect = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: number) => defectService.deleteDefect(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defects'] })
      toast({ title: '成功', description: '缺陷删除成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '删除缺陷失败'), variant: 'destructive' })
    },
  })
}

export const useUpdateDefectStatus = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, status, resolution, notes, fixed_in_version }: { id: number; status: string; resolution?: string; notes?: string; fixed_in_version?: string }) =>
      defectService.updateDefectStatusWithPayload(id, { status, resolution, notes, fixed_in_version }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['defects'] })
      queryClient.invalidateQueries({ queryKey: ['defect', data.id] })
      toast({ title: '成功', description: '缺陷状态更新成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '更新状态失败'), variant: 'destructive' })
    },
  })
}

export const useAddDefectComment = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, content }: { id: number; content: string }) => defectService.addComment(id, content),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['defectComments', variables.id] })
      toast({ title: '成功', description: '评论已添加', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '添加评论失败'), variant: 'destructive' })
    },
  })
}

export const useAssignDefect = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, assigneeId }: { id: number; assigneeId: number }) => defectService.assignDefect(id, assigneeId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['defects'] })
      queryClient.invalidateQueries({ queryKey: ['defect', data.id] })
      toast({ title: '成功', description: '缺陷分配成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '分配缺陷失败'), variant: 'destructive' })
    },
  })
}

export const useExportDefects = () => {
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ filters, format }: { filters?: DefectFilters; format: string }) =>
      defectService.exportDefects(filters, format),
    onSuccess: (blob, variables) => {
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `defects.${variables.format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast({ title: '成功', description: '缺陷数据导出成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '导出缺陷数据失败'), variant: 'destructive' })
    },
  })
}

export const useUploadAttachment = () => {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => defectService.uploadAttachment(id, file),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['defect', variables.id] })
      queryClient.invalidateQueries({ queryKey: ['defects'] })
      toast({ title: '成功', description: '附件上传成功', variant: 'success' })
    },
    onError: (error: any) => {
      toast({ title: '错误', description: getErrorMessage(error, '附件上传失败'), variant: 'destructive' })
    },
  })
}

export const useDefectManagement = () => {
  const [selectedDefects, setSelectedDefects] = useState<number[]>([])
  const [filters, setFilters] = useState<DefectFilters>({})
  const [searchTerm, setSearchTerm] = useState('')

  const handleSelectDefect = useCallback((id: number) => {
    setSelectedDefects((prev) =>
      prev.includes(id) ? prev.filter((defectId) => defectId !== id) : [...prev, id]
    )
  }, [])

  const handleSelectAllDefects = useCallback((defectIds: number[]) => {
    setSelectedDefects((prev) => (prev.length === defectIds.length ? [] : defectIds))
  }, [])

  const handleClearSelection = useCallback(() => setSelectedDefects([]), [])
  const handleUpdateFilters = useCallback((newFilters: Partial<DefectFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])
  const handleSearch = useCallback((term: string) => {
    setSearchTerm(term)
    setFilters((prev) => ({ ...prev, search: term }))
  }, [])

  return {
    selectedDefects,
    filters,
    searchTerm,
    handleSelectDefect,
    handleSelectAllDefects,
    handleClearSelection,
    handleUpdateFilters,
    handleSearch,
  }
}
