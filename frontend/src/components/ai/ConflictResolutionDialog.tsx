/**
 * 冲突解决对话框组件
 * 处理数据同步冲突的用户界面
 */
import React, { useState } from 'react';
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/Dialog';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs';
import { 
  AlertTriangle,
  Clock,
  User,
  Server,
  GitMerge,
  Eye,
  Check,
  X
} from 'lucide-react';
import { ConflictItem, ConflictResolution } from '../../lib/sync-middleware';
import { cn } from '../../lib/utils';

interface ConflictResolutionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  conflict: ConflictItem | null;
  onResolve: (conflictId: string, resolution: ConflictResolution, mergedData?: any) => void;
}

export function ConflictResolutionDialog({
  open,
  onOpenChange,
  conflict,
  onResolve
}: ConflictResolutionDialogProps) {
  const [selectedResolution, setSelectedResolution] = useState<ConflictResolution | null>(null);
  const [mergedData, setMergedData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('overview');

  if (!conflict) return null;

  const handleResolve = () => {
    if (!selectedResolution) return;

    onResolve(conflict.id, selectedResolution, mergedData);
    onOpenChange(false);
    setSelectedResolution(null);
    setMergedData(null);
  };

  const getConflictTypeLabel = (type: string) => {
    switch (type) {
      case 'version': return '版本冲突';
      case 'concurrent_edit': return '并发编辑';
      case 'deleted': return '删除冲突';
      default: return '未知冲突';
    }
  };

  const getConflictTypeColor = (type: string) => {
    switch (type) {
      case 'version': return 'bg-yellow-100 text-yellow-800';
      case 'concurrent_edit': return 'bg-red-100 text-red-800 dark:text-red-300 dark:bg-red-900/30';
      case 'deleted': return 'bg-gray-100 text-gray-800 dark:text-gray-200 dark:bg-gray-800';
      default: return 'bg-blue-100 text-blue-800 dark:text-blue-300 dark:bg-blue-900/30';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  const renderDataComparison = (localData: any, remoteData: any) => {
    const localKeys = Object.keys(localData || {});
    const remoteKeys = Object.keys(remoteData || {});
    const allKeys = Array.from(new Set([...localKeys, ...remoteKeys]));

    return (
      <div className="space-y-3">
        {allKeys.map(key => {
          const localValue = localData?.[key];
          const remoteValue = remoteData?.[key];
          const isDifferent = JSON.stringify(localValue) !== JSON.stringify(remoteValue);

          return (
            <div key={key} className={cn(
              "p-3 rounded-lg border",
              isDifferent ? "border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800" : "border-gray-200 bg-gray-50 dark:bg-gray-800/50 dark:border-gray-700"
            )}>
              <div className="font-medium text-sm text-gray-700 mb-2 dark:text-gray-300">
                {key}
                {isDifferent && (
                  <Badge className="ml-2 bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">
                    <AlertTriangle className="w-3 h-3 mr-1" />
                    冲突
                  </Badge>
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500 mb-1 flex items-center gap-1 dark:text-gray-400">
                    <User className="w-3 h-3" />
                    本地版本
                  </div>
                  <div className="text-sm bg-white p-2 rounded border dark:bg-gray-800">
                    {localValue !== undefined ? JSON.stringify(localValue, null, 2) : '(未设置)'}
                  </div>
                </div>
                
                <div>
                  <div className="text-xs text-gray-500 mb-1 flex items-center gap-1 dark:text-gray-400">
                    <Server className="w-3 h-3" />
                    服务器版本
                  </div>
                  <div className="text-sm bg-white p-2 rounded border dark:bg-gray-800">
                    {remoteValue !== undefined ? JSON.stringify(remoteValue, null, 2) : '(未设置)'}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const resolutionOptions = [
    {
      value: ConflictResolution.SERVER_WINS,
      label: '使用服务器版本',
      description: '丢弃本地更改，使用服务器上的最新版本',
      icon: <Server className="w-4 h-4" />,
      color: 'border-blue-200 hover:bg-blue-50 dark:bg-blue-900/20'
    },
    {
      value: ConflictResolution.CLIENT_WINS,
      label: '使用本地版本',
      description: '保留本地更改，覆盖服务器版本',
      icon: <User className="w-4 h-4" />,
      color: 'border-green-200 hover:bg-green-50'
    },
    {
      value: ConflictResolution.MERGE,
      label: '自动合并',
      description: '尝试自动合并两个版本的更改',
      icon: <GitMerge className="w-4 h-4" />,
      color: 'border-purple-200 hover:bg-purple-50 dark:bg-purple-900/20'
    },
    {
      value: ConflictResolution.MANUAL,
      label: '手动解决',
      description: '手动选择要保留的字段和值',
      icon: <Eye className="w-4 h-4" />,
      color: 'border-orange-200 hover:bg-orange-50 dark:bg-orange-900/20'
    }
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500 dark:text-red-400" />
            数据冲突解决
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">冲突概览</TabsTrigger>
              <TabsTrigger value="comparison">数据对比</TabsTrigger>
              <TabsTrigger value="resolution">解决方案</TabsTrigger>
            </TabsList>

            <div className="mt-4 overflow-y-auto max-h-[50vh]">
              <TabsContent value="overview" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">冲突类型</label>
                      <div className="mt-1">
                        <Badge className={getConflictTypeColor(conflict.conflictType)}>
                          {getConflictTypeLabel(conflict.conflictType)}
                        </Badge>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">实体类型</label>
                      <div className="mt-1 text-sm text-gray-900 dark:text-gray-100">{conflict.entityType}</div>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">实体ID</label>
                      <div className="mt-1 text-sm text-gray-900 dark:text-gray-100">{conflict.entityId}</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">冲突时间</label>
                      <div className="mt-1 text-sm text-gray-900 flex items-center gap-1 dark:text-gray-100">
                        <Clock className="w-4 h-4" />
                        {formatTimestamp(conflict.timestamp)}
                      </div>
                    </div>

                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">冲突ID</label>
                      <div className="mt-1 text-sm text-gray-500 font-mono dark:text-gray-400">{conflict.id}</div>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-yellow-800">冲突说明</h4>
                      <p className="text-sm text-yellow-700 mt-1">
                        检测到数据冲突，需要您选择如何解决。请仔细比较本地和服务器版本的差异，然后选择合适的解决方案。
                      </p>
                    </div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="comparison" className="space-y-4">
                <div className="text-sm text-gray-600 mb-4 dark:text-gray-400">
                  以下是本地版本和服务器版本的详细对比：
                </div>
                {renderDataComparison(conflict.localData, conflict.remoteData)}
              </TabsContent>

              <TabsContent value="resolution" className="space-y-4">
                <div className="text-sm text-gray-600 mb-4 dark:text-gray-400">
                  请选择解决冲突的方式：
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {resolutionOptions.map((option) => (
                    <div
                      key={option.value}
                      className={cn(
                        "p-4 border rounded-lg cursor-pointer transition-colors",
                        option.color,
                        selectedResolution === option.value
                          ? "ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20"
                          : ""
                      )}
                      onClick={() => setSelectedResolution(option.value)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-1">
                          {option.icon}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-gray-900 dark:text-gray-100">{option.label}</h4>
                            {selectedResolution === option.value && (
                              <Check className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mt-1 dark:text-gray-400">{option.description}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {selectedResolution === ConflictResolution.MANUAL && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg dark:bg-gray-800/50">
                    <h4 className="font-medium text-gray-900 mb-2 dark:text-gray-100">手动合并</h4>
                    <p className="text-sm text-gray-600 mb-3 dark:text-gray-400">
                      请手动编辑要保留的数据：
                    </p>
                    <textarea
                      className="w-full h-32 p-3 border rounded-lg font-mono text-sm"
                      value={mergedData ? JSON.stringify(mergedData, null, 2) : JSON.stringify({ ...conflict.localData, ...conflict.remoteData }, null, 2)}
                      onChange={(e) => {
                        try {
                          setMergedData(JSON.parse(e.target.value));
                        } catch {
                          // 忽略JSON解析错误
                        }
                      }}
                      placeholder="请输入合并后的JSON数据..."
                    />
                  </div>
                )}
              </TabsContent>
            </div>
          </Tabs>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            <X className="w-4 h-4 mr-1" />
            取消
          </Button>
          <Button
            onClick={handleResolve}
            disabled={!selectedResolution}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Check className="w-4 h-4 mr-1" />
            解决冲突
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}