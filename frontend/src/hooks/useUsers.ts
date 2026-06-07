import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'
import { userService, type CreateUserData, type UpdateUserData } from '@/services/user-service'
import type { UserFilters } from '@/types'

export const USER_QUERY_KEYS = {
  all: ['users'] as const,
  lists: () => [...USER_QUERY_KEYS.all, 'list'] as const,
  list: (filters: UserFilters) => [...USER_QUERY_KEYS.lists(), filters] as const,
  roles: () => [...USER_QUERY_KEYS.all, 'roles'] as const,
  permissions: (id: string) => [...USER_QUERY_KEYS.all, 'permissions', id] as const,
}

export const useUsers = (filters: UserFilters = {}) => {
  const queryClient = useQueryClient()

  const usersQuery = useQuery({
    queryKey: USER_QUERY_KEYS.list(filters),
    queryFn: () => userService.getUsers(filters),
    staleTime: 60 * 1000,
  })

  const invalidateUsers = () => {
    queryClient.invalidateQueries({ queryKey: USER_QUERY_KEYS.lists() })
    queryClient.invalidateQueries({ queryKey: USER_QUERY_KEYS.roles() })
  }

  const createMutation = useMutation({
    mutationFn: (data: CreateUserData) => userService.createUser(data),
    onSuccess: () => {
      invalidateUsers()
      toast.success('用户创建成功')
    },
    onError: (error: Error) => toast.error(error.message || '创建用户失败'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UpdateUserData }) => userService.updateUser(userId, data),
    onSuccess: (_, variables) => {
      invalidateUsers()
      queryClient.invalidateQueries({ queryKey: USER_QUERY_KEYS.permissions(variables.userId) })
      toast.success('用户更新成功')
    },
    onError: (error: Error) => toast.error(error.message || '更新用户失败'),
  })

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => userService.deleteUser(userId),
    onSuccess: () => {
      invalidateUsers()
      toast.success('用户删除成功')
    },
    onError: (error: Error) => toast.error(error.message || '删除用户失败'),
  })

  const lockMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason?: string }) => userService.lockUser(userId, reason),
    onSuccess: () => {
      invalidateUsers()
      toast.success('用户已锁定')
    },
    onError: (error: Error) => toast.error(error.message || '锁定用户失败'),
  })

  const unlockMutation = useMutation({
    mutationFn: (userId: string) => userService.unlockUser(userId),
    onSuccess: () => {
      invalidateUsers()
      toast.success('用户已解锁')
    },
    onError: (error: Error) => toast.error(error.message || '解锁用户失败'),
  })

  const resetPasswordMutation = useMutation({
    mutationFn: ({ userId, newPassword, forceChange }: { userId: string; newPassword: string; forceChange?: boolean }) =>
      userService.resetUserPassword(userId, newPassword, forceChange),
    onSuccess: () => toast.success('密码重置成功'),
    onError: (error: Error) => toast.error(error.message || '重置密码失败'),
  })

  const batchUpdateMutation = useMutation({
    mutationFn: ({
      userIds,
      action,
      data,
    }: {
      userIds: string[]
      action: 'activate' | 'deactivate' | 'delete' | 'assign_role' | 'remove_role'
      data?: { role_id?: number; reason?: string }
    }) => userService.batchUpdateUsers(userIds, action, data),
    onSuccess: (result) => {
      invalidateUsers()
      toast.success(`批量操作完成：成功 ${result.success_count} 个，失败 ${result.failed_count} 个`)
    },
    onError: (error: Error) => toast.error(error.message || '批量操作失败'),
  })

  const data = usersQuery.data

  return {
    users: data?.users || [],
    total: data?.total || 0,
    page: data?.page || 1,
    pageSize: data?.page_size || 10,
    totalPages: data?.total_pages || 0,
    isLoading: usersQuery.isLoading,
    refetch: usersQuery.refetch,
    createUser: createMutation.mutateAsync,
    updateUser: updateMutation.mutateAsync,
    deleteUser: deleteMutation.mutateAsync,
    lockUser: lockMutation.mutateAsync,
    unlockUser: unlockMutation.mutateAsync,
    resetPassword: resetPasswordMutation.mutateAsync,
    batchUpdate: batchUpdateMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isLocking: lockMutation.isPending,
    isUnlocking: unlockMutation.isPending,
    isResettingPassword: resetPasswordMutation.isPending,
    isBatchUpdating: batchUpdateMutation.isPending,
  }
}

export const useRoles = () =>
  useQuery({
    queryKey: USER_QUERY_KEYS.roles(),
    queryFn: () => userService.getRoles(),
    staleTime: 5 * 60 * 1000,
  })

export const useUserPermissions = (userId?: string) =>
  useQuery({
    queryKey: USER_QUERY_KEYS.permissions(userId || ''),
    queryFn: () => userService.getUserPermissions(userId || ''),
    enabled: Boolean(userId),
  })

export const useUserFilters = () => {
  const [filters, setFilters] = useState<UserFilters>({
    search: '',
    role: '',
    status: '',
    page: 1,
    size: 10,
  })

  const updateFilter = (key: keyof UserFilters, value: unknown) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      ...(key !== 'page' ? { page: 1 } : {}),
    }))
  }

  const resetFilters = () => {
    setFilters({
      search: '',
      role: '',
      status: '',
      page: 1,
      size: 10,
    })
  }

  return { filters, updateFilter, resetFilters }
}

export const useUserImportExport = () => {
  const [isExporting, setIsExporting] = useState(false)
  const [isImporting, setIsImporting] = useState(false)

  const exportUsers = async (filters: UserFilters = {}) => {
    setIsExporting(true)
    try {
      const blob = await userService.exportUsers(filters)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `users_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      toast.success('用户数据导出成功')
    } catch (error: any) {
      toast.error(error.message || '导出失败')
      throw error
    } finally {
      setIsExporting(false)
    }
  }

  const importUsers = async (file: File, options?: { onSuccess?: (result: any) => void }) => {
    setIsImporting(true)
    try {
      const result = await userService.importUsers(file)
      toast.success(`导入完成：成功 ${result.success_count} 个，失败 ${result.failed_count} 个`)
      options?.onSuccess?.(result)
      return result
    } catch (error: any) {
      toast.error(error.message || '导入失败')
      throw error
    } finally {
      setIsImporting(false)
    }
  }

  return { exportUsers, importUsers, isExporting, isImporting }
}
