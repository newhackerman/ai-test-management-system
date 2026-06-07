import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { useRoles } from '@/hooks/useUsers'
import type { User } from '@/types'

interface BatchOperationDialogProps {
  open: boolean
  selectedUsers: User[]
  onClose: () => void
  onConfirm: (action: string, data?: { role_id?: number; reason?: string }) => Promise<void>
  loading?: boolean
}

const operationDescriptions: Record<string, string> = {
  activate: '将选中的用户恢复为启用状态。',
  deactivate: '禁用选中的用户，用户将无法登录。',
  delete: '软删除选中的用户。',
  assign_role: '给选中的用户分配指定角色。',
  remove_role: '从选中的用户移除指定角色。',
}

export const BatchOperationDialog: React.FC<BatchOperationDialogProps> = ({
  open,
  selectedUsers,
  onClose,
  onConfirm,
  loading = false,
}) => {
  const [operation, setOperation] = useState('')
  const [roleId, setRoleId] = useState('')
  const { data: roles = [] } = useRoles()

  useEffect(() => {
    if (open) {
      setOperation('')
      setRoleId('')
    }
  }, [open])

  const requiresRole = operation === 'assign_role' || operation === 'remove_role'

  const handleConfirm = async () => {
    if (!operation) return
    if (requiresRole && !roleId) return
    await onConfirm(operation, requiresRole ? { role_id: Number(roleId) } : undefined)
  }

  if (!open) return null

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>批量操作用户</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-md bg-gray-50 p-3">
            <p className="mb-2 text-sm text-gray-600">已选择 {selectedUsers.length} 个用户</p>
            <div className="max-h-28 space-y-1 overflow-y-auto text-sm text-gray-800">
              {selectedUsers.map((user) => (
                <div key={user.id}>
                  {user.username} ({user.email})
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>操作类型</Label>
            <Select value={operation} onValueChange={setOperation}>
              <SelectTrigger>
                <SelectValue placeholder="选择操作类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="activate">启用用户</SelectItem>
                <SelectItem value="deactivate">禁用用户</SelectItem>
                <SelectItem value="delete">删除用户</SelectItem>
                <SelectItem value="assign_role">分配角色</SelectItem>
                <SelectItem value="remove_role">移除角色</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {requiresRole && (
            <div className="space-y-2">
              <Label>角色</Label>
              <Select value={roleId} onValueChange={setRoleId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择角色" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.id} value={String(role.id)}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {operation && <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">{operationDescriptions[operation]}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose} disabled={loading}>
              取消
            </Button>
            <Button onClick={handleConfirm} disabled={loading || !operation || (requiresRole && !roleId)} variant={operation === 'delete' ? 'destructive' : 'default'}>
              {loading ? '处理中...' : '确认操作'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default BatchOperationDialog
