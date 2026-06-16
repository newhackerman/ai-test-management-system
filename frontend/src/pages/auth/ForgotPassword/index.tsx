import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Loader2, Mail } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

// 客户端冷却时间（秒），防止短时间内反复触发重置邮件
const RESEND_COOLDOWN_SECONDS = 60

const getErrorMessage = (payload: any) => {
  const detail = payload?.detail ?? payload?.message
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || String(item)).join('; ')
  return '重置邮件发送失败，请稍后重试。'
}

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  // 冷却倒计时：>0 时禁用"重新发送"，避免邮件轰炸
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setInterval(() => setCooldown((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [cooldown])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      })
      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        // 429：后端速率限制触发，尊重 Retry-After 头，同步前端冷却
        if (response.status === 429) {
          const retryAfter = Number(response.headers.get('retry-after'))
          if (Number.isFinite(retryAfter) && retryAfter > 0) {
            setCooldown(Math.min(Math.ceil(retryAfter), 3600))
          }
          setError(getErrorMessage(data) || '请求过于频繁，请稍后再试。')
        } else {
          setError(getErrorMessage(data))
        }
        return
      }

      setSent(true)
      // 成功发送后启动冷却倒计时
      setCooldown(RESEND_COOLDOWN_SECONDS)
    } catch (err: any) {
      setError(err?.message || '网络连接异常，请稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = () => {
    if (cooldown > 0 || loading) return
    setSent(false)
    setError(null)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-800/50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">忘记密码</CardTitle>
          <CardDescription className="text-center">
            输入账号邮箱后，系统会发送一封密码重置邮件。
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="space-y-5 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div className="space-y-2">
                <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">请检查邮箱</h2>
                <p className="text-sm leading-6 text-gray-600 dark:text-gray-400">
                  如果该邮箱已注册，重置链接会发送到 <span className="font-medium text-gray-900 dark:text-gray-100">{email}</span>。
                  链接 30 分钟内有效，也请检查垃圾邮件文件夹。
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <Button type="button" variant="outline" onClick={handleResend} disabled={cooldown > 0}>
                  {cooldown > 0 ? `重新发送（${cooldown}s）` : '重新发送邮件'}
                </Button>
                <Button asChild variant="ghost">
                  <Link to="/login">返回登录</Link>
                </Button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">邮箱</label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
                  <Input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="pl-9"
                    placeholder="请输入注册邮箱"
                    autoComplete="email"
                    required
                  />
                </div>
              </div>
              {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:text-red-400 dark:bg-red-900/20">{error}</div>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                发送重置邮件
              </Button>
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

export default ForgotPasswordPage
