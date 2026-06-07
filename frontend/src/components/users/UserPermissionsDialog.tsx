import React from 'react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import { useUserPermissions } from '@/hooks/useUsers'
import { getRoleDisplayName } from '@/services/user-service'
import type { User } from '@/types'

interface UserPermissionsDialogProps {
  open: boolean
  user: User | null
  onClose: () => void
}

export const UserPermissionsDialog: React.FC<UserPermissionsDialogProps> = ({ open, user, onClose }) => {
  const { data, isLoading } = useUserPermissions(open && user ? String(user.id) : undefined)
  const displayRoles = data?.roles?.length ? data.roles : user?.roles || []

  if (!open || !user) return null

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>用户权限 - {user.username}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 rounded-md bg-gray-50 p-3 text-sm">
            <div>
              <span className="text-gray-500">用户名：</span>
              {user.username}
            </div>
            <div>
              <span className="text-gray-500">邮箱：</span>
              {user.email}
            </div>
            <div>
              <span className="text-gray-500">状态：</span>
              <Badge variant={user.is_active ? 'default' : 'destructive'}>{user.is_active ? '启用' : '禁用'}</Badge>
            </div>
            <div>
              <span className="text-gray-500">角色数：</span>
              {displayRoles.length}
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium">角色</h4>
            <div className="flex flex-wrap gap-2">
              {displayRoles.length > 0 ? (
                displayRoles.map((role) => (
                  <Badge key={role.id} variant="outline">
                    {getRoleDisplayName(role)}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-gray-500">未分配角色</span>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="font-medium">权限</h4>
            <div className="max-h-64 overflow-y-auto rounded-md border p-3">
              {isLoading ? (
                <p className="text-sm text-gray-500">加载中...</p>
              ) : data?.all_permissions?.length ? (
                <div className="grid grid-cols-1 gap-2">
                  {data.all_permissions.map((permission) => (
                    <div key={permission} className="rounded-md bg-gray-50 px-3 py-2 text-sm">
                      {permission}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">当前角色暂未分配权限</p>
              )}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button onClick={onClose}>关闭</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default UserPermissionsDialog
