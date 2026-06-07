// @ts-nocheck
import { useState } from 'react'
import { Copy, Eye, EyeOff, Globe, Lock, Share2, Users } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Switch } from '@/components/ui/Switch'
import { Textarea } from '@/components/ui/Textarea'
import { cn } from '@/lib/utils'

interface TemplateShareDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  template: {
    id: number
    name: string
    title: string
    description?: string
  }
  onShare?: (shareData: any) => void
}

type ShareType = 'PUBLIC' | 'TEAM' | 'PRIVATE'

interface ShareSettings {
  shareType: ShareType
  title: string
  description: string
  password: string
  passwordEnabled: boolean
  expiresAt: string
  expiresEnabled: boolean
  maxAccessCount: number | null
  accessLimitEnabled: boolean
  allowDownload: boolean
  allowCopy: boolean
  allowComment: boolean
  requireLogin: boolean
}

const shareTypeMeta = {
  PUBLIC: { label: '公开分享', description: '任何人都可以通过链接访问', icon: Globe },
  TEAM: { label: '团队分享', description: '仅团队成员可以访问', icon: Users },
  PRIVATE: { label: '私有分享', description: '仅指定用户可以访问', icon: Lock },
}

export function TemplateShareDialog({ open, onOpenChange, template, onShare }: TemplateShareDialogProps) {
  const [settings, setSettings] = useState<ShareSettings>({
    shareType: 'PUBLIC',
    title: template.title,
    description: template.description || '',
    password: '',
    passwordEnabled: false,
    expiresAt: '',
    expiresEnabled: false,
    maxAccessCount: null,
    accessLimitEnabled: false,
    allowDownload: true,
    allowCopy: true,
    allowComment: true,
    requireLogin: false,
  })

  const [showPassword, setShowPassword] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [shareUrl, setShareUrl] = useState<string | null>(null)

  const updateSettings = (patch: Partial<ShareSettings>) => {
    setSettings((prev) => ({ ...prev, ...patch }))
  }

  const handleCreateShare = async () => {
    setIsCreating(true)
    try {
      const shareData = {
        share_type: settings.shareType,
        title: settings.title,
        description: settings.description,
        password: settings.passwordEnabled ? settings.password || null : null,
        expires_at: settings.expiresEnabled && settings.expiresAt ? new Date(settings.expiresAt).toISOString() : null,
        max_access_count: settings.accessLimitEnabled ? settings.maxAccessCount : null,
        allow_download: settings.allowDownload,
        allow_copy: settings.allowCopy,
        allow_comment: settings.allowComment,
        require_login: settings.requireLogin,
      }

      const response = await fetch(`/api/v1/template-sharing/templates/${template.id}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(shareData),
      })

      if (!response.ok) throw new Error('创建分享失败')

      const result = await response.json()
      const generatedUrl =
        result.share_url ||
        `${window.location.origin}/shared/templates/${result.share_code || result.id || template.id}`

      setShareUrl(generatedUrl)
      onShare?.(result)
      toast.success('分享链接创建成功')
    } catch (error) {
      console.error('创建分享失败:', error)
      toast.error('创建分享失败，请重试')
    } finally {
      setIsCreating(false)
    }
  }

  const handleCopyUrl = async () => {
    if (!shareUrl) return
    await navigator.clipboard.writeText(shareUrl)
    toast.success('分享链接已复制到剪贴板')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            分享模板
          </DialogTitle>
          <DialogDescription>创建分享链接，让其他人可以访问和使用模板。</DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div className="space-y-4">
            <div>
              <Label htmlFor="share-title">分享标题</Label>
              <Input id="share-title" value={settings.title} onChange={(event) => updateSettings({ title: event.target.value })} />
            </div>
            <div>
              <Label htmlFor="share-description">分享描述</Label>
              <Textarea
                id="share-description"
                value={settings.description}
                onChange={(event) => updateSettings({ description: event.target.value })}
                rows={3}
              />
            </div>
          </div>

          <div>
            <Label>分享类型</Label>
            <div className="mt-2 grid grid-cols-1 gap-3">
              {(Object.keys(shareTypeMeta) as ShareType[]).map((type) => {
                const meta = shareTypeMeta[type]
                const Icon = meta.icon
                return (
                  <button
                    key={type}
                    type="button"
                    className={cn(
                      'flex items-center gap-3 rounded-lg border p-3 text-left transition-colors',
                      settings.shareType === type ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/50',
                    )}
                    onClick={() => updateSettings({ shareType: type })}
                  >
                    <Icon className="h-4 w-4" />
                    <div>
                      <div className="font-medium">{meta.label}</div>
                      <div className="text-sm text-muted-foreground">{meta.description}</div>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="font-medium">访问控制</h4>

            <SettingSwitch
              label="密码保护"
              description="访问者需要输入密码"
              checked={settings.passwordEnabled}
              onCheckedChange={(checked) => updateSettings({ passwordEnabled: checked, password: checked ? settings.password : '' })}
            />
            {settings.passwordEnabled && (
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={settings.password}
                  onChange={(event) => updateSettings({ password: event.target.value })}
                  placeholder="输入访问密码"
                />
                <Button type="button" variant="ghost" size="sm" className="absolute right-0 top-0 h-full px-3" onClick={() => setShowPassword((value) => !value)}>
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            )}

            <SettingSwitch
              label="设置过期时间"
              description="链接将在指定时间后失效"
              checked={settings.expiresEnabled}
              onCheckedChange={(checked) => updateSettings({ expiresEnabled: checked })}
            />
            {settings.expiresEnabled && (
              <Input type="datetime-local" value={settings.expiresAt} onChange={(event) => updateSettings({ expiresAt: event.target.value })} />
            )}

            <SettingSwitch
              label="限制访问次数"
              description="设置链接最大访问次数"
              checked={settings.accessLimitEnabled}
              onCheckedChange={(checked) => updateSettings({ accessLimitEnabled: checked, maxAccessCount: checked ? settings.maxAccessCount || 100 : null })}
            />
            {settings.accessLimitEnabled && (
              <Input
                type="number"
                min="1"
                value={settings.maxAccessCount || ''}
                onChange={(event) => updateSettings({ maxAccessCount: Number(event.target.value) || null })}
              />
            )}

            <SettingSwitch label="需要登录" description="访问者必须登录后才能查看" checked={settings.requireLogin} onCheckedChange={(checked) => updateSettings({ requireLogin: checked })} />
          </div>

          <div className="space-y-3">
            <h4 className="font-medium">权限设置</h4>
            <SettingSwitch label="允许下载" description="访问者可以下载模板文件" checked={settings.allowDownload} onCheckedChange={(checked) => updateSettings({ allowDownload: checked })} />
            <SettingSwitch label="允许复制" description="访问者可以复制模板内容" checked={settings.allowCopy} onCheckedChange={(checked) => updateSettings({ allowCopy: checked })} />
            <SettingSwitch label="允许评论" description="访问者可以添加评论和反馈" checked={settings.allowComment} onCheckedChange={(checked) => updateSettings({ allowComment: checked })} />
          </div>

          {shareUrl && (
            <div className="space-y-3 rounded-lg bg-muted/50 p-4">
              <h4 className="font-medium text-green-600">分享链接已创建</h4>
              <div className="flex items-center gap-2">
                <Input value={shareUrl} readOnly className="flex-1" />
                <Button type="button" variant="outline" size="sm" onClick={handleCopyUrl}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          {!shareUrl ? (
            <Button onClick={handleCreateShare} disabled={isCreating || !settings.title.trim()}>
              {isCreating ? '创建中...' : '创建分享链接'}
            </Button>
          ) : (
            <Button onClick={() => onOpenChange(false)}>完成</Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function SettingSwitch({
  label,
  description,
  checked,
  onCheckedChange,
}: {
  label: string
  description: string
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <Label>{label}</Label>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  )
}
