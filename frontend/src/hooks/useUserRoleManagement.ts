/**
 * 用户角色权限管理Hook
 * 提供用户角色分配、权限管理等状态管理和操作
 */
import { useState, useEffect, useCallback } from 'react';
import { message } from 'antd';
import { 
  UserRoleManagementService, 
  User, 
  Role, 
  Permission, 
  AuditLog,
  QueryParams,
  RoleCreateRequest,
  RoleUpdateRequest,
  PermissionCreateRequest
} from '../services/userRoleManagementService';

interface UseUserRoleManagementOptions {
  autoLoad?: boolean;
  pageSize?: number;
}

interface UseUserRoleManagementReturn {
  // 用户相关
  users: User[];
  usersLoading: boolean;
  usersTotal: number;
  loadUsers: (params?: QueryParams) => Promise<void>;
  getUserRoles: (userId: number) => Promise<Role[]>;
  getUserPermissions: (userId: number) => Promise<string[]>;
  assignRoleToUser: (userId: number, roleId: number, reason?: string) => Promise<boolean>;
  revokeRoleFromUser: (userId: number, roleId: number, reason?: string) => Promise<boolean>;
  batchAssignRoles: (userIds: number[], roleIds: number[], reason?: string) => Promise<boolean>;

  // 角色相关
  roles: Role[];
  rolesLoading: boolean;
  rolesTotal: number;
  loadRoles: (params?: QueryParams) => Promise<void>;
  createRole: (data: RoleCreateRequest) => Promise<boolean>;
  updateRole: (roleId: number, data: RoleUpdateRequest) => Promise<boolean>;
  deleteRole: (roleId: number) => Promise<boolean>;
  getRolePermissions: (roleId: number) => Promise<Permission[]>;
  updateRolePermissions: (roleId: number, permissionIds: number[]) => Promise<boolean>;

  // 权限相关
  permissions: Permission[];
  permissionsLoading: boolean;
  permissionsTotal: number;
  loadPermissions: (params?: QueryParams) => Promise<void>;
  createPermission: (data: PermissionCreateRequest) => Promise<boolean>;
  updatePermission: (permissionId: number, data: Partial<PermissionCreateRequest>) => Promise<boolean>;
  deletePermission: (permissionId: number) => Promise<boolean>;
  getPermissionModules: () => Promise<string[]>;

  // 权限检查
  checkUserPermission: (permissionCode: string, resourceId?: string) => Promise<boolean>;
  checkUserRole: (roleCode: string) => Promise<boolean>;

  // 审计日志
  auditLogs: AuditLog[];
  auditLogsLoading: boolean;
  auditLogsTotal: number;
  loadAuditLogs: (params?: any) => Promise<void>;

  // 统计数据
  statistics: any;
  loadStatistics: () => Promise<void>;

  // 工具方法
  refresh: () => Promise<void>;
  reset: () => void;
}

export const useUserRoleManagement = (
  options: UseUserRoleManagementOptions = {}
): UseUserRoleManagementReturn => {
  const { autoLoad = true, pageSize = 20 } = options;
  const service = new UserRoleManagementService();

  // 用户状态
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersTotal, setUsersTotal] = useState(0);

  // 角色状态
  const [roles, setRoles] = useState<Role[]>([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [rolesTotal, setRolesTotal] = useState(0);

  // 权限状态
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [permissionsLoading, setPermissionsLoading] = useState(false);
  const [permissionsTotal, setPermissionsTotal] = useState(0);

  // 审计日志状态
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditLogsLoading, setAuditLogsLoading] = useState(false);
  const [auditLogsTotal, setAuditLogsTotal] = useState(0);

  // 统计数据状态
  const [statistics, setStatistics] = useState<any>({});

  // 加载用户列表
  const loadUsers = useCallback(async (params?: QueryParams) => {
    setUsersLoading(true);
    try {
      const response = await service.getUsers({
        size: pageSize,
        ...params
      });
      setUsers(response.data.items);
      setUsersTotal(response.data.total);
    } catch (error) {
      console.error('加载用户列表失败:', error);
      message.error('加载用户列表失败');
    } finally {
      setUsersLoading(false);
    }
  }, [service, pageSize]);

  // 获取用户角色
  const getUserRoles = useCallback(async (userId: number): Promise<Role[]> => {
    try {
      const response = await service.getUserRoles(userId);
      return response.data.roles;
    } catch (error) {
      console.error('获取用户角色失败:', error);
      message.error('获取用户角色失败');
      return [];
    }
  }, [service]);

  // 获取用户权限
  const getUserPermissions = useCallback(async (userId: number): Promise<string[]> => {
    try {
      const response = await service.getUserPermissions(userId);
      return response.data.permissions;
    } catch (error) {
      console.error('获取用户权限失败:', error);
      message.error('获取用户权限失败');
      return [];
    }
  }, [service]);

  // 分配角色给用户
  const assignRoleToUser = useCallback(async (
    userId: number, 
    roleId: number, 
    reason?: string
  ): Promise<boolean> => {
    try {
      await service.assignRoleToUser(userId, roleId, { reason });
      message.success('角色分配成功');
      await loadUsers(); // 刷新用户列表
      return true;
    } catch (error) {
      console.error('角色分配失败:', error);
      message.error('角色分配失败');
      return false;
    }
  }, [service, loadUsers]);

  // 撤销用户角色
  const revokeRoleFromUser = useCallback(async (
    userId: number, 
    roleId: number, 
    reason?: string
  ): Promise<boolean> => {
    try {
      await service.revokeRoleFromUser(userId, roleId, { reason });
      message.success('角色撤销成功');
      await loadUsers(); // 刷新用户列表
      return true;
    } catch (error) {
      console.error('角色撤销失败:', error);
      message.error('角色撤销失败');
      return false;
    }
  }, [service, loadUsers]);

  // 批量分配角色
  const batchAssignRoles = useCallback(async (
    userIds: number[], 
    roleIds: number[], 
    reason?: string
  ): Promise<boolean> => {
    try {
      const response = await service.batchAssignRoles({
        user_ids: userIds,
        role_ids: roleIds,
        reason
      });
      message.success(`批量操作完成，成功: ${response.data.success_count}，失败: ${response.data.failed_count}`);
      await loadUsers(); // 刷新用户列表
      return true;
    } catch (error) {
      console.error('批量分配角色失败:', error);
      message.error('批量分配角色失败');
      return false;
    }
  }, [service, loadUsers]);

  // 加载角色列表
  const loadRoles = useCallback(async (params?: QueryParams) => {
    setRolesLoading(true);
    try {
      const response = await service.getRoles({
        size: pageSize,
        ...params
      });
      setRoles(response.data.items);
      setRolesTotal(response.data.total);
    } catch (error) {
      console.error('加载角色列表失败:', error);
      message.error('加载角色列表失败');
    } finally {
      setRolesLoading(false);
    }
  }, [service, pageSize]);

  // 创建角色
  const createRole = useCallback(async (data: RoleCreateRequest): Promise<boolean> => {
    try {
      await service.createRole(data);
      message.success('角色创建成功');
      await loadRoles(); // 刷新角色列表
      return true;
    } catch (error) {
      console.error('角色创建失败:', error);
      message.error('角色创建失败');
      return false;
    }
  }, [service, loadRoles]);

  // 更新角色
  const updateRole = useCallback(async (
    roleId: number, 
    data: RoleUpdateRequest
  ): Promise<boolean> => {
    try {
      await service.updateRole(roleId, data);
      message.success('角色更新成功');
      await loadRoles(); // 刷新角色列表
      return true;
    } catch (error) {
      console.error('角色更新失败:', error);
      message.error('角色更新失败');
      return false;
    }
  }, [service, loadRoles]);

  // 删除角色
  const deleteRole = useCallback(async (roleId: number): Promise<boolean> => {
    try {
      await service.deleteRole(roleId);
      message.success('角色删除成功');
      await loadRoles(); // 刷新角色列表
      return true;
    } catch (error) {
      console.error('角色删除失败:', error);
      message.error('角色删除失败');
      return false;
    }
  }, [service, loadRoles]);

  // 获取角色权限
  const getRolePermissions = useCallback(async (roleId: number): Promise<Permission[]> => {
    try {
      const response = await service.getRolePermissions(roleId);
      return response.data.permissions;
    } catch (error) {
      console.error('获取角色权限失败:', error);
      message.error('获取角色权限失败');
      return [];
    }
  }, [service]);

  // 更新角色权限
  const updateRolePermissions = useCallback(async (
    roleId: number, 
    permissionIds: number[]
  ): Promise<boolean> => {
    try {
      await service.updateRolePermissions(roleId, permissionIds);
      message.success('角色权限更新成功');
      await loadRoles(); // 刷新角色列表
      return true;
    } catch (error) {
      console.error('角色权限更新失败:', error);
      message.error('角色权限更新失败');
      return false;
    }
  }, [service, loadRoles]);

  // 加载权限列表
  const loadPermissions = useCallback(async (params?: QueryParams) => {
    setPermissionsLoading(true);
    try {
      const response = await service.getPermissions({
        size: pageSize,
        ...params
      });
      setPermissions(response.data.items);
      setPermissionsTotal(response.data.total);
    } catch (error) {
      console.error('加载权限列表失败:', error);
      message.error('加载权限列表失败');
    } finally {
      setPermissionsLoading(false);
    }
  }, [service, pageSize]);

  // 创建权限
  const createPermission = useCallback(async (data: PermissionCreateRequest): Promise<boolean> => {
    try {
      await service.createPermission(data);
      message.success('权限创建成功');
      await loadPermissions(); // 刷新权限列表
      return true;
    } catch (error) {
      console.error('权限创建失败:', error);
      message.error('权限创建失败');
      return false;
    }
  }, [service, loadPermissions]);

  // 更新权限
  const updatePermission = useCallback(async (
    permissionId: number, 
    data: Partial<PermissionCreateRequest>
  ): Promise<boolean> => {
    try {
      await service.updatePermission(permissionId, data);
      message.success('权限更新成功');
      await loadPermissions(); // 刷新权限列表
      return true;
    } catch (error) {
      console.error('权限更新失败:', error);
      message.error('权限更新失败');
      return false;
    }
  }, [service, loadPermissions]);

  // 删除权限
  const deletePermission = useCallback(async (permissionId: number): Promise<boolean> => {
    try {
      await service.deletePermission(permissionId);
      message.success('权限删除成功');
      await loadPermissions(); // 刷新权限列表
      return true;
    } catch (error) {
      console.error('权限删除失败:', error);
      message.error('权限删除失败');
      return false;
    }
  }, [service, loadPermissions]);

  // 获取权限模块
  const getPermissionModules = useCallback(async (): Promise<string[]> => {
    try {
      const response = await service.getPermissionModules();
      return response.data.modules;
    } catch (error) {
      console.error('获取权限模块失败:', error);
      message.error('获取权限模块失败');
      return [];
    }
  }, [service]);

  // 检查用户权限
  const checkUserPermission = useCallback(async (
    permissionCode: string, 
    resourceId?: string
  ): Promise<boolean> => {
    try {
      const response = await service.checkUserPermission(permissionCode, resourceId);
      return response.data.has_permission;
    } catch (error) {
      console.error('权限检查失败:', error);
      return false;
    }
  }, [service]);

  // 检查用户角色
  const checkUserRole = useCallback(async (roleCode: string): Promise<boolean> => {
    try {
      const response = await service.checkUserRole(roleCode);
      return response.data.has_role;
    } catch (error) {
      console.error('角色检查失败:', error);
      return false;
    }
  }, [service]);

  // 加载审计日志
  const loadAuditLogs = useCallback(async (params?: any) => {
    setAuditLogsLoading(true);
    try {
      const response = await service.getAuditLogs({
        size: pageSize,
        ...params
      });
      setAuditLogs(response.data.items);
      setAuditLogsTotal(response.data.total);
    } catch (error) {
      console.error('加载审计日志失败:', error);
      message.error('加载审计日志失败');
    } finally {
      setAuditLogsLoading(false);
    }
  }, [service, pageSize]);

  // 加载统计数据
  const loadStatistics = useCallback(async () => {
    try {
      const response = await service.getStatistics();
      setStatistics(response.data);
    } catch (error) {
      console.error('加载统计数据失败:', error);
    }
  }, [service]);

  // 刷新所有数据
  const refresh = useCallback(async () => {
    await Promise.all([
      loadUsers(),
      loadRoles(),
      loadPermissions(),
      loadStatistics()
    ]);
  }, [loadUsers, loadRoles, loadPermissions, loadStatistics]);

  // 重置状态
  const reset = useCallback(() => {
    setUsers([]);
    setUsersTotal(0);
    setRoles([]);
    setRolesTotal(0);
    setPermissions([]);
    setPermissionsTotal(0);
    setAuditLogs([]);
    setAuditLogsTotal(0);
    setStatistics({});
  }, []);

  // 初始化加载
  useEffect(() => {
    if (autoLoad) {
      refresh();
    }
  }, [autoLoad, refresh]);

  return {
    // 用户相关
    users,
    usersLoading,
    usersTotal,
    loadUsers,
    getUserRoles,
    getUserPermissions,
    assignRoleToUser,
    revokeRoleFromUser,
    batchAssignRoles,

    // 角色相关
    roles,
    rolesLoading,
    rolesTotal,
    loadRoles,
    createRole,
    updateRole,
    deleteRole,
    getRolePermissions,
    updateRolePermissions,

    // 权限相关
    permissions,
    permissionsLoading,
    permissionsTotal,
    loadPermissions,
    createPermission,
    updatePermission,
    deletePermission,
    getPermissionModules,

    // 权限检查
    checkUserPermission,
    checkUserRole,

    // 审计日志
    auditLogs,
    auditLogsLoading,
    auditLogsTotal,
    loadAuditLogs,

    // 统计数据
    statistics,
    loadStatistics,

    // 工具方法
    refresh,
    reset
  };
};