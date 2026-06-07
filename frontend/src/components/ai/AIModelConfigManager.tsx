import React, { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Edit,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Star,
  StarOff,
  Trash2,
} from 'lucide-react';

import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/Card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';
import { Input } from '../ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/Select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/Table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs';
import { aiModelConfigService } from '../../services/aiModelConfigService';
import {
  AIModelConfig,
  AIModelConfigFilters,
  AIProvider,
  AIProviderStats,
  HealthStatus,
} from '../../types/aiModelConfig';
import { AIModelConfigForm } from './AIModelConfigForm';
import { AIModelTestDialog } from './AIModelTestDialog';
import { AIProviderStatsCard } from './AIProviderStatsCard';

const providerLabels: Record<AIProvider, string> = {
  [AIProvider.OPENAI]: 'OpenAI',
  [AIProvider.ANTHROPIC]: 'Anthropic',
  [AIProvider.BAIDU_WENXIN]: '百度文心',
  [AIProvider.ALIYUN_TONGYI]: '阿里通义',
  [AIProvider.GOOGLE_GEMINI]: 'Google Gemini',
  [AIProvider.ZHIPU_CHATGLM]: '智谱 ChatGLM',
  [AIProvider.XUNFEI_XINGHUO]: '讯飞星火',
  [AIProvider.CUSTOM]: '自定义',
};

const statusLabels: Record<HealthStatus, string> = {
  [HealthStatus.HEALTHY]: '健康',
  [HealthStatus.UNHEALTHY]: '异常',
  [HealthStatus.UNKNOWN]: '未知',
  [HealthStatus.ERROR]: '错误',
};

const getHealthIcon = (status?: HealthStatus) => {
  switch (status) {
    case HealthStatus.HEALTHY:
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    case HealthStatus.UNHEALTHY:
    case HealthStatus.ERROR:
      return <AlertCircle className="h-4 w-4 text-red-600" />;
    default:
      return <Activity className="h-4 w-4 text-muted-foreground" />;
  }
};

export const AIModelConfigManager: React.FC = () => {
  const [configs, setConfigs] = useState<AIModelConfig[]>([]);
  const [stats, setStats] = useState<AIProviderStats[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState<AIModelConfigFilters>({});
  const [selectedConfig, setSelectedConfig] = useState<AIModelConfig | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [configList, providerStats] = await Promise.all([
        aiModelConfigService.getModelConfigs({ ...filters, limit: 100 }),
        aiModelConfigService.getProviderStats(),
      ]);
      setConfigs(configList.items ?? []);
      setStats(providerStats ?? []);
    } catch (error) {
      console.error('Failed to load AI model configs:', error);
      toast.error('加载 AI 模型配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [filters.provider, filters.enabled_only, filters.public_only]);

  const filteredConfigs = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return configs;

    return configs.filter((config) =>
      [
        config.display_name,
        config.model_name,
        config.provider,
        config.description ?? '',
      ].some((value) => value.toLowerCase().includes(term)),
    );
  }, [configs, searchTerm]);

  const refreshData = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const handleSaved = (config: AIModelConfig) => {
    setConfigs((prev) => {
      const exists = prev.some((item) => item.id === config.id);
      return exists ? prev.map((item) => (item.id === config.id ? config : item)) : [config, ...prev];
    });
    setCreateOpen(false);
    setEditOpen(false);
    setSelectedConfig(null);
    void refreshData();
  };

  const toggleStatus = async (config: AIModelConfig) => {
    try {
      const updated = await aiModelConfigService.toggleModelStatus(config.id);
      setConfigs((prev) => prev.map((item) => (item.id === config.id ? updated : item)));
      toast.success(`${config.display_name} 已${updated.is_enabled ? '启用' : '禁用'}`);
    } catch (error) {
      console.error('Failed to toggle model status:', error);
      toast.error('更新模型状态失败');
    }
  };

  const setDefaultModel = async (config: AIModelConfig) => {
    try {
      const updated = await aiModelConfigService.setDefaultModel(config.id);
      setConfigs((prev) =>
        prev.map((item) =>
          item.provider === config.provider
            ? { ...item, is_default: item.id === config.id }
            : item,
        ),
      );
      setConfigs((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      toast.success(`${config.display_name} 已设为默认模型`);
    } catch (error) {
      console.error('Failed to set default model:', error);
      toast.error('设置默认模型失败');
    }
  };

  const deleteConfig = async (config: AIModelConfig) => {
    if (!window.confirm(`确定删除模型配置“${config.display_name}”吗？`)) return;

    try {
      await aiModelConfigService.deleteModelConfig(config.id);
      setConfigs((prev) => prev.filter((item) => item.id !== config.id));
      toast.success('模型配置已删除');
    } catch (error) {
      console.error('Failed to delete model config:', error);
      toast.error('删除模型配置失败');
    }
  };

  const healthCheck = async (config: AIModelConfig) => {
    try {
      const result = await aiModelConfigService.healthCheckModel(config.id);
      setConfigs((prev) =>
        prev.map((item) =>
          item.id === config.id
            ? { ...item, health_status: result.status, last_health_check: result.checked_at }
            : item,
        ),
      );
      if (result.status === HealthStatus.HEALTHY) {
        toast.success(`${config.display_name} 健康检查通过`);
      } else {
        toast.error(result.error || `${config.display_name} 健康检查异常`);
      }
    } catch (error) {
      console.error('Failed to check model health:', error);
      toast.error('健康检查失败');
    }
  };

  const batchHealthCheck = async () => {
    try {
      setRefreshing(true);
      const result = await aiModelConfigService.batchHealthCheck();
      setConfigs((prev) =>
        prev.map((config) => {
          const detail = result.details.find((item) => item.config_id === config.id);
          return detail
            ? {
                ...config,
                health_status: detail.status as HealthStatus,
                last_health_check: result.checked_at,
              }
            : config;
        }),
      );
      toast.success(`检查完成：健康 ${result.healthy}，异常 ${result.unhealthy}，未知 ${result.unknown}`);
    } catch (error) {
      console.error('Failed to batch check model health:', error);
      toast.error('批量健康检查失败');
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">AI 模型配置</h1>
          <p className="text-sm text-muted-foreground">维护模型供应商、接口参数、健康状态和默认模型。</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={refreshData} disabled={refreshing || loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button variant="outline" onClick={batchHealthCheck} disabled={refreshing || loading}>
            <Activity className="mr-2 h-4 w-4" />
            健康检查
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            新增模型
          </Button>
        </div>
      </div>

      <Tabs defaultValue="configs">
        <TabsList>
          <TabsTrigger value="configs">模型列表</TabsTrigger>
          <TabsTrigger value="stats">统计概览</TabsTrigger>
        </TabsList>

        <TabsContent value="configs" className="space-y-4">
          <Card>
            <CardContent className="grid gap-3 pt-6 md:grid-cols-[1fr_180px_160px_160px]">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="搜索显示名称、模型名或描述"
                />
              </div>

              <Select
                value={filters.provider ?? ''}
                onValueChange={(value) => setFilters((prev) => ({ ...prev, provider: value ? (value as AIProvider) : undefined }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="全部供应商" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部供应商</SelectItem>
                  {Object.values(AIProvider).map((provider) => (
                    <SelectItem key={provider} value={provider}>
                      {providerLabels[provider]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                value={filters.enabled_only === true ? 'enabled' : ''}
                onValueChange={(value) => setFilters((prev) => ({ ...prev, enabled_only: value === 'enabled' ? true : undefined }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="启用状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部状态</SelectItem>
                  <SelectItem value="enabled">仅启用</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={filters.public_only === true ? 'public' : ''}
                onValueChange={(value) => setFilters((prev) => ({ ...prev, public_only: value === 'public' ? true : undefined }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="公开范围" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">全部范围</SelectItem>
                  <SelectItem value="public">仅公开</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">模型列表</CardTitle>
              <CardDescription>共 {filteredConfigs.length} 个模型配置</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex h-48 items-center justify-center text-muted-foreground">
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  加载中
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>模型</TableHead>
                      <TableHead>供应商</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>健康</TableHead>
                      <TableHead>使用量</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredConfigs.map((config) => (
                      <TableRow key={config.id}>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 font-medium">
                              {config.display_name}
                              {config.is_default && <Badge>默认</Badge>}
                            </div>
                            <div className="text-xs text-muted-foreground">{config.model_name}</div>
                            {config.description && <div className="max-w-md truncate text-xs text-muted-foreground">{config.description}</div>}
                          </div>
                        </TableCell>
                        <TableCell>{providerLabels[config.provider] ?? config.provider}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            <Badge variant={config.is_enabled ? 'default' : 'secondary'}>
                              {config.is_enabled ? '启用' : '禁用'}
                            </Badge>
                            {config.is_public && <Badge variant="outline">公开</Badge>}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getHealthIcon(config.health_status)}
                            <span>{config.health_status ? statusLabels[config.health_status] : '未检查'}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">{config.total_requests?.toLocaleString() ?? 0} 次</div>
                          <div className="text-xs text-muted-foreground">{config.total_tokens_used?.toLocaleString() ?? 0} tokens</div>
                        </TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            <Button type="button" variant="ghost" size="icon" onClick={() => toggleStatus(config)} title={config.is_enabled ? '禁用' : '启用'}>
                              {config.is_enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                            </Button>
                            <Button type="button" variant="ghost" size="icon" onClick={() => setDefaultModel(config)} title="设为默认">
                              {config.is_default ? <Star className="h-4 w-4" /> : <StarOff className="h-4 w-4" />}
                            </Button>
                            <Button type="button" variant="ghost" size="icon" onClick={() => healthCheck(config)} title="健康检查">
                              <Activity className="h-4 w-4" />
                            </Button>
                            <Button type="button" variant="ghost" size="icon" onClick={() => { setSelectedConfig(config); setTestOpen(true); }} title="测试">
                              <Play className="h-4 w-4" />
                            </Button>
                            <Button type="button" variant="ghost" size="icon" onClick={() => { setSelectedConfig(config); setEditOpen(true); }} title="编辑">
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button type="button" variant="ghost" size="icon" onClick={() => deleteConfig(config)} title="删除">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                    {filteredConfigs.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                          暂无模型配置
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stats">
          <AIProviderStatsCard stats={stats} />
        </TabsContent>
      </Tabs>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-h-[90vh] max-w-5xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>新增 AI 模型</DialogTitle>
            <DialogDescription>填写模型供应商、接口和调用参数。</DialogDescription>
          </DialogHeader>
          <AIModelConfigForm onSuccess={handleSaved} onCancel={() => setCreateOpen(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-h-[90vh] max-w-5xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>编辑 AI 模型</DialogTitle>
            <DialogDescription>更新模型显示信息、接口参数和使用限制。</DialogDescription>
          </DialogHeader>
          {selectedConfig && (
            <AIModelConfigForm
              initialData={selectedConfig}
              onSuccess={handleSaved}
              onCancel={() => {
                setEditOpen(false);
                setSelectedConfig(null);
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      {selectedConfig && (
        <AIModelTestDialog
          config={selectedConfig}
          open={testOpen}
          onOpenChange={(open) => {
            setTestOpen(open);
            if (!open) setSelectedConfig(null);
          }}
        />
      )}
    </div>
  );
};
