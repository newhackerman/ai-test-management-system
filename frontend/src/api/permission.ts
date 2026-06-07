import { apiClient } from '@/lib/api-client';
import type { Permission, ApiResponse, PaginatedResponse, CreatePermissionRequest, UpdatePermissionRequest, PermissionMatrix } from '@/types';

// 获取权限列表
export const getPermissionList = async (params: {
  page?: number;
  pageSize?: number;
  search?: string;
  module?: string;
}): Promise<ApiResponse<PaginatedResponse<Permission>>> => {
  const queryParams = new URLSearchParams();
  
  if (params.page) queryParams.append('page', params.page.toString());
  if (params.pageSize) queryParams.append('page_size', params.pageSize.toString());
  if (params.search) queryParams.append('search', params.search);
  if (params.module) queryParams.append('module', params.module);

  const response = await apiClient.get(`/permissions?${queryParams.toString()}`);
  return response;
};

// 获取权限详情
export const getPermissionDetail = async (id: number): Promise<ApiResponse<Permission>> => {
  const response = await apiClient.get(`/permissions/${id}`);
  return response;
};

// 创建权限
export const createPermission = async (data: CreatePermissionRequest): Promise<ApiResponse<Permission>> => {
  const response = await apiClient.post('/permissions', data);
  return response;
};

// 更新权限
export const updatePermission = async (id: number, data: UpdatePermissionRequest): Promise<ApiResponse<Permission>> => {
  const response = await apiClient.put(`/permissions/${id}`, data);
  return response;
};

// 删除权限
export const deletePermission = async (id: number): Promise<ApiResponse<void>> => {
  const response = await apiClient.delete(`/permissions/${id}`);
  return response;
};

// 获取权限矩阵
export const getPermissionMatrix = async (): Promise<ApiResponse<PermissionMatrix>> => {
  const response = await apiClient.get('/permissions/matrix');
  return response;
};

// 获取权限模块
export const getPermissionModules = async (): Promise<ApiResponse<string[]>> => {
  const response = await apiClient.get('/permissions/modules');
  return response;
};

// 获取所有权限（简化版，用于下拉选择）
export const getAllPermissions = async (): Promise<ApiResponse<Permission[]>> => {
  const response = await apiClient.get('/permissions/all');
  return response;
};