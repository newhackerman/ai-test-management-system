import React, { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { useAuth } from '@/stores/auth'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

const normalizeError = (detail: any) => {
  if (!detail) return '登录失败，请检查用户名和密码。'
  if (typeof detail === 'string') return detail
  if (typeof detail.message === 'string') return detail.message
  if (typeof detail.detail === 'string') return detail.detail
  return '登录失败，请检查用户名和密码。'
}

const normalizeUser = (data: any, usernameFallback: string) => {
  const rawUser = data.user || data.user_info || {}
  const username = rawUser.username || data.username || usernameFallback
  const roles = rawUser.roles || data.roles || []
  const roleCode = rawUser.role || data.role || roles?.[0]?.code || (rawUser.is_superuser ? 'admin' : 'USER')
  const isAdmin = roleCode === 'admin' || roleCode === 'ADMIN' || rawUser.is_superuser || rawUser.is_super_admin

  return {
    id: Number(rawUser.id || rawUser.user_id || data.user_id || data.id || 0),
    username,
    email: rawUser.email || data.email || '',
    real_name: rawUser.real_name || rawUser.nickname || username,
    nickname: rawUser.nickname || '',
    phone: rawUser.phone || '',
    avatar: rawUser.avatar || '',
    role: roleCode,
    status: rawUser.status || 'active',
    is_active: rawUser.is_active !== false,
    permissions: rawUser.permissions || data.permissions || (isAdmin ? [{ code: '*', name: '全部权限' }] : []),
    roles: roles.length ? roles : [{ code: roleCode, name: isAdmin ? '管理员' : roleCode }],
    is_super_admin: Boolean(isAdmin),
    isSuperAdmin: Boolean(isAdmin),
    created_at: rawUser.created_at || new Date().toISOString(),
    updated_at: rawUser.updated_at || new Date().toISOString(),
    last_login_at: rawUser.last_login_at,
  }
}

const Login: React.FC = () => {
  const location = useLocation()
  const { isAuthenticated, login } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({ username: '', password: '' })

  if (isAuthenticated) {
    const from = (location.state as any)?.from || '/'
    return <Navigate to={from} replace />
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: formData.username.trim(),
          password: formData.password,
          remember_me: false,
        }),
      })

      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(normalizeError(data.detail || data))
        return
      }

      const accessToken = data.access_token || data.token || data.accessToken
      if (!accessToken) {
        setError('登录响应缺少访问令牌。')
        return
      }

      login(normalizeUser(data, formData.username.trim()) as any, accessToken, data.refresh_token || data.refreshToken || '')
    } catch (err: any) {
      setError(err?.message || '登录失败，请检查网络连接。')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* 左側品牌面板 — 桌面端可见 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary/90 via-primary to-primary-800 dark:from-primary-800 dark:via-primary-900 dark:to-background items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
        <div className="relative z-10 text-center px-8">
          <div className="inline-flex h-20 w-20 items-center justify-center rounded-2xl bg-white/20 backdrop-blur mb-6 shadow-lg dark:bg-white/10">
            <span className="text-3xl font-bold text-white">AI</span>
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight">AI 测试管理系统</h1>
          <p className="mt-4 text-lg text-white/80 max-w-md mx-auto">
            智能化测试管理平台，覆盖测试计划、用例管理、缺陷跟踪与报告分析全流程
          </p>
          <div className="mt-10 flex items-center justify-center gap-8 text-white/60 text-sm">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-emerald-400" />
              <span>自动化测试</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-amber-400" />
              <span>性能监控</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-sky-400" />
              <span>AI 辅助</span>
            </div>
          </div>
        </div>
      </div>

      {/* 右側登錄表單 */}
      <div className="flex w-full lg:w-1/2 items-center justify-center bg-background px-4 sm:px-8">
        <div className="w-full max-w-sm">
          {/* 移動端 logo */}
          <div className="mb-8 text-center lg:hidden">
            <div className="inline-flex h-14 w-14 items-center justify-center rounded-xl bg-primary mb-3">
              <span className="text-2xl font-bold text-primary-foreground">AI</span>
            </div>
            <h1 className="text-2xl font-bold text-foreground">AI 测试管理</h1>
          </div>

          <Card className="border-0 shadow-none sm:border sm:shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-center text-xl">欢迎回来</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="username" className="mb-1.5">用户名</Label>
                  <Input
                    id="username"
                    value={formData.username}
                    onChange={(event) => setFormData((prev) => ({ ...prev, username: event.target.value }))}
                    placeholder="请输入用户名"
                    autoComplete="username"
                    required
                    className="h-11"
                  />
                </div>
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <Label htmlFor="password">密码</Label>
                    <Link to="/auth/forgot-password" className="text-xs text-primary hover:text-primary/80 hover:underline transition-colors">
                      忘记密码？
                    </Link>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(event) => setFormData((prev) => ({ ...prev, password: event.target.value }))}
                    placeholder="请输入密码"
                    autoComplete="current-password"
                    required
                    className="h-11"
                  />
                </div>

                {error && (
                  <div className="flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2.5 text-sm text-destructive border border-destructive/20">
                    <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <Button
                  type="submit"
                  className="h-11 w-full text-base"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      登录中...
                    </>
                  ) : (
                    '登录'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            © 2026 AI Test Management System
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login
