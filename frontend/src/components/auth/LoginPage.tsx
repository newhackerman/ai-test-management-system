// @ts-nocheck
import React, { useRef, useState } from 'react';
import { AlertCircle, Eye, EyeOff, Lock, User } from 'lucide-react';

import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Loading } from '@/components/ui/Loading';
import { authService } from '@/services/auth-service';
import { useAuthStore } from '@/stores/auth';

interface LoginFormData {
  username: string;
  password: string;
  rememberMe: boolean;
}

export const LoginPage: React.FC = () => {
  const { login } = useAuthStore();
  const [formData, setFormData] = useState<LoginFormData>({
    username: '',
    password: '',
    rememberMe: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<{ username?: string; password?: string }>({});
  const lastSubmitTimeRef = useRef(0);

  const validateForm = () => {
    const errors: typeof validationErrors = {};

    if (!formData.username.trim()) {
      errors.username = '请输入用户名';
    }

    if (!formData.password.trim()) {
      errors.password = '请输入密码';
    } else if (formData.password.length < 3) {
      errors.password = '密码长度至少 3 位';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (field: keyof LoginFormData) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = field === 'rememberMe' ? event.target.checked : event.target.value;
    setFormData((prev) => ({ ...prev, [field]: value }));
    setValidationErrors((prev) => ({ ...prev, [field]: undefined }));
    setError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (isSubmitting) return;
    const now = Date.now();
    if (now - lastSubmitTimeRef.current < 1000) return;
    lastSubmitTimeRef.current = now;

    if (!validateForm()) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await authService.login({
        username: formData.username.trim(),
        password: formData.password,
        rememberMe: formData.rememberMe,
      });
      login(response.user, response.accessToken, response.refreshToken);
    } catch (err: any) {
      setError(err?.message || '登录失败，请检查用户名和密码');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4 dark:from-gray-900 dark:to-gray-800">
      <Card className="w-full max-w-md space-y-6 p-8 shadow-xl">
        <div className="space-y-2 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-600">
            <Lock className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AI 测试自动化平台</h1>
          <p className="text-gray-600 dark:text-gray-400">请登录您的账号</p>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <div>
              <h4 className="font-medium">登录失败</h4>
              <p className="text-sm">{error}</p>
            </div>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">用户名</Label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              <Input
                id="username"
                type="text"
                placeholder="请输入用户名"
                value={formData.username}
                onChange={handleInputChange('username')}
                className={`pl-10 ${validationErrors.username ? 'border-red-500' : ''}`}
                disabled={isSubmitting}
                autoComplete="username"
                autoFocus
              />
            </div>
            {validationErrors.username && <p className="text-sm text-red-500 dark:text-red-400">{validationErrors.username}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">密码</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="请输入密码"
                value={formData.password}
                onChange={handleInputChange('password')}
                className={`pl-10 pr-10 ${validationErrors.password ? 'border-red-500' : ''}`}
                disabled={isSubmitting}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 dark:text-gray-400"
                disabled={isSubmitting}
                aria-label={showPassword ? '隐藏密码' : '显示密码'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {validationErrors.password && <p className="text-sm text-red-500 dark:text-red-400">{validationErrors.password}</p>}
          </div>

          <div className="flex items-center space-x-2">
            <input
              id="rememberMe"
              type="checkbox"
              checked={formData.rememberMe}
              onChange={handleInputChange('rememberMe')}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:text-blue-400"
              disabled={isSubmitting}
            />
            <Label htmlFor="rememberMe" className="text-sm text-gray-600 dark:text-gray-400">
              记住我
            </Label>
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting} size="lg">
            {isSubmitting ? (
              <>
                <Loading className="mr-2 h-4 w-4" />
                登录中...
              </>
            ) : (
              '登录'
            )}
          </Button>
        </form>

        <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
          <h4 className="mb-2 text-sm font-medium text-blue-800 dark:text-blue-200">测试账号</h4>
          <div className="space-y-1 text-xs text-blue-600 dark:text-blue-300">
            <p>
              用户名：<code className="rounded bg-blue-100 px-1 dark:bg-blue-800">admin</code>
            </p>
            <p>
              密码：<code className="rounded bg-blue-100 px-1 dark:bg-blue-800">admin123</code>
            </p>
          </div>
        </div>

        <div className="text-center text-xs text-gray-500 dark:text-gray-400">
          © 2026 AI 测试自动化平台. All rights reserved.
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
