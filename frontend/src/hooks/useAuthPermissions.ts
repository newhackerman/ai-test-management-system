// @ts-nocheck
import { useContext } from 'react';
import { AuthContext } from '@/contexts/AuthContext';

interface UseAuthPermissionsReturn {
  permissions: string[];
  roles: string[];
  hasPermission: (permission: string | string[]) => boolean;
  hasRole: (role: string | string[]) => boolean;
  hasAnyPermission: (permissions: string[]) => boolean;
  hasAllPermissions: (permissions: string[]) => boolean;
  isSuperAdmin: boolean;
}

export const useAuthPermissions = (): UseAuthPermissionsReturn => {
  const authContext = useContext(AuthContext);
  
  if (!authContext) {
    throw new Error('useAuthPermissions must be used within an AuthProvider');
  }

  const { user, permissions, roles } = authContext;
  
  // 妫€鏌ユ槸鍚︿负瓒呯骇绠＄悊鍛?
  const isSuperAdmin = user?.isSuperAdmin || false;
  
  // 鑾峰彇鏉冮檺浠ｇ爜鍒楄〃
  const permissionCodes = permissions || [];
  
  // 鑾峰彇瑙掕壊浠ｇ爜鍒楄〃
  const roleCodes = roles?.map(role => role.code) || [];

  /**
   * 妫€鏌ユ槸鍚︽湁鎸囧畾鏉冮檺
   * @param permission 鏉冮檺浠ｇ爜鎴栨潈闄愪唬鐮佹暟缁?
   * @returns 鏄惁鏈夋潈闄?
   */
  const hasPermission = (permission: string | string[]): boolean => {
    // 瓒呯骇绠＄悊鍛樻嫢鏈夋墍鏈夋潈闄?
    if (isSuperAdmin) {
      return true;
    }

    if (Array.isArray(permission)) {
      // 濡傛灉鏄暟缁勶紝妫€鏌ユ槸鍚︽湁浠绘剰涓€涓潈闄?
      return permission.some(p => permissionCodes.includes(p));
    } else {
      // 濡傛灉鏄崟涓潈闄愶紝鐩存帴妫€鏌?
      return permissionCodes.includes(permission);
    }
  };

  /**
   * 妫€鏌ユ槸鍚︽湁鎸囧畾瑙掕壊
   * @param role 瑙掕壊浠ｇ爜鎴栬鑹蹭唬鐮佹暟缁?
   * @returns 鏄惁鏈夎鑹?
   */
  const hasRole = (role: string | string[]): boolean => {
    // 瓒呯骇绠＄悊鍛樻嫢鏈夋墍鏈夎鑹?
    if (isSuperAdmin) {
      return true;
    }

    if (Array.isArray(role)) {
      // 濡傛灉鏄暟缁勶紝妫€鏌ユ槸鍚︽湁浠绘剰涓€涓鑹?
      return role.some(r => roleCodes.includes(r));
    } else {
      // 濡傛灉鏄崟涓鑹诧紝鐩存帴妫€鏌?
      return roleCodes.includes(role);
    }
  };

  /**
   * 妫€鏌ユ槸鍚︽湁浠绘剰涓€涓潈闄?
   * @param permissions 鏉冮檺浠ｇ爜鏁扮粍
   * @returns 鏄惁鏈変换鎰忔潈闄?
   */
  const hasAnyPermission = (permissions: string[]): boolean => {
    // 瓒呯骇绠＄悊鍛樻嫢鏈夋墍鏈夋潈闄?
    if (isSuperAdmin) {
      return true;
    }

    return permissions.some(permission => permissionCodes.includes(permission));
  };

  /**
   * 妫€鏌ユ槸鍚︽湁鎵€鏈夋潈闄?
   * @param permissions 鏉冮檺浠ｇ爜鏁扮粍
   * @returns 鏄惁鏈夋墍鏈夋潈闄?
   */
  const hasAllPermissions = (permissions: string[]): boolean => {
    // 瓒呯骇绠＄悊鍛樻嫢鏈夋墍鏈夋潈闄?
    if (isSuperAdmin) {
      return true;
    }

    return permissions.every(permission => permissionCodes.includes(permission));
  };

  return {
    permissions: permissionCodes,
    roles: roleCodes,
    hasPermission,
    hasRole,
    hasAnyPermission,
    hasAllPermissions,
    isSuperAdmin
  };
};