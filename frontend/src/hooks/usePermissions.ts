// @ts-nocheck
import { useState, useEffect } from 'react';
import { getPermissionList, deletePermission as deletePermissionApi } from '@/api/permission';
import type { Permission } from '@/types';

interface PermissionFilters {
  search: string;
  module: string;
  page?: string;
}

interface UsePermissionsReturn {
  permissions: Permission[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  isLoading: boolean;
  refetch: () => void;
  deletePermission: (id: number) => Promise<void>;
  isDeleting: boolean;
}

export const usePermissions = (filters: PermissionFilters): UsePermissionsReturn => {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchPermissions = async () => {
    setIsLoading(true);
    try {
      const params = {
        page: filters.page ? parseInt(filters.page) : page,
        pageSize,
        search: filters.search,
        module: filters.module
      };

      const response = await getPermissionList(params);
      
      if (response.success) {
        setPermissions(response.data.items || []);
        setTotal(response.data.total || 0);
        setPage(response.data.page || 1);
        setTotalPages(Math.ceil((response.data.total || 0) / pageSize));
      }
    } catch (error) {
      console.error('鑾峰彇鏉冮檺鍒楄〃澶辫触:', error);
      setPermissions([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setIsLoading(false);
    }
  };

  const deletePermission = async (id: number) => {
    setIsDeleting(true);
    try {
      await deletePermissionApi(id);
      await fetchPermissions(); // 閲嶆柊鑾峰彇鏁版嵁
    } catch (error) {
      console.error('鍒犻櫎鏉冮檺澶辫触:', error);
      throw error;
    } finally {
      setIsDeleting(false);
    }
  };

  const refetch = () => {
    fetchPermissions();
  };

  useEffect(() => {
    fetchPermissions();
  }, [filters.search, filters.module, filters.page]);

  return {
    permissions,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    refetch,
    deletePermission,
    isDeleting
  };
};