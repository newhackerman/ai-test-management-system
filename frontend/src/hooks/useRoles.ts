import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { roleService } from '@/services/role-service'
import type { Role, RoleFilters } from '@/types'
import { toast } from 'react-hot-toast'

// 查询键
export const ROLE_QUERY_KEYS = {
  all: ['roles'] as const,
  lists: () => [...ROLE_QUERY_KEYS.all, 'list'] as const,
  list: (filters: RoleFilters) => [...ROLE_QUERY_KEYS.lists(), filters] as const,
  details: () => [...ROLE_QUERY_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...ROLE_QUERY_KEYS.details(), id] as const,
}

// 获取所有角色hook
export const useAllRoles = () => {
  const { data: roles = [], isLoading } = useQuery({
    queryKey: ROLE_QUERY_KEYS.all,
    queryFn: () => roleService.getAllRoles(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  return {
    roles,
    isLoading
  }
}

// 角色列表hook
export const useRoles = (filters: RoleFilters = {}) => {
  const queryClient = useQueryClient()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ROLE_QUERY_KEYS.list(filters),
    queryFn: () => roleService.getRoles({ ...filters, size: filters.size || filters.pageSize }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // 创建角色
  const createMutation = useMutation({
    mutationFn: roleService.createRole,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ROLE_QUERY_KEYS.lists() })
      queryClient.invalidateQueries({ queryKey: ROLE_QUERY_KEYS.all })
      toast.success('角色创建成功')
    },
    onError: (error: any) => {
      toast.error(error.message || '创建角色失败')
    }
  })

  // 更新角色
  const updateMutation = useMutation({
    mutationFn: ({ roleId, data }: { roleId: string; data: any }) => 
      roleService.updateRole(roleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ROLE_QUERY_KEYS.lists() })
      queryClient.invalidateQueries({ queryKey: ROLE_QUERY_KEYS.all })
      toast.success('角色更新成功')
    },
    onError: (error: any) => {
      toast.error(error.message || '更新角色失败')
    }
  })

  // 删除角色
  const deleteMutation = useMutation({
    mutationFn: (roleId: string) => roleService.deleteRole(roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ROLE_QUERY_KEYS.lists() })
      queryClient.invalidateQueries({ queryKey: ROLE_QUERY_KEYS.all })
      toast.success('角色删除成功')
    },
    onError: (error: any) => {
      toast.error(error.message || '删除角色失败')
    }
  })

  return {
    roles: data?.roles || [],
    total: data?.total || 0,
    page: data?.page || 1,
    pageSize: data?.page_size || 10,
    totalPages: data?.total_pages || 0,
    isLoading,
    refetch,
    createRole: createMutation.mutate,
    updateRole: updateMutation.mutate,
    deleteRole: deleteMutation.mutate,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  }
}

// 角色筛选器hook
export const useRoleFilters = () => {
  const [filters, setFilters] = useState<RoleFilters>({
    search: '',
    type: '',
    status: '',
    page: 1,
    pageSize: 10
  })

  const updateFilter = (key: keyof RoleFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      // 更新筛选条件时重置页码
      ...(key !== 'page' && { page: 1 })
    }))
  }

  const resetFilters = () => {
    setFilters({
      search: '',
      type: '',
      status: '',
      page: 1,
      pageSize: 10
    })
  }

  return {
    filters,
    updateFilter,
    resetFilters
  }
}
