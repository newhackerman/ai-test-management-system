import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Checkbox } from '@/components/ui/Checkbox'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { useRoles } from '@/hooks/useUsers'
import type { CreateUserData } from '@/services/user-service'

interface CreateUserDialogProps {
  open: boolean
  onClose: () => void
  onCreate: (data: CreateUserData) => Promise<unknown>
}

interface FormState {
  username: string
  email: string
  nickname: string
  phone: string
  password: string
  confirmPassword: string
  is_active: boolean
  role_ids: number[]
}

const emptyForm: FormState = {
  username: '',
  email: '',
  nickname: '',
  phone: '',
  password: '',
  confirmPassword: '',
  is_active: true,
  role_ids: [],
}

function validatePassword(password: string) {
  if (password.length < 8) return '密码至少 8 位'
  if (!/[A-Z]/.test(password)) return '密码必须包含大写字母'
  if (!/[a-z]/.test(password)) return '密码必须包含小写字母'
  if (!/\d/.test(password)) return '密码必须包含数字'
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) return '密码必须包含特殊字符'
  return ''
}

export const CreateUserDialog: React.FC<CreateUserDialogProps> = ({ open, onClose, onCreate }) => {
  const [formData, setFormData] = useState<FormState>(emptyForm)
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [loading, setLoading] = useState(false)
  const { data: roles = [], isLoading: loadingRoles } = useRoles()

  useEffect(() => {
    if (open) {
      setFormData(emptyForm)
      setErrors({})
    }
  }, [open])

  const updateField = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setErrors((prev) => ({ ...prev, [field]: undefined }))
  }

  const toggleRole = (roleId: number, checked: boolean) => {
    updateField(
      'role_ids',
      checked ? Array.from(new Set([...formData.role_ids, roleId])) : formData.role_ids.filter((id) => id !== roleId),
    )
  }

  const validate = () => {
    const nextErrors: Partial<Record<keyof FormState, string>> = {}
    if (!formData.username.trim()) nextErrors.username = '请输入用户名'
    if (formData.username.trim().length > 0 && formData.username.trim().length < 3) nextErrors.username = '用户名至少 3 位'
    if (!formData.email.trim()) nextErrors.email = '请输入邮箱'
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) nextErrors.email = '邮箱格式不正确'
    if (formData.phone && !/^1[3-9]\d{9}$/.test(formData.phone)) nextErrors.phone = '手机号格式不正确'
    const passwordError = validatePassword(formData.password)
    if (passwordError) nextErrors.password = passwordError
    if (formData.password !== formData.confirmPassword) nextErrors.confirmPassword = '两次输入的密码不一致'
    if (formData.role_ids.length === 0) nextErrors.role_ids = '请至少选择一个角色'

    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!validate()) return

    setLoading(true)
    try {
      await onCreate({
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
        nickname: formData.nickname.trim() || null,
        phone: formData.phone.trim() || null,
        is_active: formData.is_active,
        role_ids: formData.role_ids,
      })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>新增用户</DialogTitle>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="username">用户名 *</Label>
              <Input id="username" value={formData.username} onChange={(event) => updateField('username', event.target.value)} />
              {errors.username && <p className="text-sm text-red-600 dark:text-red-400">{errors.username}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">邮箱 *</Label>
              <Input id="email" type="email" value={formData.email} onChange={(event) => updateField('email', event.target.value)} />
              {errors.email && <p className="text-sm text-red-600 dark:text-red-400">{errors.email}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="nickname">昵称</Label>
              <Input id="nickname" value={formData.nickname} onChange={(event) => updateField('nickname', event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">手机号</Label>
              <Input id="phone" value={formData.phone} onChange={(event) => updateField('phone', event.target.value)} />
              {errors.phone && <p className="text-sm text-red-600 dark:text-red-400">{errors.phone}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码 *</Label>
              <Input id="password" type="password" value={formData.password} onChange={(event) => updateField('password', event.target.value)} />
              {errors.password && <p className="text-sm text-red-600 dark:text-red-400">{errors.password}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">确认密码 *</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={(event) => updateField('confirmPassword', event.target.value)}
              />
              {errors.confirmPassword && <p className="text-sm text-red-600 dark:text-red-400">{errors.confirmPassword}</p>}
            </div>
          </div>

          <div className="space-y-2">
            <Label>角色 *</Label>
            <div className="max-h-44 space-y-2 overflow-y-auto rounded-md border p-3">
              {loadingRoles ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">正在加载角色...</p>
              ) : roles.length > 0 ? (
                roles.map((role) => (
                  <label key={role.id} className="flex items-center gap-3 rounded-md px-2 py-1 hover:bg-gray-50 dark:bg-gray-800/50 dark:hover:bg-gray-800">
                    <Checkbox checked={formData.role_ids.includes(role.id)} onCheckedChange={(checked) => toggleRole(role.id, checked)} />
                    <span className="text-sm">{role.name}</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">{role.code}</span>
                  </label>
                ))
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">暂无可选角色</p>
              )}
            </div>
            {errors.role_ids && <p className="text-sm text-red-600 dark:text-red-400">{errors.role_ids}</p>}
          </div>

          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={formData.is_active} onCheckedChange={(checked) => updateField('is_active', checked)} />
            创建后立即启用
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? '创建中...' : '创建'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default CreateUserDialog
