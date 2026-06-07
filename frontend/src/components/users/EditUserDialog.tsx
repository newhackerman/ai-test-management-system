import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Checkbox } from '@/components/ui/Checkbox'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useRoles } from '@/hooks/useUsers'
import type { UpdateUserData } from '@/services/user-service'
import type { User } from '@/types'

interface EditUserDialogProps {
  open: boolean
  user: User | null
  onClose: () => void
  onUpdate: (userId: string, data: UpdateUserData) => Promise<unknown>
}

interface FormState {
  username: string
  email: string
  nickname: string
  phone: string
  status: string
  role_ids: number[]
}

export const EditUserDialog: React.FC<EditUserDialogProps> = ({ open, user, onClose, onUpdate }) => {
  const [formData, setFormData] = useState<FormState>({
    username: '',
    email: '',
    nickname: '',
    phone: '',
    status: 'active',
    role_ids: [],
  })
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [loading, setLoading] = useState(false)
  const { data: roles = [], isLoading: loadingRoles } = useRoles()

  useEffect(() => {
    if (open && user) {
      setFormData({
        username: user.username || '',
        email: user.email || '',
        nickname: user.nickname || '',
        phone: user.phone || '',
        status: user.status || 'active',
        role_ids: user.roles?.map((role) => role.id) || [],
      })
      setErrors({})
    }
  }, [open, user])

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
    if (formData.role_ids.length === 0) nextErrors.role_ids = '请至少选择一个角色'
    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!user || !validate()) return

    setLoading(true)
    try {
      await onUpdate(String(user.id), {
        username: formData.username.trim(),
        email: formData.email.trim(),
        nickname: formData.nickname.trim() || null,
        phone: formData.phone.trim() || null,
        is_active: formData.status === 'active',
        role_ids: formData.role_ids,
      })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  if (!open || !user) return null

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>编辑用户 - {user.username}</DialogTitle>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="edit-username">用户名</Label>
              <Input id="edit-username" value={formData.username} onChange={(event) => updateField('username', event.target.value)} />
              {errors.username && <p className="text-sm text-red-600">{errors.username}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-email">邮箱</Label>
              <Input id="edit-email" type="email" value={formData.email} onChange={(event) => updateField('email', event.target.value)} />
              {errors.email && <p className="text-sm text-red-600">{errors.email}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-nickname">昵称</Label>
              <Input id="edit-nickname" value={formData.nickname} onChange={(event) => updateField('nickname', event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-phone">手机号</Label>
              <Input id="edit-phone" value={formData.phone} onChange={(event) => updateField('phone', event.target.value)} />
              {errors.phone && <p className="text-sm text-red-600">{errors.phone}</p>}
            </div>
          </div>

          <div className="space-y-2">
            <Label>状态</Label>
            <Select value={formData.status} onValueChange={(value) => updateField('status', value)}>
              <SelectTrigger>
                <SelectValue placeholder="选择状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">启用</SelectItem>
                <SelectItem value="disabled">禁用</SelectItem>
                <SelectItem value="pending">待审核</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>角色 *</Label>
            <div className="max-h-44 space-y-2 overflow-y-auto rounded-md border p-3">
              {loadingRoles ? (
                <p className="text-sm text-gray-500">正在加载角色...</p>
              ) : roles.length > 0 ? (
                roles.map((role) => (
                  <label key={role.id} className="flex items-center gap-3 rounded-md px-2 py-1 hover:bg-gray-50">
                    <Checkbox checked={formData.role_ids.includes(role.id)} onCheckedChange={(checked) => toggleRole(role.id, checked)} />
                    <span className="text-sm">{role.name}</span>
                    <span className="text-xs text-gray-500">{role.code}</span>
                  </label>
                ))
              ) : (
                <p className="text-sm text-gray-500">暂无可选角色</p>
              )}
            </div>
            {errors.role_ids && <p className="text-sm text-red-600">{errors.role_ids}</p>}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              取消
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? '保存中...' : '保存'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default EditUserDialog
