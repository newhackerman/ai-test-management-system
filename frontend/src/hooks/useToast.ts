/**
 * Toast 通知系统 Hook
 */
import { useState, useCallback, useRef } from 'react';

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'destructive';

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastType;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  onClose?: () => void;
}

interface ToastOptions {
  title?: string;
  description?: string;
  variant?: ToastType;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface UseToastReturn {
  toasts: Toast[];
  toast: (options: ToastOptions) => string;
  dismiss: (toastId: string) => void;
  dismissAll: () => void;
}

// 全局 toast 状态管理
let globalToasts: Toast[] = [];
let globalListeners: Set<(toasts: Toast[]) => void> = new Set();

const notifyListeners = () => {
  globalListeners.forEach(listener => listener([...globalToasts]));
};

const addToast = (toast: Toast) => {
  globalToasts = [...globalToasts, toast];
  notifyListeners();
  
  // 自动移除 toast
  if (toast.duration !== 0) {
    setTimeout(() => {
      removeToast(toast.id);
    }, toast.duration || 5000);
  }
};

const removeToast = (toastId: string) => {
  const toast = globalToasts.find(t => t.id === toastId);
  if (toast?.onClose) {
    toast.onClose();
  }
  
  globalToasts = globalToasts.filter(t => t.id !== toastId);
  notifyListeners();
};

const removeAllToasts = () => {
  globalToasts.forEach(toast => {
    if (toast.onClose) {
      toast.onClose();
    }
  });
  globalToasts = [];
  notifyListeners();
};

export function useToast(): UseToastReturn {
  const [toasts, setToasts] = useState<Toast[]>(globalToasts);
  const listenerRef = useRef<(toasts: Toast[]) => void>();

  // 注册监听器
  if (!listenerRef.current) {
    listenerRef.current = (newToasts: Toast[]) => {
      setToasts(newToasts);
    };
    globalListeners.add(listenerRef.current);
  }

  // 清理监听器
  const cleanup = useCallback(() => {
    if (listenerRef.current) {
      globalListeners.delete(listenerRef.current);
    }
  }, []);

  // 显示 toast
  const toast = useCallback((options: ToastOptions): string => {
    const id = Math.random().toString(36).substring(2, 9);
    
    const newToast: Toast = {
      id,
      title: options.title,
      description: options.description,
      variant: options.variant || 'info',
      duration: options.duration,
      action: options.action,
    };

    addToast(newToast);
    return id;
  }, []);

  // 关闭指定 toast
  const dismiss = useCallback((toastId: string) => {
    removeToast(toastId);
  }, []);

  // 关闭所有 toast
  const dismissAll = useCallback(() => {
    removeAllToasts();
  }, []);

  return {
    toasts,
    toast,
    dismiss,
    dismissAll
  };
}

// 便捷方法
export const toast = {
  success: (title: string, description?: string, options?: Omit<ToastOptions, 'title' | 'description' | 'variant'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    addToast({
      id,
      title,
      description,
      variant: 'success',
      duration: options?.duration || 4000,
      action: options?.action
    });
    return id;
  },

  error: (title: string, description?: string, options?: Omit<ToastOptions, 'title' | 'description' | 'variant'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    addToast({
      id,
      title,
      description,
      variant: 'destructive',
      duration: options?.duration || 6000,
      action: options?.action
    });
    return id;
  },

  warning: (title: string, description?: string, options?: Omit<ToastOptions, 'title' | 'description' | 'variant'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    addToast({
      id,
      title,
      description,
      variant: 'warning',
      duration: options?.duration || 5000,
      action: options?.action
    });
    return id;
  },

  info: (title: string, description?: string, options?: Omit<ToastOptions, 'title' | 'description' | 'variant'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    addToast({
      id,
      title,
      description,
      variant: 'info',
      duration: options?.duration || 4000,
      action: options?.action
    });
    return id;
  },

  dismiss: (toastId: string) => {
    removeToast(toastId);
  },

  dismissAll: () => {
    removeAllToasts();
  }
};