import { apiClient } from '@/lib/api-client';
import type { LoginRequest, LoginResponse, User, ApiResponse } from '@/types';

// 用户登录
export const login = async (credentials: LoginRequest): Promise<ApiResponse<LoginResponse>> => {
  const response = await apiClient.post('/api/v1/auth/login', credentials);
  return response;
};

// 用户登出
export const logout = async (): Promise<ApiResponse<void>> => {
  const response = await apiClient.post('/api/v1/auth/logout');
  return response;
};

// 刷新令牌
export const refreshToken = async (refreshToken: string): Promise<ApiResponse<LoginResponse>> => {
  const response = await apiClient.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
  return response;
};

// 获取当前用户信息
export const getUserInfo = async (): Promise<ApiResponse<{
  user_info: User;
  permissions: string[];
  roles: any[];
}>> => {
  const response = await apiClient.get('/api/v1/auth/me');
  return response;
};

// 修改密码
export const changePassword = async (data: {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}): Promise<ApiResponse<void>> => {
  const response = await apiClient.post('/api/v1/auth/change-password', data);
  return response;
};

// 忘记密码
export const forgotPassword = async (email: string): Promise<ApiResponse<void>> => {
  const response = await apiClient.post('/api/v1/auth/forgot-password', { email });
  return response;
};

// 重置密码
export const resetPassword = async (data: {
  token: string;
  password: string;
  confirmPassword: string;
}): Promise<ApiResponse<void>> => {
  const response = await apiClient.post('/api/v1/auth/reset-password', data);
  return response;
};

// 验证邮箱
export const verifyEmail = async (token: string): Promise<ApiResponse<void>> => {
  const response = await apiClient.post('/api/v1/auth/verify-email', { token });
  return response;
};

// 发送验证邮件
export const sendVerificationEmail = async (): Promise<ApiResponse<void>> => {
  const response = await apiClient.post('/api/v1/auth/send-verification-email');
  return response;
};