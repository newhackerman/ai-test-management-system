// @ts-nocheck
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { updateRole } from '@/api/role';
import { Button } from '@/components/ui/Button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Switch } from '@/components/ui/Switch';
import { Textarea } from '@/components/ui/Textarea';
import type { Role } from '@/types';

interface EditRoleDialogProps {
  open: boolean;
  role: Role;
  onClose: () => void;
  onSuccess: () => void;
}

export const EditRoleDialog: React.FC<EditRoleDialogProps> = ({ open, role, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_active: true,
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!role) return;
    setFormData({
      name: role.name || '',
      description: role.description || '',
      is_active: role.is_active ?? role.isActive ?? true,
    });
  }, [role]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!formData.name.trim()) {
      toast.error('请填写角色名称');
      return;
    }

    setIsLoading(true);
    try {
      await updateRole(role.id, {
        name: formData.name.trim(),
        description: formData.description.trim(),
        is_active: formData.is_active,
      });
      toast.success('角色更新成功');
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error?.message || '更新角色失败');
    } finally {
      setIsLoading(false);
    }
  };

  const isSystemRole = role?.is_system_role ?? role?.isSystem ?? false;

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>编辑角色</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="role-name">角色名称 *</Label>
            <Input
              id="role-name"
              value={formData.name}
              onChange={(event) => setFormData((prev) => ({ ...prev, name: event.target.value }))}
              placeholder="请输入角色名称"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-code">角色代码</Label>
            <Input id="role-code" value={role?.code || ''} disabled className="bg-gray-100" />
            <p className="text-sm text-gray-500">角色代码创建后不可修改。</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-description">角色描述</Label>
            <Textarea
              id="role-description"
              value={formData.description}
              onChange={(event) => setFormData((prev) => ({ ...prev, description: event.target.value }))}
              placeholder="请输入角色描述"
              disabled={isLoading}
              rows={3}
            />
          </div>

          {!isSystemRole && (
            <div className="flex items-center justify-between rounded-md border p-3">
              <div>
                <Label htmlFor="role-active">启用角色</Label>
                <p className="text-xs text-gray-500">关闭后该角色不会再用于新的授权判断。</p>
              </div>
              <Switch
                id="role-active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData((prev) => ({ ...prev, is_active: checked }))}
                disabled={isLoading}
              />
            </div>
          )}

          <div className="flex justify-end space-x-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              取消
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? '更新中...' : '保存'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EditRoleDialog;
