// Token 存储键名
const TOKEN_KEY = 'ai_test_access_token';
const REFRESH_TOKEN_KEY = 'ai_test_refresh_token';

/**
 * 获取访问令牌
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * 设置访问令牌
 */
export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

/**
 * 移除访问令牌
 */
export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};

/**
 * 获取刷新令牌
 */
export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

/**
 * 设置刷新令牌
 */
export const setRefreshToken = (token: string): void => {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
};

/**
 * 检查令牌是否存在
 */
export const hasToken = (): boolean => {
  return !!getToken();
};

/**
 * 清除所有认证相关数据
 */
export const clearAuth = (): void => {
  removeToken();
  // 可以在这里清除其他认证相关的本地存储数据
};