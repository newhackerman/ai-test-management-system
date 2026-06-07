import { useState, useEffect, useCallback } from 'react'
import { message } from 'antd'
import { ConfigService, ConfigItem, ConfigGroup, Environment, ConfigCreateRequest, ConfigUpdateRequest } from '@/services/config-service'

export const useConfigManagement = () => {
  const [configs, setConfigs] = useState<ConfigItem[]>([])
  const [groups, setGroups] = useState<ConfigGroup[]>([])
  const [environments, setEnvironments] = useState<Environment[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0
  })

  // 加载配置列表
  const loadConfigs = useCallback(async (params: {
    environment?: 'dev' | 'test' | 'prod'
    group_id?: number
    page?: number
    size?: number
    search?: string
    config_type?: string
    is_core?: boolean
  } = {}) => {
    setLoading(true)
    try {
      const response = await ConfigService.getConfigs({
        ...params,
        page: params.page || pagination.current,
        size: params.size || pagination.pageSize
      })
      
      setConfigs(response.items)
      setPagination(prev => ({
        ...prev,
        total: response.total,
        current: params.page || prev.current,
        pageSize: params.size || prev.pageSize
      }))
      
      return response
    } catch (error) {
      message.error('加载配置列表失败')
      throw error
    } finally {
      setLoading(false)
    }
  }, [pagination.current, pagination.pageSize])

  // 加载分组列表
  const loadGroups = useCallback(async () => {
    try {
      const groupList = await ConfigService.getConfigGroups()
      setGroups(groupList)
      return groupList
    } catch (error) {
      message.error('加载分组列表失败')
      throw error
    }
  }, [])

  // 加载环境列表
  const loadEnvironments = useCallback(async () => {
    try {
      const envList = await ConfigService.getEnvironments()
      setEnvironments(envList)
      return envList
    } catch (error) {
      message.error('加载环境列表失败')
      throw error
    }
  }, [])

  // 创建配置
  const createConfig = useCallback(async (data: ConfigCreateRequest) => {
    try {
      const result = await ConfigService.createConfig(data)
      message.success('创建配置成功')
      return result
    } catch (error) {
      message.error('创建配置失败')
      throw error
    }
  }, [])

  // 更新配置
  const updateConfig = useCallback(async (
    configKey: string, 
    data: ConfigUpdateRequest, 
    environment: 'dev' | 'test' | 'prod' = 'prod'
  ) => {
    try {
      const result = await ConfigService.updateConfig(configKey, data, environment)
      message.success('更新配置成功')
      return result
    } catch (error) {
      message.error('更新配置失败')
      throw error
    }
  }, [])

  // 删除配置
  const deleteConfig = useCallback(async (
    configKey: string, 
    environment: 'dev' | 'test' | 'prod' = 'prod',
    hardDelete: boolean = false
  ) => {
    try {
      await ConfigService.deleteConfig(configKey, environment, hardDelete)
      message.success('删除配置成功')
    } catch (error) {
      message.error('删除配置失败')
      throw error
    }
  }, [])

  // 批量更新配置
  const batchUpdateConfigs = useCallback(async (updates: any[]) => {
    try {
      const result = await ConfigService.batchUpdateConfigs(updates)
      message.success('批量更新成功')
      return result
    } catch (error) {
      message.error('批量更新失败')
      throw error
    }
  }, [])

  // 环境同步
  const syncEnvironments = useCallback(async (
    sourceEnv: string, 
    targetEnv: string, 
    configKeys?: string[]
  ) => {
    try {
      const result = await ConfigService.syncEnvironments(sourceEnv, targetEnv, configKeys)
      message.success('环境同步成功')
      return result
    } catch (error) {
      message.error('环境同步失败')
      throw error
    }
  }, [])

  // 比较环境
  const compareEnvironments = useCallback(async (env1: string, env2: string) => {
    try {
      const result = await ConfigService.compareEnvironments(env1, env2)
      return result
    } catch (error) {
      message.error('环境比较失败')
      throw error
    }
  }, [])

  // 获取环境统计
  const getEnvironmentStatistics = useCallback(async (environment: string) => {
    try {
      const result = await ConfigService.getEnvironmentStatistics(environment)
      return result
    } catch (error) {
      message.error('获取环境统计失败')
      throw error
    }
  }, [])

  return {
    // 状态
    configs,
    groups,
    environments,
    loading,
    pagination,
    
    // 设置状态
    setConfigs,
    setGroups,
    setEnvironments,
    setPagination,
    
    // 方法
    loadConfigs,
    loadGroups,
    loadEnvironments,
    createConfig,
    updateConfig,
    deleteConfig,
    batchUpdateConfigs,
    syncEnvironments,
    compareEnvironments,
    getEnvironmentStatistics
  }
}

export const useConfigGroups = () => {
  const [groups, setGroups] = useState<ConfigGroup[]>([])
  const [loading, setLoading] = useState(false)

  // 加载分组列表
  const loadGroups = useCallback(async () => {
    setLoading(true)
    try {
      const groupList = await ConfigService.getConfigGroups()
      setGroups(groupList)
      return groupList
    } catch (error) {
      message.error('加载分组列表失败')
      throw error
    } finally {
      setLoading(false)
    }
  }, [])

  // 创建分组
  const createGroup = useCallback(async (data: Partial<ConfigGroup>) => {
    try {
      const result = await ConfigService.createConfigGroup(data)
      message.success('创建分组成功')
      return result
    } catch (error) {
      message.error('创建分组失败')
      throw error
    }
  }, [])

  // 更新分组
  const updateGroup = useCallback(async (id: number, data: Partial<ConfigGroup>) => {
    try {
      const result = await ConfigService.updateConfigGroup(id, data)
      message.success('更新分组成功')
      return result
    } catch (error) {
      message.error('更新分组失败')
      throw error
    }
  }, [])

  // 删除分组
  const deleteGroup = useCallback(async (id: number) => {
    try {
      await ConfigService.deleteConfigGroup(id)
      message.success('删除分组成功')
    } catch (error) {
      message.error('删除分组失败')
      throw error
    }
  }, [])

  // 初始化时加载数据
  useEffect(() => {
    loadGroups()
  }, [loadGroups])

  return {
    groups,
    loading,
    setGroups,
    loadGroups,
    createGroup,
    updateGroup,
    deleteGroup
  }
}

export const useConfigPermissions = () => {
  const [permissions, setPermissions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  // 检查配置权限
  const checkConfigPermission = useCallback(async (
    configKey: string, 
    environment: string, 
    action: string
  ) => {
    try {
      const result = await ConfigService.checkConfigPermission(configKey, environment, action)
      return result
    } catch (error) {
      console.error('检查配置权限失败:', error)
      return false
    }
  }, [])

  // 批量检查配置权限
  const batchCheckConfigPermission = useCallback(async (
    configKeys: string[], 
    environment: string, 
    action: string
  ) => {
    try {
      const result = await ConfigService.batchCheckConfigPermission(configKeys, environment, action)
      return result
    } catch (error) {
      console.error('批量检查配置权限失败:', error)
      return {}
    }
  }, [])

  // 获取我的权限
  const getMyPermissions = useCallback(async () => {
    setLoading(true)
    try {
      const result = await ConfigService.getMyConfigPermissions()
      setPermissions(result)
      return result
    } catch (error) {
      message.error('获取权限列表失败')
      throw error
    } finally {
      setLoading(false)
    }
  }, [])

  // 授予权限
  const grantPermission = useCallback(async (targetUserId: number, permissionData: any) => {
    try {
      const result = await ConfigService.grantConfigPermission(targetUserId, permissionData)
      message.success('授予权限成功')
      return result
    } catch (error) {
      message.error('授予权限失败')
      throw error
    }
  }, [])

  // 撤销权限
  const revokePermission = useCallback(async (permissionId: number) => {
    try {
      await ConfigService.revokeConfigPermission(permissionId)
      message.success('撤销权限成功')
    } catch (error) {
      message.error('撤销权限失败')
      throw error
    }
  }, [])

  return {
    permissions,
    loading,
    checkConfigPermission,
    batchCheckConfigPermission,
    getMyPermissions,
    grantPermission,
    revokePermission
  }
}