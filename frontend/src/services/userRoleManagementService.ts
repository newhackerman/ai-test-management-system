/**
 * 用户角色权限管理服务
 * 提供用户角色分配、权限管理、审计日志等API调用
 */
import { apiClient } from './api';

export interface User {
  id: number;
  username: string;
  email: string;
  nickname?: string;
  status: string;
  roles: Role[];
  permissions: string[];
  created_at: string;
  last_login_at?: string;
}

export interface Role {
  id: number;
  code: string;
  name: string;
  description?: string;
  priority: number;
  is_system_role: boolean;
  is_active: boolean;
  user_count: number;
  permission_count: number;
  created_at: string;
}

export interface Permission {
  id: number;
  code: string;
  name: string;
  module: string;
  action: string;
  resource?: string;
  description?: string;
  is_active: boolean;
}

export interface AuditLog {
  id: number;
  user_id: number;
  action: string;
  resource_type: string;
  resource_id: string;
  result: string;
  created_at: string;
  details?: any;
}

export interface UserRoleAssignmentRequest {
  reason?: string;
  expires_at?: string;
}

export interface BatchRoleAssignmentRequest {
  user_ids: number[];
  role_ids: number[];
  reason?: string;
}

export interface RoleCreateRequest {
  name: string;
  code: string;
  description?: string;
  priority?: number;
  is_system_role?: boolean;
  permission_ids?: number[];
  parent_id?: number;
  data_scope?: string;
  data_scope_config?: any;
  max_users?: number;
}

export interface RoleUpdateRequest {
  name?: string;
  code?: string;
  description?: string;
  priority?: number;
  is_active?: boolean;
  permission_ids?: number[];
  data_scope?: string;
  data_scope_config?: any;
  max_users?: number;
}

export interface PermissionCreateRequest {
  name: string;
  code: string;
  module: string;
  action: string;
  resource?: string;
  description?: string;
  parent_id?: number;
  conditions?: any;
}

export interface QueryParams {
  page?: number;
  size?: number;
  search?: string;
  [key: string]: any;
}

export class UserRoleManagementService {
  private baseUrl = '/api/v1/user-role-management';

  // 用户管理
  async getUsers(params?: QueryParams) {
    return apiClient.get(`${this.baseUrl}/users`, { params });
  }

  async getUserById(userId: number) {
    return apiClient.get(`${this.baseUrl}/users/${userId}`);
  }

  async getUserRoles(userId: number) {
    return apiClient.get(`${this.baseUrl}/users/${userId}/roles`);
  }

  async getUserPermissions(userId: number) {
    return apiClient.get(`${this.baseUrl}/users/${userId}/permissions`);
  }

  async getUserDataScope(userId: number) {
    return apiClient.get(`${this.baseUrl}/users/${userId}/data-scope`);
  }

  async assignRoleToUser(userId: number, roleId: number, data?: UserRoleAssignmentRequest) {
    return apiClient.post(`${this.baseUrl}/users/${userId}/roles/${roleId}/assign`, data);
  }

  async revokeRoleFromUser(userId: number, roleId: number, data?: { reason?: string }) {
    return apiClient.delete(`${this.baseUrl}/users/${userId}/roles/${roleId}`, { data });
  }

  async batchAssignRoles(data: BatchRoleAssignmentRequest) {
    return apiClient.post(`${this.baseUrl}/users/batch-assign-roles`, data);
  }

  // 角色管理
  async getRoles(params?: QueryParams) {
    return apiClient.get(`${this.baseUrl}/roles`, { params });
  }

  async getRoleById(roleId: number) {
    return apiClient.get(`${this.baseUrl}/roles/${roleId}`);
  }

  async createRole(data: RoleCreateRequest) {
    return apiClient.post(`${this.baseUrl}/roles`, data);
  }

  async updateRole(roleId: number, data: RoleUpdateRequest) {
    return apiClient.put(`${this.baseUrl}/roles/${roleId}`, data);
  }

  async deleteRole(roleId: number) {
    return apiClient.delete(`${this.baseUrl}/roles/${roleId}`);
  }

  async getRoleHierarchy(roleId: number) {
    return apiClient.get(`${this.baseUrl}/roles/${roleId}/hierarchy`);
  }

  async getRolePermissions(roleId: number) {
    return apiClient.get(`${this.baseUrl}/roles/${roleId}/permissions`);
  }

  async updateRolePermissions(roleId: number, permissionIds: number[]) {
    return apiClient.put(`${this.baseUrl}/roles/${roleId}/permissions`, {
      permission_ids: permissionIds
    });
  }

  async assignPermissionToRole(roleId: number, permissionId: number) {
    return apiClient.post(`${this.baseUrl}/roles/${roleId}/permissions/${permissionId}`);
  }

  async removePermissionFromRole(roleId: number, permissionId: number) {
    return apiClient.delete(`${this.baseUrl}/roles/${roleId}/permissions/${permissionId}`);
  }

  // 权限管理
  async getPermissions(params?: QueryParams) {
    return apiClient.get(`${this.baseUrl}/permissions`, { params });
  }

  async getPermissionModules() {
    return apiClient.get(`${this.baseUrl}/permissions/modules`);
  }

  async createPermission(data: PermissionCreateRequest) {
    return apiClient.post(`${this.baseUrl}/permissions`, data);
  }

  async updatePermission(permissionId: number, data: Partial<PermissionCreateRequest>) {
    return apiClient.put(`${this.baseUrl}/permissions/${permissionId}`, data);
  }

  async deletePermission(permissionId: number) {
    return apiClient.delete(`${this.baseUrl}/permissions/${permissionId}`);
  }

  // 权限检查
  async checkUserPermission(permissionCode: string, resourceId?: string) {
    return apiClient.post(`${this.baseUrl}/check-permission`, {
      permission_code: permissionCode,
      resource_id: resourceId
    });
  }

  async checkUserRole(roleCode: string) {
    return apiClient.post(`${this.baseUrl}/check-role`, {
      role_code: roleCode
    });
  }

  // 审计日志
  async getAuditLogs(params?: {
    user_id?: number;
    action?: string;
    resource_type?: string;
    start_time?: string;
    end_time?: string;
    page?: number;
    size?: number;
  }) {
    return apiClient.get(`${this.baseUrl}/audit-logs`, { params });
  }

  // 统计数据
  async getStatistics() {
    return apiClient.get(`${this.baseUrl}/statistics`);
  }

  async getUserRoleStatistics() {
    return apiClient.get(`${this.baseUrl}/statistics/user-roles`);
  }

  async getRoleUsageStatistics(roleId?: number) {
    const url = roleId 
      ? `${this.baseUrl}/statistics/role-usage/${roleId}`
      : `${this.baseUrl}/statistics/role-usage`;
    return apiClient.get(url);
  }

  // 数据权限
  async getDataPermissions(params?: QueryParams) {
    return apiClient.get(`${this.baseUrl}/data-permissions`, { params });
  }

  async createDataPermission(data: {
    name: string;
    description?: string;
    resource_type: string;
    scope_type: string;
    scope_value?: string[];
    filter_conditions?: any;
    field_permissions?: any;
    priority?: number;
  }) {
    return apiClient.post(`${this.baseUrl}/data-permissions`, data);
  }

  async updateDataPermission(dataPermissionId: number, data: any) {
    return apiClient.put(`${this.baseUrl}/data-permissions/${dataPermissionId}`, data);
  }

  async deleteDataPermission(dataPermissionId: number) {
    return apiClient.delete(`${this.baseUrl}/data-permissions/${dataPermissionId}`);
  }

  async assignDataPermissionToUser(userId: number, dataPermissionId: number) {
    return apiClient.post(`${this.baseUrl}/users/${userId}/data-permissions/${dataPermissionId}`);
  }

  async removeDataPermissionFromUser(userId: number, dataPermissionId: number) {
    return apiClient.delete(`${this.baseUrl}/users/${userId}/data-permissions/${dataPermissionId}`);
  }

  // 角色模板
  async getRoleTemplates(params?: QueryParams) {
    return apiClient.get(`${this.baseUrl}/role-templates`, { params });
  }

  async createRoleTemplate(data: {
    name: string;
    description?: string;
    category?: string;
    template_data: any;
  }) {
    return apiClient.post(`${this.baseUrl}/role-templates`, data);
  }

  async applyRoleTemplate(templateId: number, data: {
    role_name: string;
    role_code: string;
    description?: string;
  }) {
    return apiClient.post(`${this.baseUrl}/role-templates/${templateId}/apply`, data);
  }

  async deleteRoleTemplate(templateId: number) {
    return apiClient.delete(`${this.baseUrl}/role-templates/${templateId}`);
  }

  // 角色审批
  async getRoleApprovals(params?: QueryParams) {
    return apiClient.get(`${this.baseUrl}/role-approvals`, { params });
  }

  async createRoleApproval(data: {
    user_id: number;
    role_id: number;
    action: string;
    reason?: string;
  }) {
    return apiClient.post(`${this.baseUrl}/role-approvals`, data);
  }

  async approveRoleRequest(approvalId: number, data: {
    status: 'approved' | 'rejected';
    approval_reason?: string;
  }) {
    return apiClient.put(`${this.baseUrl}/role-approvals/${approvalId}/approve`, data);
  }

  // 导入导出
  async exportUsers(params?: {
    format?: 'excel' | 'csv';
    include_roles?: boolean;
    include_permissions?: boolean;
  }) {
    return apiClient.get(`${this.baseUrl}/export/users`, { 
      params,
      responseType: 'blob'
    });
  }

  async exportRoles(params?: {
    format?: 'excel' | 'csv';
    include_permissions?: boolean;
  }) {
    return apiClient.get(`${this.baseUrl}/export/roles`, { 
      params,
      responseType: 'blob'
    });
  }

  async importUsers(file: File, options?: {
    update_existing?: boolean;
    assign_default_role?: boolean;
    default_role_id?: number;
  }) {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        formData.append(key, String(value));
      });
    }
    
    return apiClient.post(`${this.baseUrl}/import/users`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }

  async importRoles(file: File, options?: {
    update_existing?: boolean;
  }) {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        formData.append(key, String(value));
      });
    }
    
    return apiClient.post(`${this.baseUrl}/import/roles`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }

  // 权限验证辅助方法
  async hasPermission(permissionCode: string, resourceId?: string): Promise<boolean> {
    try {
      const response = await this.checkUserPermission(permissionCode, resourceId);
      return response.data.has_permission;
    } catch (error) {
      console.error('权限检查失败:', error);
      return false;
    }
  }

  async hasRole(roleCode: string): Promise<boolean> {
    try {
      const response = await this.checkUserRole(roleCode);
      return response.data.has_role;
    } catch (error) {
      console.error('角色检查失败:', error);
      return false;
    }
  }

  async hasAnyPermission(permissionCodes: string[]): Promise<boolean> {
    try {
      const results = await Promise.all(
        permissionCodes.map(code => this.hasPermission(code))
      );
      return results.some(result => result);
    } catch (error) {
      console.error('权限检查失败:', error);
      return false;
    }
  }

  async hasAllPermissions(permissionCodes: string[]): Promise<boolean> {
    try {
      const results = await Promise.all(
        permissionCodes.map(code => this.hasPermission(code))
      );
      return results.every(result => result);
    } catch (error) {
      console.error('权限检查失败:', error);
      return false;
    }
  }
}