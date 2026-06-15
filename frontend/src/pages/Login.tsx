import React, { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
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
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">登录</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium">用户名</label>
              <Input
                value={formData.username}
                onChange={(event) => setFormData((prev) => ({ ...prev, username: event.target.value }))}
                placeholder="请输入用户名"
                autoComplete="username"
                required
              />
            </div>
            <div>
              <div className="mb-1 flex items-center justify-between gap-3">
                <label className="block text-sm font-medium">密码</label>
                <Link to="/auth/forgot-password" className="text-sm text-blue-600 hover:text-blue-700 hover:underline">
                  忘记密码？
                </Link>
              </div>
              <Input
                type="password"
                value={formData.password}
                onChange={(event) => setFormData((prev) => ({ ...prev, password: event.target.value }))}
                placeholder="请输入密码"
                autoComplete="current-password"
                required
              />
            </div>
            {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '登录中...' : '登录'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export default Login
