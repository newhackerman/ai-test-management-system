import { useState, useEffect } from 'react';
import { getPermissionMatrix } from '@/api/permission';
import type { PermissionMatrix } from '@/types';

interface UsePermissionMatrixReturn {
  matrix: PermissionMatrix | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export const usePermissionMatrix = (): UsePermissionMatrixReturn => {
  const [matrix, setMatrix] = useState<PermissionMatrix | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMatrix = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await getPermissionMatrix();
      
      if (response.success) {
        setMatrix(response.data);
      } else {
        setError(response.message || '获取权限矩阵失败');
      }
    } catch (err: any) {
      console.error('获取权限矩阵失败:', err);
      setError(err.message || '获取权限矩阵失败');
      setMatrix(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refetch = () => {
    fetchMatrix();
  };

  useEffect(() => {
    fetchMatrix();
  }, []);

  return {
    matrix,
    isLoading,
    error,
    refetch
  };
};