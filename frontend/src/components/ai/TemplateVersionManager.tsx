/**
 * 模板版本管理组件
 * 提供版本历史查看、版本比较、版本回滚等功能
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { 
  History, 
  GitBranch, 
  Eye, 
  RotateCcw, 
  Trash2, 
  Star, 
  Calendar,
  User,
  MessageSquare,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Plus,
  Edit,
  GitCompare,
  Download,
  Upload
} from 'lucide-react';
import { useToast } from '@/hooks/useToast';
import { 
  PromptTemplate, 
  PromptTemplateUpdate,
  promptTemplateService 
} from '@/services/prompt-template-service';

interface TemplateVersionManagerProps {
  template: PromptTemplate;
  onVersionChange?: (version: PromptTemplate) => void;
  onClose?: () => void;
}

interface VersionHistory {
  version: string;
  created_at: string;
  is_latest: boolean;
  usage_count: number;
  rating_avg: number;
  changes_summary: string[];
  template_id: number;
}

interface VersionComparison {
  version1: string;
  version2: string;
  changes: Record<string, {
    old_value?: any;
    new_value?: any;
    value?: any;
    changed: boolean;
  }>;
  metadata: {
    version1_created: string;
    version2_created: string;
    version1_usage: number;
    version2_usage: number;
  };
}

export function TemplateVersionManager({ 
  template, 
  onVersionChange, 
  onClose 
}: TemplateVersionManagerProps) {
  const { toast } = useToast();

  // 状态管理
  const [versions, setVersions] = useState<PromptTemplate[]>([]);
  const [versionHistory, setVersionHistory] = useState<VersionHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('history');
  
  // 版本比较
  const [compareVersion1, setCompareVersion1] = useState('');
  const [compareVersion2, setCompareVersion2] = useState('');
  const [comparison, setComparison] = useState<VersionComparison | null>(null);
  const [comparing, setComparing] = useState(false);
  
  // 版本创建
  const [showCreateVersion, setShowCreateVersion] = useState(false);
  const [newVersionData, setNewVersionData] = useState<Partial<PromptTemplateUpdate>>({});
  const [creating, setCreating] = useState(false);

  // 加载版本数据
  const loadVersions = async () => {
    setLoading(true);
    try {
      const [versionsData, historyData] = await Promise.all([
        promptTemplateService.getTemplateVersions(template.id),
        promptTemplateService.getTemplateVersionHistory(template.id)
      ]);
      
      setVersions(versionsData);
      setVersionHistory(historyData.history);
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '加载版本信息失败',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  // 初始化
  useEffect(() => {
    loadVersions();
  }, [template.id]);

  // 创建新版本
  const handleCreateVersion = async () => {
    if (!newVersionData.title && !newVersionData.content) {
      toast({
        title: '请填写修改内容',
        description: '至少需要修改标题或内容',
        variant: 'destructive'
      });
      return;
    }

    setCreating(true);
    try {
      const newVersion = await promptTemplateService.createTemplateVersion(
        template.id, 
        newVersionData
      );
      
      toast({
        title: '版本创建成功',
        description: `新版本 ${newVersion.version} 已创建`,
        variant: 'success'
      });
      
      setShowCreateVersion(false);
      setNewVersionData({});
      loadVersions();
      onVersionChange?.(newVersion);
    } catch (error: any) {
      toast({
        title: '创建失败',
        description: error.message || '创建新版本失败',
        variant: 'destructive'
      });
    } finally {
      setCreating(false);
    }
  };

  // 回滚到指定版本
  const handleRollback = async (version: string) => {
    if (!confirm(`确定要回滚到版本 ${version} 吗？这将使该版本成为最新版本。`)) {
      return;
    }

    try {
      const rolledBackTemplate = await promptTemplateService.rollbackToVersion(
        template.id, 
        version
      );
      
      toast({
        title: '回滚成功',
        description: `已回滚到版本 ${version}`,
        variant: 'success'
      });
      
      loadVersions();
      onVersionChange?.(rolledBackTemplate);
    } catch (error: any) {
      toast({
        title: '回滚失败',
        description: error.message || '版本回滚失败',
        variant: 'destructive'
      });
    }
  };

  // 删除版本
  const handleDeleteVersion = async (version: string) => {
    if (!confirm(`确定要删除版本 ${version} 吗？此操作不可撤销。`)) {
      return;
    }

    try {
      await promptTemplateService.deleteTemplateVersion(template.id, version);
      
      toast({
        title: '删除成功',
        description: `版本 ${version} 已删除`,
        variant: 'success'
      });
      
      loadVersions();
    } catch (error: any) {
      toast({
        title: '删除失败',
        description: error.message || '删除版本失败',
        variant: 'destructive'
      });
    }
  };

  // 设置为最新版本
  const handleSetAsLatest = async (version: string) => {
    try {
      const updatedTemplate = await promptTemplateService.setTemplateAsLatest(
        template.id, 
        version
      );
      
      toast({
        title: '设置成功',
        description: `版本 ${version} 已设为最新版本`,
        variant: 'success'
      });
      
      loadVersions();
      onVersionChange?.(updatedTemplate);
    } catch (error: any) {
      toast({
        title: '设置失败',
        description: error.message || '设置最新版本失败',
        variant: 'destructive'
      });
    }
  };

  // 比较版本
  const handleCompareVersions = async () => {
    if (!compareVersion1 || !compareVersion2) {
      toast({
        title: '请选择版本',
        description: '需要选择两个版本进行比较',
        variant: 'destructive'
      });
      return;
    }

    if (compareVersion1 === compareVersion2) {
      toast({
        title: '版本相同',
        description: '请选择不同的版本进行比较',
        variant: 'destructive'
      });
      return;
    }

    setComparing(true);
    try {
      const comparisonData = await promptTemplateService.compareTemplateVersions(
        template.id,
        compareVersion1,
        compareVersion2
      );
      
      setComparison(comparisonData as VersionComparison);
    } catch (error: any) {
      toast({
        title: '比较失败',
        description: error.message || '版本比较失败',
        variant: 'destructive'
      });
    } finally {
      setComparing(false);
    }
  };

  // 查看版本详情
  const handleViewVersion = async (version: string) => {
    try {
      const versionTemplate = await promptTemplateService.getTemplateVersionByNumber(
        template.id,
        version
      );
      
      if (versionTemplate) {
        onVersionChange?.(versionTemplate);
      }
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '加载版本详情失败',
        variant: 'destructive'
      });
    }
  };

  // 渲染变更摘要
  const renderChangesSummary = (changes: string[]) => {
    if (changes.length === 0) {
      return <span className="text-gray-500 dark:text-gray-400">初始版本</span>;
    }
    
    return (
      <div className="flex flex-wrap gap-1">
        {changes.map((change, index) => (
          <Badge key={index} variant="outline" className="text-xs">
            {change}
          </Badge>
        ))}
      </div>
    );
  };

  // 渲染比较结果
  const renderComparisonResult = () => {
    if (!comparison) return null;

    const changedFields = Object.entries(comparison.changes).filter(([_, change]) => change.changed);
    
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">版本比较结果</h3>
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <span>版本 {comparison.version1}</span>
            <ArrowRight className="w-4 h-4" />
            <span>版本 {comparison.version2}</span>
          </div>
        </div>

        {changedFields.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center">
              <CheckCircle className="w-8 h-8 text-green-600 mx-auto mb-2 dark:text-green-400" />
              <p className="text-gray-600 dark:text-gray-400">两个版本没有差异</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {changedFields.map(([field, change]) => (
              <Card key={field}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base capitalize">
                    {field.replace(/_/g, ' ')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-medium text-red-700 mb-2 dark:text-red-400">
                        版本 {comparison.version1} (旧)
                      </h4>
                      <div className="p-3 bg-red-50 border border-red-200 rounded text-sm dark:bg-red-900/20 dark:border-red-800">
                        {typeof change.old_value === 'object' 
                          ? JSON.stringify(change.old_value, null, 2)
                          : String(change.old_value || '(空)')
                        }
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-green-700 mb-2">
                        版本 {comparison.version2} (新)
                      </h4>
                      <div className="p-3 bg-green-50 border border-green-200 rounded text-sm">
                        {typeof change.new_value === 'object'
                          ? JSON.stringify(change.new_value, null, 2)
                          : String(change.new_value || '(空)')
                        }
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">版本元数据</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="font-medium mb-2">版本 {comparison.version1}</h4>
                <p>创建时间: {new Date(comparison.metadata.version1_created).toLocaleString()}</p>
                <p>使用次数: {comparison.metadata.version1_usage}</p>
              </div>
              <div>
                <h4 className="font-medium mb-2">版本 {comparison.version2}</h4>
                <p>创建时间: {new Date(comparison.metadata.version2_created).toLocaleString()}</p>
                <p>使用次数: {comparison.metadata.version2_usage}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <GitBranch className="w-6 h-6" />
            版本管理
          </h1>
          <p className="text-gray-600 mt-1 dark:text-gray-400">
            管理模板 "{template.title}" 的版本历史
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => setShowCreateVersion(true)}
          >
            <Plus className="w-4 h-4 mr-2" />
            创建新版本
          </Button>
          <Button variant="outline" onClick={onClose}>
            关闭
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="history">版本历史</TabsTrigger>
          <TabsTrigger value="compare">版本比较</TabsTrigger>
          <TabsTrigger value="create">创建版本</TabsTrigger>
        </TabsList>

        {/* 版本历史 */}
        <TabsContent value="history" className="space-y-4">
          {loading ? (
            <Card>
              <CardContent className="p-8 text-center">
                <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p>加载版本历史...</p>
              </CardContent>
            </Card>
          ) : versionHistory.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <History className="w-12 h-12 text-gray-400 mx-auto mb-4 dark:text-gray-500" />
                <h3 className="text-lg font-medium text-gray-600 mb-2 dark:text-gray-400">暂无版本历史</h3>
                <p className="text-gray-500 dark:text-gray-400">这是模板的第一个版本</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {versionHistory.map((history, index) => (
                <Card key={history.version} className={history.is_latest ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-lg">
                            版本 {history.version}
                          </h3>
                          {history.is_latest && (
                            <Badge variant="default" className="bg-blue-600">
                              <Star className="w-3 h-3 mr-1" />
                              最新版本
                            </Badge>
                          )}
                          <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              {new Date(history.created_at).toLocaleString()}
                            </div>
                            <div className="flex items-center gap-1">
                              <MessageSquare className="w-4 h-4" />
                              {history.usage_count} 次使用
                            </div>
                            {history.rating_avg > 0 && (
                              <div className="flex items-center gap-1">
                                <Star className="w-4 h-4 fill-current text-yellow-500" />
                                {history.rating_avg.toFixed(1)}
                              </div>
                            )}
                          </div>
                        </div>
                        
                        <div className="mb-3">
                          <h4 className="text-sm font-medium text-gray-700 mb-1 dark:text-gray-300">变更内容:</h4>
                          {renderChangesSummary(history.changes_summary)}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewVersion(history.version)}
                        >
                          <Eye className="w-4 h-4 mr-1" />
                          查看
                        </Button>
                        
                        {!history.is_latest && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleSetAsLatest(history.version)}
                            >
                              <CheckCircle className="w-4 h-4 mr-1" />
                              设为最新
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleRollback(history.version)}
                            >
                              <RotateCcw className="w-4 h-4 mr-1" />
                              回滚
                            </Button>
                          </>
                        )}
                        
                        {versionHistory.length > 1 && !history.is_latest && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteVersion(history.version)}
                            className="text-red-600 hover:text-red-700 dark:text-red-400"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* 版本比较 */}
        <TabsContent value="compare" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitCompare className="w-5 h-5" />
                选择要比较的版本
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                    版本 1
                  </label>
                  <select
                    value={compareVersion1}
                    onChange={(e) => setCompareVersion1(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600"
                  >
                    <option value="">选择版本</option>
                    {versions.map(version => (
                      <option key={version.id} value={version.version}>
                        版本 {version.version} {version.is_latest_version && '(最新)'}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                    版本 2
                  </label>
                  <select
                    value={compareVersion2}
                    onChange={(e) => setCompareVersion2(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md dark:border-gray-600"
                  >
                    <option value="">选择版本</option>
                    {versions.map(version => (
                      <option key={version.id} value={version.version}>
                        版本 {version.version} {version.is_latest_version && '(最新)'}
                      </option>
                    ))}
                  </select>
                </div>
                
                <Button 
                  onClick={handleCompareVersions}
                  disabled={comparing || !compareVersion1 || !compareVersion2}
                >
                  {comparing ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                      比较中...
                    </>
                  ) : (
                    <>
                      <GitCompare className="w-4 h-4 mr-2" />
                      开始比较
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {comparison && renderComparisonResult()}
        </TabsContent>

        {/* 创建版本 */}
        <TabsContent value="create" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="w-5 h-5" />
                创建新版本
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                  新标题 (可选)
                </label>
                <Input
                  type="text"
                  value={newVersionData.title || ''}
                  onChange={(e) => setNewVersionData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder={`当前: ${template.title}`}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                  新描述 (可选)
                </label>
                <Textarea
                  value={newVersionData.description || ''}
                  onChange={(e) => setNewVersionData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder={`当前: ${template.description}`}
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2 dark:text-gray-300">
                  新内容 (可选)
                </label>
                <Textarea
                  value={newVersionData.content || ''}
                  onChange={(e) => setNewVersionData(prev => ({ ...prev, content: e.target.value }))}
                  placeholder="输入新的模板内容，留空则保持不变"
                  rows={10}
                  className="font-mono text-sm"
                />
              </div>

              <div className="flex items-center gap-3">
                <Button 
                  onClick={handleCreateVersion}
                  disabled={creating}
                >
                  {creating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                      创建中...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      创建版本
                    </>
                  )}
                </Button>
                
                <Button 
                  variant="outline"
                  onClick={() => {
                    setNewVersionData({});
                    setShowCreateVersion(false);
                  }}
                >
                  取消
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
