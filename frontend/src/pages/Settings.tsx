import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api/client'

type TabKey = 'basic' | 'security' | 'email' | 'upload' | 'maintenance'

interface SettingsState {
  systemName: string
  systemVersion: string
  systemDescription: string
  passwordMinLength: number
  passwordRequireUppercase: boolean
  passwordRequireLowercase: boolean
  passwordRequireNumbers: boolean
  passwordRequireSymbols: boolean
  maxLoginAttempts: number
  accountLockoutDuration: number
  sessionTimeout: number
  jwtAccessTokenExpire: number
  jwtRefreshTokenExpire: number
  emailEnabled: boolean
  smtpHost: string
  smtpPort: number
  smtpUsername: string
  smtpPassword: string
  maxFileSize: number
  allowedFileTypes: string
  maintenanceMode: boolean
  maintenanceMessage: string
}

const defaultSettings: SettingsState = {
  systemName: 'AI自动化测试管理系统',
  systemVersion: 'v1.0.0',
  systemDescription: '基于 AI 的自动化测试管理平台',
  passwordMinLength: 8,
  passwordRequireUppercase: true,
  passwordRequireLowercase: true,
  passwordRequireNumbers: true,
  passwordRequireSymbols: true,
  maxLoginAttempts: 5,
  accountLockoutDuration: 30,
  sessionTimeout: 60,
  jwtAccessTokenExpire: 1,
  jwtRefreshTokenExpire: 7,
  emailEnabled: true,
  smtpHost: 'smtp.example.com',
  smtpPort: 587,
  smtpUsername: 'noreply@example.com',
  smtpPassword: '',
  maxFileSize: 10,
  allowedFileTypes: 'jpg,png,pdf,doc,docx,xls,xlsx',
  maintenanceMode: false,
  maintenanceMessage: '系统正在维护中，请稍后再试。',
}

const tabs: Array<{ id: TabKey; name: string }> = [
  { id: 'basic', name: '基础设置' },
  { id: 'security', name: '安全设置' },
  { id: 'email', name: '邮件设置' },
  { id: 'upload', name: '文件上传' },
  { id: 'maintenance', name: '系统维护' },
]

const passwordRequirements: Array<{
  key: 'passwordRequireUppercase' | 'passwordRequireLowercase' | 'passwordRequireNumbers' | 'passwordRequireSymbols'
  label: string
}> = [
  { key: 'passwordRequireUppercase', label: '要求大写字母' },
  { key: 'passwordRequireLowercase', label: '要求小写字母' },
  { key: 'passwordRequireNumbers', label: '要求数字' },
  { key: 'passwordRequireSymbols', label: '要求特殊字符' },
]

const normalizeSettings = (payload: any): SettingsState => ({
  ...defaultSettings,
  ...(payload?.settings || payload || {}),
})

const toNumber = (value: string, fallback: number) => {
  if (value === '') return fallback
  const nextValue = Number(value)
  return Number.isFinite(nextValue) ? nextValue : fallback
}

const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SettingsState>(defaultSettings)
  const [activeTab, setActiveTab] = useState<TabKey>('basic')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isResetting, setIsResetting] = useState(false)

  useEffect(() => {
    const loadSettings = async () => {
      setIsLoading(true)
      try {
        const response = await apiClient.get('/settings')
        setSettings(normalizeSettings(response.data))
      } catch (error) {
        console.error('Failed to load system settings:', error)
        toast.error('加载系统设置失败')
      } finally {
        setIsLoading(false)
      }
    }

    loadSettings()
  }, [])

  const updateSetting = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSettings((current) => ({ ...current, [key]: value }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const response = await apiClient.put('/settings', settings)
      setSettings(normalizeSettings(response.data))
      toast.success('设置已保存')
    } catch (error) {
      console.error('Failed to save system settings:', error)
      toast.error('保存系统设置失败')
    } finally {
      setIsSaving(false)
    }
  }

  const handleReset = async () => {
    if (!window.confirm('确定要重置所有设置吗？')) return

    setIsResetting(true)
    try {
      const response = await apiClient.post('/settings/reset')
      setSettings(normalizeSettings(response.data))
      toast.success('设置已重置')
    } catch (error) {
      console.error('Failed to reset system settings:', error)
      toast.error('重置系统设置失败')
    } finally {
      setIsResetting(false)
    }
  }

  const actionDisabled = isLoading || isSaving || isResetting

  if (isLoading) {
    return <div className="flex min-h-64 items-center justify-center text-gray-600 dark:text-gray-300">正在加载系统设置...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">系统设置</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">配置系统基础信息、安全策略、邮件、上传和维护参数</p>
        </div>
        <div className="flex items-center space-x-2">
          <button onClick={handleReset} disabled={actionDisabled} className="rounded-md bg-gray-600 px-4 py-2 text-white hover:bg-gray-700 disabled:opacity-50">
            {isResetting ? '重置中...' : '重置'}
          </button>
          <button onClick={handleSave} disabled={actionDisabled} className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50">
            {isSaving ? '保存中...' : '保存设置'}
          </button>
        </div>
      </div>

      <div className="rounded-lg bg-white shadow dark:bg-gray-800">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex flex-wrap gap-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`border-b-2 px-1 py-4 text-sm font-medium ${
                  activeTab === tab.id ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'basic' && (
            <Section title="基础设置">
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <TextField label="系统名称" value={settings.systemName} onChange={(value) => updateSetting('systemName', value)} />
                <TextField label="系统版本" value={settings.systemVersion} onChange={(value) => updateSetting('systemVersion', value)} />
                <TextAreaField label="系统描述" value={settings.systemDescription} onChange={(value) => updateSetting('systemDescription', value)} className="md:col-span-2" />
              </div>
            </Section>
          )}

          {activeTab === 'security' && (
            <Section title="安全设置">
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <NumberField label="密码最小长度" min={6} max={20} value={settings.passwordMinLength} onChange={(value) => updateSetting('passwordMinLength', toNumber(value, 8))} />
                <NumberField label="最大登录尝试次数" min={3} max={10} value={settings.maxLoginAttempts} onChange={(value) => updateSetting('maxLoginAttempts', toNumber(value, 5))} />
                <NumberField label="账号锁定时长（分钟）" min={5} max={1440} value={settings.accountLockoutDuration} onChange={(value) => updateSetting('accountLockoutDuration', toNumber(value, 30))} />
                <NumberField label="会话超时时间（分钟）" min={15} max={480} value={settings.sessionTimeout} onChange={(value) => updateSetting('sessionTimeout', toNumber(value, 60))} />
              </div>

              <div className="space-y-3">
                <h4 className="text-md font-medium text-gray-900 dark:text-white">密码复杂度要求</h4>
                {passwordRequirements.map((item) => (
                  <CheckboxRow key={item.key} checked={settings[item.key]} onChange={(checked) => updateSetting(item.key, checked)}>
                    {item.label}
                  </CheckboxRow>
                ))}
              </div>
            </Section>
          )}

          {activeTab === 'email' && (
            <Section title="邮件设置">
              <CheckboxRow checked={settings.emailEnabled} onChange={(checked) => updateSetting('emailEnabled', checked)}>
                启用邮件功能
              </CheckboxRow>

              {settings.emailEnabled && (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <TextField label="SMTP 服务器" value={settings.smtpHost} onChange={(value) => updateSetting('smtpHost', value)} />
                  <NumberField label="SMTP 端口" value={settings.smtpPort} onChange={(value) => updateSetting('smtpPort', toNumber(value, 587))} />
                  <TextField label="用户名" value={settings.smtpUsername} onChange={(value) => updateSetting('smtpUsername', value)} />
                  <TextField label="密码" type="password" value={settings.smtpPassword} placeholder="留空则不设置" onChange={(value) => updateSetting('smtpPassword', value)} />
                </div>
              )}
            </Section>
          )}

          {activeTab === 'upload' && (
            <Section title="文件上传设置">
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <NumberField label="最大文件大小（MB）" min={1} max={100} value={settings.maxFileSize} onChange={(value) => updateSetting('maxFileSize', toNumber(value, 10))} />
                <TextField label="允许的文件类型" value={settings.allowedFileTypes} placeholder="jpg,png,pdf,doc,docx" onChange={(value) => updateSetting('allowedFileTypes', value)} help="用英文逗号分隔多个文件类型" />
              </div>
            </Section>
          )}

          {activeTab === 'maintenance' && (
            <Section title="系统维护">
              <CheckboxRow checked={settings.maintenanceMode} onChange={(checked) => updateSetting('maintenanceMode', checked)}>
                启用维护模式
              </CheckboxRow>

              {settings.maintenanceMode && (
                <TextAreaField label="维护提示信息" value={settings.maintenanceMessage} onChange={(value) => updateSetting('maintenanceMessage', value)} />
              )}

              <div className="rounded-md border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
                启用维护模式后，除管理员外的用户将无法访问系统，并会看到维护提示信息。
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  )
}

const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <div className="space-y-6">
    <h3 className="text-lg font-medium text-gray-900 dark:text-white">{title}</h3>
    {children}
  </div>
)

const FieldShell = ({ label, children, className = '', help }: { label: string; children: React.ReactNode; className?: string; help?: string }) => (
  <label className={`block ${className}`}>
    <span className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
    {children}
    {help && <p className="mt-1 text-xs text-gray-500">{help}</p>}
  </label>
)

const inputClass = 'w-full rounded-md border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500'

const TextField = ({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  help,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  placeholder?: string
  help?: string
}) => (
  <FieldShell label={label} help={help}>
    <input type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} className={inputClass} />
  </FieldShell>
)

const NumberField = ({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string
  value: number
  onChange: (value: string) => void
  min?: number
  max?: number
}) => (
  <FieldShell label={label}>
    <input type="number" min={min} max={max} value={value} onChange={(event) => onChange(event.target.value)} className={inputClass} />
  </FieldShell>
)

const TextAreaField = ({
  label,
  value,
  onChange,
  className,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  className?: string
}) => (
  <FieldShell label={label} className={className}>
    <textarea value={value} onChange={(event) => onChange(event.target.value)} rows={3} className={inputClass} />
  </FieldShell>
)

const CheckboxRow = ({ checked, onChange, children }: { checked: boolean; onChange: (checked: boolean) => void; children: React.ReactNode }) => (
  <label className="flex items-center text-sm text-gray-700 dark:text-gray-300">
    <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="mr-2" />
    {children}
  </label>
)

export default Settings
