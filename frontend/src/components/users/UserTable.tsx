import React from 'react'
import { Edit, Key, Lock, MoreHorizontal, Shield, Trash2, Unlock } from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Checkbox } from '@/components/ui/Checkbox'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu'
import { getRoleDisplayName } from '@/services/user-service'
import type { User } from '@/types'

interface UserTableProps {
  users: User[]
  loading?: boolean
  selectedUsers: User[]
  onSelectUser: (user: User, selected: boolean) => void
  onSelectAll: (selected: boolean) => void
  onEdit: (user: User) => void
  onDelete: (user: User) => void
  onResetPassword: (user: User) => void
  onToggleLock: (user: User) => void
  onViewPermissions: (user: User) => void
}

const statusLabel: Record<User['status'], string> = {
  active: '启用',
  disabled: '禁用',
  locked: '锁定',
  pending: '待审核',
  deleted: '已删除',
}

function formatDate(value?: string) {
  if (!value) return '从未登录'
  const base = value.includes('T') ? value : value.replace(' ', 'T')
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(base) ? base : `${base}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
}

function getStatusBadge(user: User) {
  if (user.status === 'locked') return <Badge variant="destructive">锁定</Badge>
  if (user.status === 'deleted') return <Badge variant="outline">已删除</Badge>
  if (!user.is_active || user.status === 'disabled') return <Badge variant="destructive">禁用</Badge>
  if (user.status === 'pending') return <Badge variant="secondary">{statusLabel[user.status]}</Badge>
  return <Badge variant="default">启用</Badge>
}

function roleName(user: User) {
  if (user.roles?.length) {
    return user.roles.map((role) => getRoleDisplayName(role)).join('、')
  }
  return getRoleDisplayName(user.role)
}

export const UserTable: React.FC<UserTableProps> = ({
  users,
  loading = false,
  selectedUsers,
  onSelectUser,
  onSelectAll,
  onEdit,
  onDelete,
  onResetPassword,
  onToggleLock,
  onViewPermissions,
}) => {
  const currentPageSelectedCount = users.filter((user) => selectedUsers.some((selected) => selected.id === user.id)).length
  const allSelected = users.length > 0 && currentPageSelectedCount === users.length
  const someSelected = currentPageSelectedCount > 0 && currentPageSelectedCount < users.length

  if (loading) {
    return (
      <div className="flex justify-center py-10">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600" />
      </div>
    )
  }

  if (users.length === 0) {
    return <div className="py-10 text-center text-gray-500">暂无用户数据</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="w-12 px-4 py-3 text-left">
              <Checkbox checked={allSelected} indeterminate={someSelected} onCheckedChange={onSelectAll} aria-label="选择全部用户" />
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-900">用户</th>
            <th className="px-4 py-3 text-left font-medium text-gray-900">邮箱</th>
            <th className="px-4 py-3 text-left font-medium text-gray-900">角色</th>
            <th className="px-4 py-3 text-left font-medium text-gray-900">状态</th>
            <th className="px-4 py-3 text-left font-medium text-gray-900">上次登录</th>
            <th className="px-4 py-3 text-left font-medium text-gray-900">创建时间</th>
            <th className="px-4 py-3 text-right font-medium text-gray-900">操作</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => {
            const locked = user.status === 'locked'
            return (
              <tr key={user.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Checkbox
                    checked={selectedUsers.some((selected) => selected.id === user.id)}
                    onCheckedChange={(checked) => onSelectUser(user, checked)}
                    aria-label={`选择用户 ${user.username}`}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user.avatar} alt={user.username} />
                      <AvatarFallback>{user.username.slice(0, 1).toUpperCase()}</AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="font-medium text-gray-900">{user.username}</div>
                      {user.nickname && user.nickname !== user.username && <div className="text-sm text-gray-500">{user.nickname}</div>}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600">{user.email}</td>
                <td className="px-4 py-3">
                  <Badge variant="outline">{roleName(user)}</Badge>
                </td>
                <td className="px-4 py-3">{getStatusBadge(user)}</td>
                <td className="px-4 py-3 text-gray-600">{formatDate(user.last_login_at)}</td>
                <td className="px-4 py-3 text-gray-600">{formatDate(user.created_at)}</td>
                <td className="px-4 py-3 text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" aria-label="用户操作">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>操作</DropdownMenuLabel>
                      <DropdownMenuItem onClick={() => onViewPermissions(user)}>
                        <Shield className="mr-2 h-4 w-4" />
                        查看权限
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onEdit(user)}>
                        <Edit className="mr-2 h-4 w-4" />
                        编辑
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onResetPassword(user)}>
                        <Key className="mr-2 h-4 w-4" />
                        重置密码
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => onToggleLock(user)}>
                        {locked ? <Unlock className="mr-2 h-4 w-4" /> : <Lock className="mr-2 h-4 w-4" />}
                        {locked ? '解锁' : '锁定'}
                      </DropdownMenuItem>
                      <DropdownMenuItem className="text-red-600" onClick={() => onDelete(user)}>
                        <Trash2 className="mr-2 h-4 w-4" />
                        删除
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default UserTable
