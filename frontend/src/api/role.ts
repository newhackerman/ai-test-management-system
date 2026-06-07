import { apiClient } from '@/lib/api-client';
import type { Role, ApiResponse, PaginatedResponse, CreateRoleRequest, UpdateRoleRequest } from '@/types';

// 获取角色列表
export const getRoleList = async (params: {
  page?: number;
  pageSize?: number;
  search?: string;
  type?: string;
  status?: string;
}): Promise<ApiResponse<PaginatedResponse<Role>>> => {
  const queryParams = new URLSearchParams();
  
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params.search) queryParams.append('search', params.search);
  if (params.type) queryParams.append('type', params.type);
  if (params.status) queryParams.append('status', params.status);

  const response = await apiClient.get(`/roles?${queryParams.toString()}`);
  return response;
};

// 获取角色详情
export const getRoleDetail = async (id: number): Promise<ApiResponse<Role>> => {
  const response = await apiClient.get(`/roles/${id}`);
  return response;
};

// 创建角色
export const createRole = async (data: CreateRoleRequest): Promise<ApiResponse<Role>> => {
  const response = await apiClient.post('/roles', data);
  return response;
};

// 更新角色
export const updateRole = async (id: number, data: UpdateRoleRequest): Promise<ApiResponse<Role>> => {
  const response = await apiClient.put(`/roles/${id}`, data);
  return response;
};

// 删除角色
export const deleteRole = async (id: number): Promise<ApiResponse<void>> => {
  const response = await apiClient.delete(`/roles/${id}`);
  return response;
};

// 获取角色权限
export const getRolePermissions = async (id: number): Promise<ApiResponse<any>> => {
  const response = await apiClient.get(`/roles/${id}/permissions`);
  return response;
};

// 为角色分配权限
export const assignRolePermissions = async (id: number, permissionIds: number[]): Promise<ApiResponse<void>> => {
  const response = await apiClient.post(`/roles/${id}/permissions`, permissionIds);
  return response;
};

// 更新角色权限
export const updateRolePermissions = async (id: number, permissionIds: number[]): Promise<ApiResponse<void>> => {
  const response = await apiClient.put(`/roles/${id}/permissions`, permissionIds);
  return response;
};

// 移除角色权限
export const removeRolePermission = async (roleId: number, permissionId: number): Promise<ApiResponse<void>> => {
  const response = await apiClient.delete(`/roles/${roleId}/permissions/${permissionId}`);
  return response;
};

// 获取角色用户
export const getRoleUsers = async (id: number, params: {
  page?: number;
  pageSize?: number;
}): Promise<ApiResponse<any>> => {
  const queryParams = new URLSearchParams();
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.pageSize) queryParams.append('page_size', params.pageSize.toString());

  const response = await apiClient.get(`/roles/${id}/users?${queryParams.toString()}`);
  return response;
};

// 获取所有角色（简化版，用于下拉选择）
export const getAllRoles = async (): Promise<ApiResponse<Role[]>> => {
  const response = await apiClient.get('/roles/all');
  return response;
};