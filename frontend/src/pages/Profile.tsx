import React, { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { apiClient } from '@/services/api/client'
import { useAuthStore } from '@/stores/auth'

type TabKey = 'basic' | 'settings' | 'security' | 'activity'

interface ProfileState {
  username: string
  email: string
  realName: string
  phone: string
  avatar: string
  bio: string
  language: string
  timezone: string
  theme: string
  emailNotifications: boolean
  smsNotifications: boolean
  pushNotifications: boolean
  twoFactorEnabled: boolean
  lastPasswordChange: string
  lastLoginAt: string
  loginCount: number
  createdAt: string
  updatedAt: string
}

const defaultProfile: ProfileState = {
  username: '',
  email: '',
  realName: '',
  phone: '',
  avatar: '',
  bio: '',
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  theme: 'light',
  emailNotifications: true,
  smsNotifications: false,
  pushNotifications: true,
  twoFactorEnabled: false,
  lastPasswordChange: '',
  lastLoginAt: '',
  loginCount: 0,
  createdAt: '',
  updatedAt: '',
}

const tabs: Array<{ id: TabKey; name: string }> = [
  { id: 'basic', name: '基本信息' },
  { id: 'settings', name: '个人设置' },
  { id: 'security', name: '安全设置' },
  { id: 'activity', name: '活动记录' },
]

const normalizeProfile = (payload: any): ProfileState => {
  const info = payload?.user_info || payload?.data?.user_info || payload?.data || payload || {}
  return {
    username: info.username || '',
    email: info.email || '',
    realName: info.nickname || info.real_name || info.realName || info.username || '',
    phone: info.phone || '',
    avatar: info.avatar || info.avatar_url || '',
    bio: info.bio || '',
    language: info.language || 'zh-CN',
    timezone: info.timezone || 'Asia/Shanghai',
    theme: info.theme || localStorage.getItem('theme') || 'light',
    emailNotifications: info.email_notifications ?? info.emailNotifications ?? true,
    smsNotifications: info.sms_notifications ?? info.smsNotifications ?? false,
    pushNotifications: info.push_notifications ?? info.pushNotifications ?? true,
    twoFactorEnabled: info.mfa_enabled ?? info.two_factor_enabled ?? false,
    lastPasswordChange: info.password_updated_at || info.last_password_change || info.lastPasswordChange || '',
    lastLoginAt: info.last_login_at || info.lastLoginAt || '',
    loginCount: Number(info.login_count || info.loginCount || 0),
    createdAt: info.created_at || info.createdAt || '',
    updatedAt: info.updated_at || info.updatedAt || '',
  }
}

const formatDate = (value?: string) => {
  if (!value) return '-'
  const base = value.includes('T') ? value : value.replace(' ', 'T')
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(base) ? base : `${base}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
}

const resolveAssetUrl = (url?: string) => {
  if (!url) return ''
  if (/^https?:\/\//i.test(url) || url.startsWith('data:')) return url
  if (url.startsWith('/static/')) return `${apiClient.defaults.baseURL}${url}`
  return url
}

const applyTheme = (theme: string) => {
  localStorage.setItem('theme', theme)
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  const useDark = theme === 'dark' || (theme === 'auto' && prefersDark)
  document.documentElement.classList.toggle('dark', useDark)
}

const Profile: React.FC = () => {
  const { user, updateUser } = useAuthStore()
  const [activeTab, setActiveTab] = useState<TabKey>('basic')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)
  const [profile, setProfile] = useState<ProfileState>(defaultProfile)
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })

  useEffect(() => {
    const loadProfile = async () => {
      setIsLoading(true)
      try {
        const response = await apiClient.get('/auth/profile')
        const nextProfile = normalizeProfile(response.data)
        setProfile(nextProfile)
        applyTheme(nextProfile.theme)
      } catch (error) {
        console.error('Failed to load profile:', error)
        toast.error('加载个人资料失败')
      } finally {
        setIsLoading(false)
      }
    }

    loadProfile()
  }, [])

  useEffect(() => {
    applyTheme(profile.theme)
  }, [profile.theme])

  const profilePayload = useMemo(
    () => ({
      email: profile.email,
      nickname: profile.realName,
      phone: profile.phone,
      avatar: profile.avatar,
      bio: profile.bio,
      language: profile.language,
      timezone: profile.timezone,
      theme: profile.theme,
      email_notifications: profile.emailNotifications,
      sms_notifications: profile.smsNotifications,
      push_notifications: profile.pushNotifications,
    }),
    [profile],
  )

  const refreshProfile = async () => {
    const response = await apiClient.get('/auth/profile')
    const nextProfile = normalizeProfile(response.data)
    setProfile(nextProfile)
    applyTheme(nextProfile.theme)
    return nextProfile
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      const response = await apiClient.put('/auth/profile', profilePayload)
      const savedProfile = normalizeProfile(response.data)
      setProfile(savedProfile)
      applyTheme(savedProfile.theme)

      if (user) {
        updateUser({
          ...user,
          username: savedProfile.username || user.username,
          email: savedProfile.email,
          real_name: savedProfile.realName,
          nickname: savedProfile.realName,
          avatar: savedProfile.avatar || user.avatar,
          language: savedProfile.language,
          timezone: savedProfile.timezone,
          theme: savedProfile.theme,
          email_notifications: savedProfile.emailNotifications,
          sms_notifications: savedProfile.smsNotifications,
          push_notifications: savedProfile.pushNotifications,
        })
      }

      toast.success('个人资料已保存')
    } catch (error) {
      console.error('Failed to save profile:', error)
      toast.error('保存个人资料失败')
    } finally {
      setIsSaving(false)
    }
  }

  const handlePasswordChange = async () => {
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      toast.error('新密码和确认密码不一致')
      return
    }
    if (passwordForm.newPassword.length < 8) {
      toast.error('密码长度至少 8 位')
      return
    }

    setIsSaving(true)
    try {
      await apiClient.post('/auth/change-password', {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      })
      await refreshProfile()
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' })
      toast.success('密码修改成功')
    } catch (error) {
      console.error('Failed to change password:', error)
      toast.error('密码修改失败，请检查当前密码')
    } finally {
      setIsSaving(false)
    }
  }

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      toast.error('只能上传图片文件')
      event.target.value = ''
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('头像文件不能超过 5MB')
      event.target.value = ''
      return
    }

    const formData = new FormData()
    formData.append('file', file)
    setIsUploadingAvatar(true)

    try {
      const response = await apiClient.post('/auth/profile/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const savedProfile = normalizeProfile(response.data)
      setProfile(savedProfile)

      if (user) {
        updateUser({
          ...user,
          avatar: savedProfile.avatar || user.avatar,
          email: savedProfile.email || user.email,
          real_name: savedProfile.realName,
          nickname: savedProfile.realName,
        })
      }

      toast.success('头像已上传')
    } catch (error) {
      console.error('Failed to upload avatar:', error)
      toast.error('头像上传失败')
    } finally {
      setIsUploadingAvatar(false)
      event.target.value = ''
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-end gap-3">
        <button onClick={handleSave} disabled={isSaving} className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50">
          {isSaving ? '保存中...' : '保存更改'}
        </button>
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
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">基本信息</h3>
              <div className="flex items-center space-x-6">
                <div className="relative">
                  <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full bg-gray-200">
                    {profile.avatar ? (
                      <img src={resolveAssetUrl(profile.avatar)} alt="头像" className="h-full w-full object-cover" />
                    ) : (
                      <span className="text-2xl text-gray-500 dark:text-gray-400">{profile.username.charAt(0).toUpperCase()}</span>
                    )}
                  </div>
                  <label className="absolute bottom-0 right-0 cursor-pointer rounded-full bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700">
                    {isUploadingAvatar ? '上传中' : '上传'}
                    <input type="file" accept="image/*" onChange={handleAvatarUpload} disabled={isUploadingAvatar} className="hidden" />
                  </label>
                </div>
                <div>
                  <h4 className="text-lg font-medium text-gray-900 dark:text-white">{profile.realName || profile.username}</h4>
                  <p className="text-gray-600 dark:text-gray-400">@{profile.username}</p>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">头像上传后立即保存，其它信息点击“保存更改”后生效。</p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <Field label="用户名">
                  <input value={profile.username} disabled className="w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-gray-500 dark:text-gray-400 dark:bg-gray-800/50 dark:border-gray-600" />
                </Field>
                <Field label="邮箱地址">
                  <input type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} className={inputClass} />
                </Field>
                <Field label="真实姓名">
                  <input value={profile.realName} onChange={(e) => setProfile({ ...profile, realName: e.target.value })} className={inputClass} />
                </Field>
                <Field label="手机号码">
                  <input value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} className={inputClass} />
                </Field>
                <Field label="个人简介">
                  <textarea value={profile.bio} onChange={(e) => setProfile({ ...profile, bio: e.target.value })} rows={3} className={inputClass} />
                </Field>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">个人设置</h3>
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <Field label="语言">
                  <select value={profile.language} onChange={(e) => setProfile({ ...profile, language: e.target.value })} className={inputClass}>
                    <option value="zh-CN">简体中文</option>
                    <option value="zh-TW">繁体中文</option>
                    <option value="en-US">English</option>
                  </select>
                </Field>
                <Field label="时区">
                  <select value={profile.timezone} onChange={(e) => setProfile({ ...profile, timezone: e.target.value })} className={inputClass}>
                    <option value="Asia/Shanghai">北京时间 (UTC+8)</option>
                    <option value="Asia/Tokyo">东京时间 (UTC+9)</option>
                    <option value="America/New_York">纽约时间 (UTC-5)</option>
                    <option value="Europe/London">伦敦时间 (UTC+0)</option>
                  </select>
                </Field>
                <Field label="主题">
                  <select value={profile.theme} onChange={(e) => setProfile({ ...profile, theme: e.target.value })} className={inputClass}>
                    <option value="light">浅色主题</option>
                    <option value="dark">深色主题</option>
                    <option value="auto">跟随系统</option>
                  </select>
                </Field>
              </div>

              <div className="space-y-3">
                <h4 className="text-md font-medium text-gray-900 dark:text-white">通知设置</h4>
                <Checkbox checked={profile.emailNotifications} onChange={(checked) => setProfile({ ...profile, emailNotifications: checked })}>
                  邮件通知
                </Checkbox>
                <Checkbox checked={profile.smsNotifications} onChange={(checked) => setProfile({ ...profile, smsNotifications: checked })}>
                  短信通知
                </Checkbox>
                <Checkbox checked={profile.pushNotifications} onChange={(checked) => setProfile({ ...profile, pushNotifications: checked })}>
                  站内通知
                </Checkbox>
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">安全设置</h3>
              <div className="rounded-lg bg-gray-50 p-6 dark:bg-gray-700">
                <h4 className="mb-4 text-md font-medium text-gray-900 dark:text-white">修改密码</h4>
                <div className="space-y-4">
                  <Field label="当前密码">
                    <input type="password" value={passwordForm.currentPassword} onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })} className={inputClass} />
                  </Field>
                  <Field label="新密码">
                    <input type="password" value={passwordForm.newPassword} onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })} className={inputClass} />
                  </Field>
                  <Field label="确认新密码">
                    <input type="password" value={passwordForm.confirmPassword} onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })} className={inputClass} />
                  </Field>
                  <button onClick={handlePasswordChange} disabled={isSaving || !passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmPassword} className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50">
                    修改密码
                  </button>
                </div>
              </div>

              <div className="rounded-lg bg-gray-50 p-6 dark:bg-gray-700">
                <h4 className="mb-4 text-md font-medium text-gray-900 dark:text-white">安全信息</h4>
                <InfoRow label="多因素认证" value={profile.twoFactorEnabled ? '已启用' : '未启用'} />
                <InfoRow label="上次密码修改" value={formatDate(profile.lastPasswordChange)} />
                <InfoRow label="上次登录时间" value={formatDate(profile.lastLoginAt)} />
              </div>
            </div>
          )}

          {activeTab === 'activity' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">活动记录</h3>
              <div className="rounded-lg bg-gray-50 p-6 dark:bg-gray-700">
                <h4 className="mb-4 text-md font-medium text-gray-900 dark:text-white">账号统计</h4>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <Stat label="总登录次数" value={String(profile.loginCount || '-')} />
                  <Stat label="使用天数" value={profile.createdAt ? String(Math.max(0, Math.floor((Date.now() - new Date(profile.createdAt).getTime()) / 86400000))) : '-'} />
                  <Stat label="最近更新" value={formatDate(profile.updatedAt)} />
                </div>
              </div>
              <div className="space-y-3">
                <InfoRow label="账号创建时间" value={formatDate(profile.createdAt)} />
                <InfoRow label="最后登录时间" value={formatDate(profile.lastLoginAt)} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const inputClass = 'w-full rounded-md border border-gray-300 px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500'

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <label className="block">
    <span className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
    {children}
  </label>
)

const Checkbox = ({ checked, onChange, children }: { checked: boolean; onChange: (checked: boolean) => void; children: React.ReactNode }) => (
  <label className="flex items-center text-sm text-gray-700 dark:text-gray-300">
    <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mr-2" />
    {children}
  </label>
)

const InfoRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex justify-between border-b border-gray-200 py-2 text-sm last:border-b-0 dark:border-gray-600">
    <span className="text-gray-600 dark:text-gray-400">{label}</span>
    <span className="text-gray-900 dark:text-white">{value}</span>
  </div>
)

const Stat = ({ label, value }: { label: string; value: string }) => (
  <div className="text-center">
    <div className="text-2xl font-bold text-blue-600">{value}</div>
    <div className="text-sm text-gray-600 dark:text-gray-400">{label}</div>
  </div>
)

export default Profile
