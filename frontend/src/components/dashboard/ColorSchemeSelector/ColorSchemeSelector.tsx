import React, { useMemo, useRef, useState } from 'react';
import { Check, Copy, Download, Loader2, Palette, Plus, Trash2, Upload, X } from 'lucide-react';
import toast from 'react-hot-toast';

import { Alert, AlertDescription } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Switch } from '@/components/ui/Switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { useColorScheme } from '@/hooks/dashboard/useColorScheme';
import { ColorScheme, CreateColorSchemeRequest } from '@/services/dashboard/colorSchemeService';

interface ColorSchemeSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyScheme?: (schemeId: string) => void;
}

const typeLabels: Record<string, string> = {
  system: '系统',
  enterprise: '企业',
  custom: '自定义',
};

const applyColorsToDocument = (colors: string[]) => {
  const root = document.documentElement;
  const [primary, secondary, accent, danger] = colors;
  if (primary) root.style.setProperty('--dashboard-primary', primary);
  if (secondary) root.style.setProperty('--dashboard-secondary', secondary);
  if (accent) root.style.setProperty('--dashboard-accent', accent);
  if (danger) root.style.setProperty('--dashboard-danger', danger);
  localStorage.setItem('dashboard-color-scheme', JSON.stringify(colors));
};

const ColorSchemeSelector: React.FC<ColorSchemeSelectorProps> = ({ isOpen, onClose, onApplyScheme }) => {
  const {
    colorSchemes,
    userPreferences,
    effectiveColors,
    previewData,
    loading,
    previewLoading,
    error,
    applyColorScheme,
    createColorScheme,
    previewColorScheme,
    updateUserPreferences,
    deleteColorScheme,
    exportColorScheme,
    importColorScheme,
    copyColorsToClipboard,
    validateColorFormat,
    convertToHex,
    getCurrentScheme,
    getCategories,
  } = useColorScheme();

  const [activeTab, setActiveTab] = useState('preset');
  const [filterType, setFilterType] = useState('all');
  const [filterCategory, setFilterCategory] = useState('all');
  const [selectedSchemeId, setSelectedSchemeId] = useState<string | null>(null);
  const [customName, setCustomName] = useState('');
  const [customCategory, setCustomCategory] = useState('自定义');
  const [customDescription, setCustomDescription] = useState('');
  const [customColors, setCustomColors] = useState<string[]>(['#2563EB', '#10B981', '#F59E0B', '#EF4444']);
  const [isPublic, setIsPublic] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentScheme = getCurrentScheme();
  const categories = getCategories();

  const filteredSchemes = useMemo(() => {
    return colorSchemes.filter((scheme) => {
      if (filterType !== 'all' && scheme.type !== filterType) return false;
      if (filterCategory !== 'all' && scheme.category !== filterCategory) return false;
      return true;
    });
  }, [colorSchemes, filterCategory, filterType]);

  if (!isOpen) return null;

  const handleApply = async (scheme: ColorScheme) => {
    const success = await applyColorScheme(scheme.id, {
      applyToCharts: userPreferences?.applyToCharts ?? true,
      applyToWidgets: userPreferences?.applyToWidgets ?? true,
      applyToTheme: userPreferences?.applyToTheme ?? true,
    });

    if (success) {
      applyColorsToDocument(scheme.colors);
      setSelectedSchemeId(scheme.id);
      onApplyScheme?.(scheme.id);
      toast.success('配色已应用');
    }
  };

  const handleCreate = async () => {
    const name = customName.trim();
    if (!name) {
      toast.error('请输入方案名称');
      return;
    }

    if (customColors.length < 2 || customColors.some((color) => !validateColorFormat(color))) {
      toast.error('请至少提供两个有效颜色');
      return;
    }

    const request: CreateColorSchemeRequest = {
      name,
      category: customCategory.trim() || '自定义',
      colors: customColors.map(convertToHex),
      description: customDescription.trim() || undefined,
      isPublic,
    };

    const created = await createColorScheme(request);
    applyColorsToDocument(created.colors);
    setSelectedSchemeId(created.id);
    setCustomName('');
    setCustomDescription('');
    setCustomColors(['#2563EB', '#10B981', '#F59E0B', '#EF4444']);
  };

  const updateColor = (index: number, value: string) => {
    setCustomColors((prev) => {
      const next = [...prev];
      next[index] = value;
      if (next.length >= 2) previewColorScheme(next).catch(() => undefined);
      return next;
    });
  };

  const removeColor = (index: number) => {
    setCustomColors((prev) => prev.filter((_, i) => i !== index));
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await importColorScheme(file);
    event.target.value = '';
  };

  const handlePreferenceChange = async (key: 'applyToCharts' | 'applyToWidgets' | 'applyToTheme', checked: boolean) => {
    await updateUserPreferences({ [key]: checked });
    if (key === 'applyToTheme' && checked) {
      applyColorsToDocument(effectiveColors);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-h-[90vh] w-full max-w-5xl overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between border-b">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              配色方案
            </CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">选择或创建仪表盘配色，并立即应用到页面。</p>
          </div>
          <Button type="button" variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent className="max-h-[calc(90vh-90px)] overflow-y-auto p-6">
          {error && (
            <Alert className="mb-4 border-orange-200 bg-orange-50 text-orange-700">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="preset">方案库</TabsTrigger>
              <TabsTrigger value="custom">自定义</TabsTrigger>
              <TabsTrigger value="preferences">偏好设置</TabsTrigger>
            </TabsList>

            <TabsContent value="preset" className="space-y-4">
              <div className="grid gap-3 md:grid-cols-[180px_180px_1fr_auto]">
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger>
                    <SelectValue placeholder="类型" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部类型</SelectItem>
                    <SelectItem value="system">系统</SelectItem>
                    <SelectItem value="enterprise">企业</SelectItem>
                    <SelectItem value="custom">自定义</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={filterCategory} onValueChange={setFilterCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="分类" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部分类</SelectItem>
                    {categories.map((category) => (
                      <SelectItem key={category} value={category}>{category}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  当前方案：{currentScheme?.name ?? '未设置'}
                </div>

                <div className="flex gap-2">
                  <input ref={fileInputRef} type="file" accept=".json" className="hidden" onChange={handleImport} />
                  <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()}>
                    <Upload className="mr-2 h-4 w-4" />
                    导入
                  </Button>
                </div>
              </div>

              {loading ? (
                <div className="flex h-40 items-center justify-center text-muted-foreground">
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  加载中
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {filteredSchemes.map((scheme) => (
                    <SchemeCard
                      key={scheme.id}
                      scheme={scheme}
                      active={scheme.id === selectedSchemeId || scheme.id === userPreferences?.colorSchemeId}
                      onApply={() => handleApply(scheme)}
                      onPreview={() => previewColorScheme(scheme.colors).catch(() => undefined)}
                      onCopy={() => copyColorsToClipboard(scheme.colors)}
                      onExport={() => exportColorScheme(scheme)}
                      onDelete={scheme.type === 'custom' ? () => deleteColorScheme(scheme.id) : undefined}
                    />
                  ))}
                  {filteredSchemes.length === 0 && (
                    <div className="col-span-full flex h-40 items-center justify-center rounded-md border text-muted-foreground">
                      暂无配色方案
                    </div>
                  )}
                </div>
              )}
            </TabsContent>

            <TabsContent value="custom" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">方案名称</label>
                  <Input value={customName} onChange={(event) => setCustomName(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">分类</label>
                  <Input value={customCategory} onChange={(event) => setCustomCategory(event.target.value)} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <label className="text-sm font-medium">描述</label>
                  <Input value={customDescription} onChange={(event) => setCustomDescription(event.target.value)} />
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium">颜色</div>
                  <Button type="button" variant="outline" size="sm" onClick={() => setCustomColors((prev) => [...prev, '#000000'])}>
                    <Plus className="mr-2 h-4 w-4" />
                    添加颜色
                  </Button>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {customColors.map((color, index) => (
                    <div key={index} className="grid grid-cols-[44px_1fr_auto] items-center gap-2">
                      <input type="color" value={color} onChange={(event) => updateColor(index, event.target.value)} className="h-10 w-11 rounded border" />
                      <Input value={color} onChange={(event) => updateColor(index, event.target.value)} />
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeColor(index)} disabled={customColors.length <= 2}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              <Switch checked={isPublic} onChange={(event) => setIsPublic(event.target.checked)} label="公开这个配色方案" />

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => previewColorScheme(customColors).catch(() => undefined)} disabled={previewLoading}>
                  {previewLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  预览
                </Button>
                <Button type="button" onClick={handleCreate}>保存方案</Button>
              </div>
            </TabsContent>

            <TabsContent value="preferences" className="space-y-4">
              <Card>
                <CardContent className="space-y-4 pt-6">
                  <Switch
                    checked={userPreferences?.applyToCharts ?? true}
                    onChange={(event) => handlePreferenceChange('applyToCharts', event.target.checked)}
                    label="应用到图表"
                  />
                  <Switch
                    checked={userPreferences?.applyToWidgets ?? true}
                    onChange={(event) => handlePreferenceChange('applyToWidgets', event.target.checked)}
                    label="应用到组件"
                  />
                  <Switch
                    checked={userPreferences?.applyToTheme ?? true}
                    onChange={(event) => handlePreferenceChange('applyToTheme', event.target.checked)}
                    label="应用到页面主题"
                  />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <PreviewPanel title="当前生效颜色" colors={effectiveColors} />
            <PreviewPanel title="预览分析" colors={previewData?.colorPalette ?? customColors} description={previewData?.recommendations?.join('；')} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

interface SchemeCardProps {
  scheme: ColorScheme;
  active: boolean;
  onApply: () => void;
  onPreview: () => void;
  onCopy: () => void;
  onExport: () => void;
  onDelete?: () => void;
}

const SchemeCard: React.FC<SchemeCardProps> = ({ scheme, active, onApply, onPreview, onCopy, onExport, onDelete }) => (
  <Card className={active ? 'border-primary' : ''}>
    <CardHeader className="pb-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <CardTitle className="text-base">{scheme.name}</CardTitle>
          <div className="mt-1 flex gap-1">
            <Badge variant="outline">{typeLabels[scheme.type] ?? scheme.type}</Badge>
            {scheme.category && <Badge variant="secondary">{scheme.category}</Badge>}
          </div>
        </div>
        {active && <Check className="h-5 w-5 text-primary" />}
      </div>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="flex overflow-hidden rounded-md border">
        {scheme.colors.map((color, index) => (
          <div key={`${color}-${index}`} className="h-10 flex-1" style={{ backgroundColor: color }} />
        ))}
      </div>
      {scheme.description && <p className="line-clamp-2 text-sm text-muted-foreground">{scheme.description}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" onClick={onApply}>应用</Button>
        <Button type="button" variant="outline" size="sm" onClick={onPreview}>预览</Button>
        <Button type="button" variant="ghost" size="icon" onClick={onCopy}><Copy className="h-4 w-4" /></Button>
        <Button type="button" variant="ghost" size="icon" onClick={onExport}><Download className="h-4 w-4" /></Button>
        {onDelete && <Button type="button" variant="ghost" size="icon" onClick={onDelete}><Trash2 className="h-4 w-4" /></Button>}
      </div>
    </CardContent>
  </Card>
);

const PreviewPanel: React.FC<{ title: string; colors: string[]; description?: string }> = ({ title, colors, description }) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-base">{title}</CardTitle>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="flex overflow-hidden rounded-md border">
        {colors.map((color, index) => (
          <div key={`${color}-${index}`} className="h-12 flex-1" style={{ backgroundColor: color }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {colors.map((color) => (
          <Badge key={color} variant="outline">{color}</Badge>
        ))}
      </div>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
    </CardContent>
  </Card>
);

export default ColorSchemeSelector;
