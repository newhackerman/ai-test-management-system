import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { updatePermission } from '@/api/permission';
import { toast } from 'react-hot-toast';
import type { Permission } from '@/types';

interface EditPermissionDialogProps {
  open: boolean;
  permission: Permission;
  onClose: () => void;
  onSuccess: () => void;
}

export const EditPermissionDialog: React.FC<EditPermissionDialogProps> = ({
  open,
  permission,
  onClose,
  onSuccess
}) => {
  const [formData, setFormData] = useState({
    name: '',
    description: ''
  });
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (permission) {
      setFormData({
        name: permission.name,
        description: permission.description || ''
      });
    }
  }, [permission]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      toast.error('请填写权限名称');
      return;
    }

    setIsLoading(true);
    try {
      await updatePermission(permission.id, formData);
      toast.success('权限更新成功');
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || '更新权限失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>编辑权限</DialogTitle>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">权限名称 *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="请输入权限名称"
              disabled={isLoading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="code">权限代码</Label>
            <Input
              id="code"
              value={permission.code}
              disabled
              className="bg-gray-100 dark:bg-gray-800"
            />
            <p className="text-sm text-gray-500 dark:text-gray-400">权限代码不可修改</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="module">所属模块</Label>
            <Input
              id="module"
              value={permission.module}
              disabled
              className="bg-gray-100 dark:bg-gray-800"
            />
            <p className="text-sm text-gray-500 dark:text-gray-400">所属模块不可修改</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="action">操作类型</Label>
            <Input
              id="action"
              value={permission.action}
              disabled
              className="bg-gray-100 dark:bg-gray-800"
            />
            <p className="text-sm text-gray-500 dark:text-gray-400">操作类型不可修改</p>
          </div>

          {permission.resource && (
            <div className="space-y-2">
              <Label htmlFor="resource">资源标识</Label>
              <Input
                id="resource"
                value={permission.resource}
                disabled
                className="bg-gray-100 dark:bg-gray-800"
              />
              <p className="text-sm text-gray-500 dark:text-gray-400">资源标识不可修改</p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="description">权限描述</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="请输入权限描述"
              disabled={isLoading}
              rows={3}
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
            >
              {isLoading ? '更新中...' : '更新'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};