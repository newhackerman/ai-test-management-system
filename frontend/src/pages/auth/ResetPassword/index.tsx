import React, { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, KeyRound, Loader2, Lock } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

const getErrorMessage = (payload: any) => {
  const detail = payload?.detail ?? payload?.message
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || String(item)).join('; ')
  return '密码重置失败，请确认链接是否有效。'
}

const passwordChecks = [
  { label: '至少 8 个字符', test: (value: string) => value.length >= 8 },
  { label: '包含大写字母', test: (value: string) => /[A-Z]/.test(value) },
  { label: '包含小写字母', test: (value: string) => /[a-z]/.test(value) },
  { label: '包含数字', test: (value: string) => /\d/.test(value) },
  { label: '包含特殊字符', test: (value: string) => /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(value) },
]

const ResetPasswordPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  // 令牌已被服务端判定为无效/已使用/已过期时为 true，禁用重试并引导重新申请
  const [tokenInvalid, setTokenInvalid] = useState(false)

  const passedCount = useMemo(() => passwordChecks.filter((item) => item.test(password)).length, [password])
  const isPasswordValid = passedCount === passwordChecks.length
  const progress = Math.round((passedCount / passwordChecks.length) * 100)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)

    if (!token) {
      setError('重置链接缺少 token，请重新申请重置邮件。')
      return
    }
    if (!isPasswordValid) {
      setError('新密码不符合安全规则。')
      return
    }
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致。')
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        // 429：速率限制触发，展示提示并尊重 Retry-After
        if (response.status === 429) {
          const retryAfter = Number(response.headers.get('retry-after'))
          const suffix = Number.isFinite(retryAfter) && retryAfter > 0
            ? `请在 ${Math.ceil(retryAfter)} 秒后重试。`
            : '请稍后重试。'
          setError(getErrorMessage(data) || `重置请求过于频繁，${suffix}`)
          return
        }
        // 400：令牌无效/已使用/已过期 —— 标记为不可重试，引导重新申请
        const message = getErrorMessage(data)
        if (response.status === 400) {
          setError(`${message} 为安全起见，该链接已失效，请重新申请重置邮件。`)
          setTokenInvalid(true)
        } else {
          setError(message)
        }
        return
      }

      setDone(true)
      window.setTimeout(() => navigate('/login'), 1200)
    } catch (err: any) {
      setError(err?.message || '网络连接异常，请稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">重置密码</CardTitle>
          <CardDescription className="text-center">设置一个新的登录密码，提交后原重置链接会立即失效。</CardDescription>
        </CardHeader>
        <CardContent>
          {!token ? (
            <div className="space-y-5 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-600">
                <KeyRound className="h-6 w-6" />
              </div>
              <p className="text-sm leading-6 text-gray-600">当前重置链接无效，请重新申请密码重置邮件。</p>
              <Button asChild className="w-full">
                <Link to="/auth/forgot-password">重新申请重置邮件</Link>
              </Button>
            </div>
          ) : done ? (
            <div className="space-y-5 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <p className="text-sm leading-6 text-gray-600">密码已重置成功，正在返回登录页。</p>
              <Button asChild className="w-full">
                <Link to="/login">立即登录</Link>
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">新密码</label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="pl-9"
                    placeholder="请输入新密码"
                    autoComplete="new-password"
                    required
                  />
                </div>
              </div>
              <div className="space-y-2 rounded-md bg-gray-50 p-3">
                <div className="h-1.5 overflow-hidden rounded-full bg-gray-200">
                  <div className="h-full bg-blue-600 transition-all" style={{ width: `${progress}%` }} />
                </div>
                <div className="grid grid-cols-1 gap-1 text-xs text-gray-600">
                  {passwordChecks.map((item) => {
                    const passed = item.test(password)
                    return (
                      <span key={item.label} className={passed ? 'text-emerald-600' : 'text-gray-500'}>
                        {passed ? '✓' : '•'} {item.label}
                      </span>
                    )
                  })}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">确认密码</label>
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="请再次输入新密码"
                  autoComplete="new-password"
                  required
                />
              </div>
              {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
              <Button type="submit" className="w-full" disabled={loading || tokenInvalid}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                重置密码
              </Button>
              {tokenInvalid && (
                <Button asChild className="w-full">
                  <Link to="/auth/forgot-password">重新申请重置邮件</Link>
                </Button>
              )}
              <Button asChild variant="ghost" className="w-full">
                <Link to="/login">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  返回登录
                </Link>
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default ResetPasswordPage
