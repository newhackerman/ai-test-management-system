import React, { useEffect, useState } from 'react'
import { AlertTriangle, Copy, Key, Shield, Smartphone } from 'lucide-react'

import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/AlertDialog'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { useToast } from '@/hooks/useToast'
import { authService } from '@/services/auth-service'

interface MFAStatus {
  enabled: boolean
  backup_codes_count: number
}

interface MFASetup {
  secret: string
  qr_code: string
  backup_codes: string[]
  setup_complete: boolean
}

const authHeaders = () => ({
  Authorization: `Bearer ${authService.getAccessToken()}`,
})

const MFASettings: React.FC = () => {
  const [mfaStatus, setMfaStatus] = useState<MFAStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [setupData, setSetupData] = useState<MFASetup | null>(null)
  const [isSetupOpen, setIsSetupOpen] = useState(false)
  const [isDisableOpen, setIsDisableOpen] = useState(false)
  const [verificationCode, setVerificationCode] = useState('')
  const [password, setPassword] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const { toast } = useToast()

  const loadMFAStatus = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('/api/v1/auth/mfa/status', {
        headers: authHeaders(),
      })

      if (!response.ok) {
        throw new Error('load mfa status failed')
      }

      setMfaStatus(await response.json())
    } catch (error) {
      console.error('Failed to load MFA status:', error)
      toast({
        variant: 'destructive',
        title: '获取失败',
        description: '无法获取 MFA 状态',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadMFAStatus()
  }, [])

  const startMFASetup = async () => {
    try {
      setIsProcessing(true)
      const response = await fetch('/api/v1/auth/mfa/setup', {
        method: 'POST',
        headers: authHeaders(),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'setup failed')
      }

      setSetupData(await response.json())
      setIsSetupOpen(true)
    } catch (error) {
      console.error('Failed to start MFA setup:', error)
      toast({
        variant: 'destructive',
        title: '设置失败',
        description: '无法启动 MFA 设置',
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const enableMFA = async () => {
    if (!setupData || verificationCode.length !== 6) {
      toast({
        variant: 'destructive',
        title: '输入错误',
        description: '请输入 6 位验证码',
      })
      return
    }

    try {
      setIsProcessing(true)
      const response = await fetch('/api/v1/auth/mfa/enable', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          secret: setupData.secret,
          token: verificationCode,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'enable failed')
      }

      const result = await response.json()
      toast({ title: '启用成功', description: result.message || 'MFA 已启用' })
      setIsSetupOpen(false)
      setVerificationCode('')
      await loadMFAStatus()
    } catch (error) {
      console.error('Failed to enable MFA:', error)
      toast({
        variant: 'destructive',
        title: '启用失败',
        description: '验证码错误或已过期',
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const disableMFA = async () => {
    if (!password) {
      toast({
        variant: 'destructive',
        title: '密码必填',
        description: '请输入当前密码',
      })
      return
    }

    try {
      setIsProcessing(true)
      const response = await fetch('/api/v1/auth/mfa/disable', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({ password }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'disable failed')
      }

      const result = await response.json()
      toast({ title: '禁用成功', description: result.message || 'MFA 已禁用' })
      setIsDisableOpen(false)
      setPassword('')
      await loadMFAStatus()
    } catch (error) {
      console.error('Failed to disable MFA:', error)
      toast({
        variant: 'destructive',
        title: '禁用失败',
        description: '密码错误或操作失败',
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text)
    toast({ title: '复制成功', description: '已复制到剪贴板' })
  }

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-gray-900" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-6">
        <h1 className="flex items-center space-x-2 text-2xl font-bold">
          <Shield className="h-6 w-6" />
          <span>多因素认证 (MFA)</span>
        </h1>
        <p className="mt-2 text-gray-600">为账号增加额外安全保护。</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>MFA 状态</span>
            <Badge variant={mfaStatus?.enabled ? 'default' : 'secondary'}>
              {mfaStatus?.enabled ? '已启用' : '未启用'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {!mfaStatus?.enabled ? (
            <>
              <div className="flex items-start space-x-4">
                <Smartphone className="mt-1 h-8 w-8 text-blue-500" />
                <div>
                  <h3 className="font-medium">保护您的账号</h3>
                  <p className="mt-1 text-gray-600">
                    启用 MFA 后，登录时除了密码，还需要输入身份验证应用生成的动态验证码。
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-gray-500">
                    <li>防止未授权访问</li>
                    <li>即使密码泄露，账号仍有额外保护</li>
                    <li>支持 Google Authenticator、Authy 等应用</li>
                  </ul>
                </div>
              </div>

              <Dialog open={isSetupOpen} onOpenChange={setIsSetupOpen}>
                <DialogTrigger asChild>
                  <Button onClick={startMFASetup} disabled={isProcessing}>
                    {isProcessing ? '设置中...' : '启用 MFA'}
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-md">
                  <DialogHeader>
                    <DialogTitle>设置多因素认证</DialogTitle>
                    <DialogDescription>按步骤完成 MFA 绑定。</DialogDescription>
                  </DialogHeader>

                  {setupData && (
                    <div className="space-y-4">
                      <div>
                        <h4 className="mb-2 font-medium">1. 扫描二维码</h4>
                        <div className="flex justify-center">
                          <div
                            className="rounded-lg border bg-white p-4"
                            dangerouslySetInnerHTML={{ __html: setupData.qr_code }}
                          />
                        </div>
                      </div>

                      <div>
                        <h4 className="mb-2 font-medium">2. 手动输入密钥</h4>
                        <div className="flex items-center space-x-2">
                          <Input value={setupData.secret} readOnly className="font-mono text-sm" />
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => copyToClipboard(setupData.secret)}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="verification-code">3. 输入 6 位验证码</Label>
                        <Input
                          id="verification-code"
                          value={verificationCode}
                          onChange={(event) => setVerificationCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                          placeholder="000000"
                          maxLength={6}
                          inputMode="numeric"
                        />
                      </div>

                      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                        <div className="flex items-start space-x-2 text-sm">
                          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
                          <p className="text-amber-700">
                            启用后请妥善保存备用代码，以防无法访问身份验证应用。
                          </p>
                        </div>
                      </div>

                      <div className="flex justify-end space-x-2">
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => {
                            setIsSetupOpen(false)
                            setVerificationCode('')
                          }}
                        >
                          取消
                        </Button>
                        <Button
                          type="button"
                          onClick={enableMFA}
                          disabled={verificationCode.length !== 6 || isProcessing}
                        >
                          {isProcessing ? '验证中...' : '启用 MFA'}
                        </Button>
                      </div>
                    </div>
                  )}
                </DialogContent>
              </Dialog>
            </>
          ) : (
            <>
              <div className="flex items-center space-x-3 rounded-lg border border-green-200 bg-green-50 p-4">
                <Shield className="h-6 w-6 text-green-600" />
                <div>
                  <h3 className="font-medium text-green-800">MFA 已启用</h3>
                  <p className="text-sm text-green-600">您的账号受到多因素认证保护。</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="mb-2 font-medium">备用代码</h4>
                  <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                    <div>
                      <p className="text-sm">剩余备用代码：{mfaStatus?.backup_codes_count || 0} 个</p>
                      <p className="text-xs text-gray-600">备用代码用于无法使用验证应用时登录。</p>
                    </div>
                    <Button type="button" size="sm" variant="outline">
                      <Key className="mr-1 h-4 w-4" />
                      重新生成
                    </Button>
                  </div>
                </div>

                <AlertDialog open={isDisableOpen} onOpenChange={setIsDisableOpen}>
                  <AlertDialogTrigger asChild>
                    <Button type="button" variant="destructive" size="sm">
                      禁用 MFA
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>确认禁用 MFA</AlertDialogTitle>
                      <AlertDialogDescription className="space-y-2">
                        <p>禁用多因素认证会降低账号安全性。</p>
                        <p>请输入当前密码确认操作。</p>
                        <Input
                          type="password"
                          placeholder="请输入密码"
                          value={password}
                          onChange={(event) => setPassword(event.target.value)}
                        />
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel onClick={() => setPassword('')}>取消</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={disableMFA}
                        disabled={!password || isProcessing}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        {isProcessing ? '禁用中...' : '确认禁用'}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default MFASettings
