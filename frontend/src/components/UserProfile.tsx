import React, { useEffect, useState } from 'react';
import { Bell, Clock, Palette, Shield, User } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Switch } from '@/components/ui/Switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Textarea } from '@/components/ui/Textarea';
import { useToast } from '@/hooks/useToast';

interface UserProfileData {
  id: number | string;
  username: string;
  email: string;
  nickname?: string;
  phone?: string;
  avatar?: string;
  bio?: string;
  location?: string;
  website?: string;
  language?: string;
  timezone?: string;
  theme?: string;
  email_notifications?: boolean;
  sms_notifications?: boolean;
  push_notifications?: boolean;
  is_email_verified?: boolean;
  mfa_enabled?: boolean;
  last_login_at?: string;
  password_changed_at?: string;
  created_at?: string;
  updated_at?: string;
}

const defaultProfile: UserProfileData = {
  id: 0,
  username: 'user',
  email: 'user@example.com',
  nickname: '用户',
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  theme: 'light',
  email_notifications: true,
  sms_notifications: false,
  push_notifications: true,
  is_email_verified: true,
  mfa_enabled: false
};

const readStoredProfile = (): UserProfileData => {
  const candidates = [
    localStorage.getItem('auth-user'),
    localStorage.getItem('user'),
    localStorage.getItem('auth-storage')
  ].filter(Boolean);

  for (const value of candidates) {
    try {
      const parsed = JSON.parse(value as string);
      const user = parsed?.state?.user || parsed?.state?.userInfo || parsed?.user || parsed;
      if (user?.username || user?.email) {
        return {
          ...defaultProfile,
          id: user.id || user.user_id || defaultProfile.id,
          username: user.username || defaultProfile.username,
          email: user.email || defaultProfile.email,
          nickname: user.nickname || user.realName || user.real_name || user.username,
          avatar: user.avatar,
          last_login_at: user.lastLoginAt || user.last_login_at,
          password_changed_at: user.passwordChangedAt || user.password_changed_at,
          created_at: user.createdAt || user.created_at,
          updated_at: user.updatedAt || user.updated_at,
          mfa_enabled: user.twoFactorEnabled || user.is_mfa_enabled || false
        };
      }
    } catch {
      // Ignore malformed storage entries.
    }
  }

  return defaultProfile;
};

const saveStoredProfile = (profile: UserProfileData) => {
  localStorage.setItem('auth-user', JSON.stringify(profile));
};

const UserProfile: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<UserProfileData>(defaultProfile);
  const [form, setForm] = useState({
    nickname: '',
    phone: '',
    bio: '',
    location: '',
    website: '',
    language: 'zh-CN',
    timezone: 'Asia/Shanghai',
    theme: 'light',
    email_notifications: true,
    sms_notifications: false,
    push_notifications: true
  });

  useEffect(() => {
    const next = readStoredProfile();
    setProfile(next);
    setForm({
      nickname: next.nickname || '',
      phone: next.phone || '',
      bio: next.bio || '',
      location: next.location || '',
      website: next.website || '',
      language: next.language || 'zh-CN',
      timezone: next.timezone || 'Asia/Shanghai',
      theme: next.theme || 'light',
      email_notifications: next.email_notifications ?? true,
      sms_notifications: next.sms_notifications ?? false,
      push_notifications: next.push_notifications ?? true
    });
    setLoading(false);
  }, []);

  const setField = <K extends keyof typeof form>(field: K, value: (typeof form)[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const saveProfile = async () => {
    setSaving(true);
    try {
      const updated: UserProfileData = {
        ...profile,
        ...form,
        updated_at: new Date().toISOString()
      };
      setProfile(updated);
      saveStoredProfile(updated);
      toast({ title: '保存成功', description: '个人设置已更新' });
    } catch {
      toast({ title: '保存失败', description: '个人设置更新失败', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-muted-foreground">加载个人资料中...</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex items-center gap-4 pt-6">
          <Avatar className="h-16 w-16">
            <AvatarImage src={profile.avatar} />
            <AvatarFallback>{(profile.nickname || profile.username || 'U').slice(0, 1).toUpperCase()}</AvatarFallback>
          </Avatar>
          <div>
            <div className="text-xl font-semibold">{profile.nickname || profile.username}</div>
            <div className="text-sm text-muted-foreground">{profile.email}</div>
            <div className="mt-2 flex gap-2">
              <Badge variant={profile.is_email_verified ? 'default' : 'secondary'}>
                {profile.is_email_verified ? '邮箱已验证' : '邮箱未验证'}
              </Badge>
              <Badge variant={profile.mfa_enabled ? 'default' : 'outline'}>{profile.mfa_enabled ? 'MFA 已启用' : 'MFA 未启用'}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="basic">
        <TabsList>
          <TabsTrigger value="basic">基本资料</TabsTrigger>
          <TabsTrigger value="preferences">偏好设置</TabsTrigger>
          <TabsTrigger value="security">安全信息</TabsTrigger>
        </TabsList>

        <TabsContent value="basic">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <User className="h-5 w-5" />
                基本资料
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Field label="昵称">
                <Input value={form.nickname} onChange={(event) => setField('nickname', event.target.value)} />
              </Field>
              <Field label="手机">
                <Input value={form.phone} onChange={(event) => setField('phone', event.target.value)} />
              </Field>
              <Field label="所在地">
                <Input value={form.location} onChange={(event) => setField('location', event.target.value)} />
              </Field>
              <Field label="个人网站">
                <Input value={form.website} onChange={(event) => setField('website', event.target.value)} />
              </Field>
              <div className="space-y-2 md:col-span-2">
                <Label>个人简介</Label>
                <Textarea value={form.bio} onChange={(event) => setField('bio', event.target.value)} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preferences">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Palette className="h-5 w-5" />
                偏好设置
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Field label="语言">
                <select className="h-10 rounded-md border px-3 text-sm" value={form.language} onChange={(event) => setField('language', event.target.value)}>
                  <option value="zh-CN">简体中文</option>
                  <option value="en-US">English</option>
                </select>
              </Field>
              <Field label="时区">
                <select className="h-10 rounded-md border px-3 text-sm" value={form.timezone} onChange={(event) => setField('timezone', event.target.value)}>
                  <option value="Asia/Shanghai">Asia/Shanghai</option>
                  <option value="UTC">UTC</option>
                </select>
              </Field>
              <Switch checked={form.email_notifications} onCheckedChange={(checked) => setField('email_notifications', checked)} label="邮件通知" />
              <Switch checked={form.sms_notifications} onCheckedChange={(checked) => setField('sms_notifications', checked)} label="短信通知" />
              <Switch checked={form.push_notifications} onCheckedChange={(checked) => setField('push_notifications', checked)} label="站内通知" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Shield className="h-5 w-5" />
                安全信息
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Info icon={<Clock className="h-4 w-4" />} label="上次登录" value={formatTime(profile.last_login_at, form.timezone)} />
              <Info icon={<Shield className="h-4 w-4" />} label="上次修改密码" value={formatTime(profile.password_changed_at, form.timezone)} />
              <Info icon={<Bell className="h-4 w-4" />} label="通知状态" value={form.push_notifications ? '已开启' : '已关闭'} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end">
        <Button type="button" onClick={saveProfile} disabled={saving}>
          {saving ? '保存中...' : '保存修改'}
        </Button>
      </div>
    </div>
  );
};

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="space-y-2">
    <Label>{label}</Label>
    {children}
  </div>
);

const Info: React.FC<{ icon: React.ReactNode; label: string; value: React.ReactNode }> = ({ icon, label, value }) => (
  <div className="rounded-md border p-3">
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      {icon}
      {label}
    </div>
    <div className="mt-1 font-medium">{value || '-'}</div>
  </div>
);

const formatTime = (value?: string, timezone = 'Asia/Shanghai') => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false, timeZone: timezone });
};

export default UserProfile;
