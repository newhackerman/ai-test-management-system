/**
 * 提示词模板编辑器
 * 提供可视化的模板编辑功能，包括内容编辑、变量管理、预览等
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { 
  Save, 
  Eye, 
  Code, 
  Settings, 
  Plus, 
  Trash2, 
  AlertCircle, 
  CheckCircle,
  Copy,
  Download,
  Upload,
  Wand2,
  Variable,
  Tag,
  Globe,
  Lock,
  Users,
  GitBranch,
  History
} from 'lucide-react';
import { useToast } from '@/hooks/useToast';
import { 
  PromptTemplate, 
  PromptTemplateCreate, 
  PromptTemplateUpdate, 
  TemplateVariable,
  promptTemplateService 
} from '@/services/prompt-template-service';
import { TemplateVersionManager } from './TemplateVersionManager';
import { TemplateTestingPanel } from './TemplateTestingPanel';

interface TemplateEditorProps {
  template?: PromptTemplate;
  onSave?: (template: PromptTemplate) => void;
  onCancel?: () => void;
  mode?: 'create' | 'edit';
}

interface ValidationError {
  field: string;
  message: string;
}

export function TemplateEditor({ 
  template, 
  onSave, 
  onCancel, 
  mode = 'create' 
}: TemplateEditorProps) {
  const { toast } = useToast();
  
  // 表单状态
  const [formData, setFormData] = useState<PromptTemplateCreate>({
    name: '',
    title: '',
    description: '',
    category: 'GENERAL',
    content: '',
    variables: [],
    default_values: {},
    example_context: {},
    supported_providers: ['openai', 'anthropic'],
    supported_models: [],
    use_cases: [],
    tags: [],
    visibility: 'PRIVATE'
  });

  // UI状态
  const [activeTab, setActiveTab] = useState('basic');
  const [isLoading, setSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [syntaxErrors, setSyntaxErrors] = useState<string[]>([]);
  const [previewContent, setPreviewContent] = useState('');
  const [categories, setCategories] = useState<any[]>([]);
  const [visibilityOptions, setVisibilityOptions] = useState<any[]>([]);

  // 变量编辑状态
  const [newVariable, setNewVariable] = useState<Partial<TemplateVariable>>({
    name: '',
    type: 'string',
    description: '',
    required: true
  });

  // 版本管理状态
  const [showVersionManager, setShowVersionManager] = useState(false);

  // 模板测试状态
  const [showTestingPanel, setShowTestingPanel] = useState(false);

  // 初始化数据
  useEffect(() => {
    if (template && mode === 'edit') {
      setFormData({
        name: template.name,
        title: template.title,
        description: template.description,
        category: template.category,
        subcategory: template.subcategory,
        content: template.content,
        variables: template.variables || [],
        default_values: template.default_values || {},
        example_context: template.example_context || {},
        supported_providers: template.supported_providers || [],
        supported_models: template.supported_models || [],
        use_cases: template.use_cases || [],
        tags: template.tags || [],
        visibility: template.visibility,
        team_id: template.team_id
      });
    }
  }, [template, mode]);

  // 加载分类和可见性选项
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [categoriesData, visibilityData] = await Promise.all([
          promptTemplateService.getCategories(),
          promptTemplateService.getVisibilityOptions()
        ]);
        setCategories(categoriesData);
        setVisibilityOptions(visibilityData);
      } catch (error) {
        console.error('Failed to load options:', error);
      }
    };
    loadOptions();
  }, []);

  // 实时语法验证
  useEffect(() => {
    if (formData.content) {
      const validation = promptTemplateService.validateTemplateSyntax(formData.content);
      setSyntaxErrors(validation.errors);
      
      // 更新预览
      if (validation.isValid) {
        const preview = promptTemplateService.previewTemplate(formData.content, formData.example_context);
        setPreviewContent(preview);
      }
    }
  }, [formData.content, formData.example_context]);

  // 表单验证
  const validateForm = (): ValidationError[] => {
    const errors: ValidationError[] = [];

    if (!formData.name.trim()) {
      errors.push({ field: 'name', message: '模板名称不能为空' });
    }

    if (!formData.title.trim()) {
      errors.push({ field: 'title', message: '模板标题不能为空' });
    }

    if (!formData.content.trim()) {
      errors.push({ field: 'content', message: '模板内容不能为空' });
    }

    if (syntaxErrors.length > 0) {
      errors.push({ field: 'content', message: '模板语法错误' });
    }

    return errors;
  };

  // 保存模板
  const handleSave = async () => {
    const errors = validateForm();
    if (errors.length > 0) {
      setValidationErrors(errors);
      toast({
        title: '验证失败',
        description: '请修复表单中的错误',
        variant: 'destructive'
      });
      return;
    }

    setSaving(true);
    try {
      let savedTemplate: PromptTemplate;
      
      if (mode === 'create') {
        savedTemplate = await promptTemplateService.createTemplate(formData);
        toast({
          title: '创建成功',
          description: '模板已成功创建',
          variant: 'success'
        });
      } else {
        savedTemplate = await promptTemplateService.updateTemplate(
          template!.id, 
          formData as PromptTemplateUpdate
        );
        toast({
          title: '更新成功',
          description: '模板已成功更新',
          variant: 'success'
        });
      }

      onSave?.(savedTemplate);
    } catch (error: any) {
      toast({
        title: '保存失败',
        description: error.message || '保存模板时发生错误',
        variant: 'destructive'
      });
    } finally {
      setSaving(false);
    }
  };

  // 添加变量
  const handleAddVariable = () => {
    if (!newVariable.name || !newVariable.description) {
      toast({
        title: '请填写完整信息',
        description: '变量名称和描述不能为空',
        variant: 'destructive'
      });
      return;
    }

    const variable: TemplateVariable = {
      name: newVariable.name!,
      type: newVariable.type as any,
      description: newVariable.description!,
      required: newVariable.required!,
      default_value: newVariable.default_value,
      validation_rules: newVariable.validation_rules
    };

    setFormData(prev => ({
      ...prev,
      variables: [...prev.variables, variable]
    }));

    setNewVariable({
      name: '',
      type: 'string',
      description: '',
      required: true
    });

    toast({
      title: '变量已添加',
      description: `变量 ${variable.name} 已成功添加`,
      variant: 'success'
    });
  };

  // 删除变量
  const handleRemoveVariable = (index: number) => {
    setFormData(prev => ({
      ...prev,
      variables: prev.variables.filter((_, i) => i !== index)
    }));
  };

  // 自动检测变量
  const handleAutoDetectVariables = () => {
    const detectedVars = promptTemplateService.extractVariables(formData.content);
    const existingVarNames = formData.variables.map(v => v.name);
    
    const newVariables: TemplateVariable[] = detectedVars
      .filter(varName => !existingVarNames.includes(varName))
      .map(varName => ({
        name: varName,
        type: 'string',
        description: `自动检测的变量: ${varName}`,
        required: true
      }));

    if (newVariables.length > 0) {
      setFormData(prev => ({
        ...prev,
        variables: [...prev.variables, ...newVariables]
      }));

      toast({
        title: '变量检测完成',
        description: `检测到 ${newVariables.length} 个新变量`,
        variant: 'success'
      });
    } else {
      toast({
        title: '未发现新变量',
        description: '模板中的所有变量都已定义',
        variant: 'info'
      });
    }
  };

  // 导入模板
  const handleImportTemplate = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result as string);
        setFormData(prev => ({
          ...prev,
          ...imported,
          name: imported.name + '_imported',
          visibility: 'PRIVATE' // 导入的模板默认为私有
        }));
        
        toast({
          title: '导入成功',
          description: '模板已成功导入',
          variant: 'success'
        });
      } catch (error) {
        toast({
          title: '导入失败',
          description: '文件格式不正确',
          variant: 'destructive'
        });
      }
    };
    reader.readAsText(file);
  };

  // 导出模板
  const handleExportTemplate = () => {
    const exportData = {
      ...formData,
      exported_at: new Date().toISOString(),
      version: '1.0'
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${formData.name || 'template'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: '导出成功',
      description: '模板已导出到本地',
      variant: 'success'
    });
  };

  // 获取字段错误
  const getFieldError = (field: string) => {
    return validationErrors.find(error => error.field === field)?.message;
  };

  // 处理版本变更
  const handleVersionChange = (newVersion: PromptTemplate) => {
    setFormData({
      name: newVersion.name,
      title: newVersion.title,
      description: newVersion.description,
      category: newVersion.category,
      subcategory: newVersion.subcategory,
      content: newVersion.content,
      variables: newVersion.variables || [],
      default_values: newVersion.default_values || {},
      example_context: newVersion.example_context || {},
      supported_providers: newVersion.supported_providers || [],
      supported_models: newVersion.supported_models || [],
      use_cases: newVersion.use_cases || [],
      tags: newVersion.tags || [],
      visibility: newVersion.visibility,
      team_id: newVersion.team_id
    });
    
    onSave?.(newVersion);
  };

  // 如果显示版本管理器，渲染版本管理器
  if (showVersionManager && template) {
    return (
      <TemplateVersionManager
        template={template}
        onVersionChange={handleVersionChange}
        onClose={() => setShowVersionManager(false)}
      />
    );
  }

  // 如果显示测试面板，渲染测试面板
  if (showTestingPanel && template) {
    return (
      <TemplateTestingPanel
        template={template}
        onClose={() => setShowTestingPanel(false)}
      />
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">
              {mode === 'create' ? '创建提示词模板' : '编辑提示词模板'}
            </h1>
            {mode === 'edit' && template && (
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="flex items-center gap-1">
                  <History className="w-3 h-3" />
                  版本 {template.version}
                </Badge>
                {template.is_latest_version && (
                  <Badge variant="default" className="bg-green-600">
                    最新版本
                  </Badge>
                )}
              </div>
            )}
          </div>
          <p className="text-gray-600 mt-1">
            {mode === 'create' 
              ? '创建一个新的提示词模板，可以在AI对话中重复使用'
              : '修改现有的提示词模板内容和设置'
            }
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* 版本管理 */}
          {mode === 'edit' && template && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowVersionManager(true)}
            >
              <GitBranch className="w-4 h-4 mr-2" />
              版本管理
            </Button>
          )}

          {/* 模板测试 */}
          {mode === 'edit' && template && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowTestingPanel(true)}
            >
              <Wand2 className="w-4 h-4 mr-2" />
              测试模板
            </Button>
          )}

          {/* 导入/导出 */}
          <div className="flex items-center gap-2">
            <input
              type="file"
              accept=".json"
              onChange={handleImportTemplate}
              className="hidden"
              id="import-template"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => document.getElementById('import-template')?.click()}
            >
              <Upload className="w-4 h-4 mr-2" />
              导入
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportTemplate}
            >
              <Download className="w-4 h-4 mr-2" />
              导出
            </Button>
          </div>

          {/* 操作按钮 */}
          <Button variant="outline" onClick={onCancel}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                保存
              </>
            )}
          </Button>
        </div>
      </div>

      {/* 语法错误提示 */}
      {syntaxErrors.length > 0 && (
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-800 mb-2">模板语法错误</h3>
                <ul className="text-sm text-red-700 space-y-1">
                  {syntaxErrors.map((error, index) => (
                    <li key={index}>• {error}</li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basic">基本信息</TabsTrigger>
          <TabsTrigger value="content">模板内容</TabsTrigger>
          <TabsTrigger value="variables">变量管理</TabsTrigger>
          <TabsTrigger value="settings">高级设置</TabsTrigger>
        </TabsList>

        {/* 基本信息 */}
        <TabsContent value="basic" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>基本信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    模板名称 *
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="输入模板名称"
                    className={getFieldError('name') ? 'border-red-300' : ''}
                  />
                  {getFieldError('name') && (
                    <p className="text-sm text-red-600 mt-1">{getFieldError('name')}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    模板标题 *
                  </label>
                  <Input
                    value={formData.title}
                    onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="输入模板标题"
                    className={getFieldError('title') ? 'border-red-300' : ''}
                  />
                  {getFieldError('title') && (
                    <p className="text-sm text-red-600 mt-1">{getFieldError('title')}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    模板描述
                  </label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="描述模板的用途和特点"
                    rows={3}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    分类
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  >
                    {categories.map(category => (
                      <option key={category.value} value={category.value}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    子分类
                  </label>
                  <Input
                    value={formData.subcategory || ''}
                    onChange={(e) => setFormData(prev => ({ ...prev, subcategory: e.target.value }))}
                    placeholder="可选的子分类"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>可见性和权限</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    可见性
                  </label>
                  <div className="space-y-2">
                    {visibilityOptions.map(option => (
                      <label key={option.value} className="flex items-center gap-3">
                        <input
                          type="radio"
                          name="visibility"
                          value={option.value}
                          checked={formData.visibility === option.value}
                          onChange={(e) => setFormData(prev => ({ ...prev, visibility: e.target.value as any }))}
                          className="w-4 h-4"
                        />
                        <div className="flex items-center gap-2">
                          {option.value === 'PRIVATE' && <Lock className="w-4 h-4" />}
                          {option.value === 'TEAM' && <Users className="w-4 h-4" />}
                          {option.value === 'PUBLIC' && <Globe className="w-4 h-4" />}
                          <div>
                            <div className="font-medium">{option.label}</div>
                            <div className="text-sm text-gray-500">{option.description}</div>
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    标签
                  </label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {formData.tags.map((tag, index) => (
                      <Badge key={index} variant="secondary" className="flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {tag}
                        <button
                          onClick={() => setFormData(prev => ({
                            ...prev,
                            tags: prev.tags.filter((_, i) => i !== index)
                          }))}
                          className="ml-1 hover:text-red-600"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      placeholder="添加标签"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          const value = (e.target as HTMLInputElement).value.trim();
                          if (value && !formData.tags.includes(value)) {
                            setFormData(prev => ({
                              ...prev,
                              tags: [...prev.tags, value]
                            }));
                            (e.target as HTMLInputElement).value = '';
                          }
                        }
                      }}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    使用场景
                  </label>
                  <Textarea
                    value={formData.use_cases.join('\n')}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      use_cases: e.target.value.split('\n').filter(line => line.trim())
                    }))}
                    placeholder="每行一个使用场景"
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 模板内容 */}
        <TabsContent value="content" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="w-5 h-5" />
                  模板编辑器
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Textarea
                    value={formData.content}
                    onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
                    placeholder="输入模板内容，使用 {变量名} 来定义变量"
                    rows={15}
                    className={`font-mono text-sm ${getFieldError('content') ? 'border-red-300' : ''}`}
                  />
                  {getFieldError('content') && (
                    <p className="text-sm text-red-600">{getFieldError('content')}</p>
                  )}
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleAutoDetectVariables}
                    >
                      <Wand2 className="w-4 h-4 mr-2" />
                      自动检测变量
                    </Button>
                    
                    <div className="text-sm text-gray-500">
                      字符数: {formData.content.length}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="w-5 h-5" />
                  实时预览
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 bg-gray-50 rounded-lg border min-h-[300px]">
                    {syntaxErrors.length > 0 ? (
                      <div className="text-red-600">
                        <AlertCircle className="w-5 h-5 inline mr-2" />
                        模板包含语法错误，无法预览
                      </div>
                    ) : previewContent ? (
                      <div className="whitespace-pre-wrap text-sm">
                        {previewContent}
                      </div>
                    ) : (
                      <div className="text-gray-400 text-center py-8">
                        输入模板内容以查看预览
                      </div>
                    )}
                  </div>
                  
                  {syntaxErrors.length === 0 && (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <CheckCircle className="w-4 h-4" />
                      模板语法正确
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 变量管理 */}
        <TabsContent value="variables" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Variable className="w-5 h-5" />
                  变量列表
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {formData.variables.length === 0 ? (
                    <div className="text-center py-8 text-gray-400">
                      暂无变量，请添加变量或使用自动检测功能
                    </div>
                  ) : (
                    formData.variables.map((variable, index) => (
                      <div key={index} className="p-3 border rounded-lg">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                                {variable.name}
                              </code>
                              <Badge variant={variable.required ? 'default' : 'secondary'}>
                                {variable.required ? '必需' : '可选'}
                              </Badge>
                              <Badge variant="outline">{variable.type}</Badge>
                            </div>
                            <p className="text-sm text-gray-600">{variable.description}</p>
                            {variable.default_value && (
                              <p className="text-xs text-gray-500 mt-1">
                                默认值: {String(variable.default_value)}
                              </p>
                            )}
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveVariable(index)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>添加变量</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    变量名称 *
                  </label>
                  <Input
                    value={newVariable.name || ''}
                    onChange={(e) => setNewVariable(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="变量名称（如：user_name）"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    变量类型
                  </label>
                  <select
                    value={newVariable.type}
                    onChange={(e) => setNewVariable(prev => ({ ...prev, type: e.target.value as any }))}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  >
                    <option value="string">字符串</option>
                    <option value="number">数字</option>
                    <option value="boolean">布尔值</option>
                    <option value="array">数组</option>
                    <option value="object">对象</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    变量描述 *
                  </label>
                  <Textarea
                    value={newVariable.description || ''}
                    onChange={(e) => setNewVariable(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="描述变量的用途和格式"
                    rows={2}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    默认值
                  </label>
                  <Input
                    value={newVariable.default_value == null ? '' : String(newVariable.default_value)}
                    onChange={(e) => setNewVariable(prev => ({ ...prev, default_value: e.target.value }))}
                    placeholder="可选的默认值"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="required"
                    checked={newVariable.required}
                    onChange={(e) => setNewVariable(prev => ({ ...prev, required: e.target.checked }))}
                    className="w-4 h-4"
                  />
                  <label htmlFor="required" className="text-sm font-medium text-gray-700">
                    必需变量
                  </label>
                </div>

                <Button onClick={handleAddVariable} className="w-full">
                  <Plus className="w-4 h-4 mr-2" />
                  添加变量
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* 示例上下文 */}
          <Card>
            <CardHeader>
              <CardTitle>示例上下文</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  为模板变量提供示例值，用于预览和测试模板效果
                </p>
                <Textarea
                  value={JSON.stringify(formData.example_context, null, 2)}
                  onChange={(e) => {
                    try {
                      const parsed = JSON.parse(e.target.value);
                      setFormData(prev => ({ ...prev, example_context: parsed }));
                    } catch (error) {
                      // 忽略JSON解析错误，用户可能正在编辑
                    }
                  }}
                  placeholder='{"variable_name": "example_value"}'
                  rows={6}
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 高级设置 */}
        <TabsContent value="settings" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>AI模型支持</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    支持的AI提供商
                  </label>
                  <div className="space-y-2">
                    {['openai', 'anthropic', 'baidu_wenxin', 'aliyun_tongyi'].map(provider => (
                      <label key={provider} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={formData.supported_providers.includes(provider)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormData(prev => ({
                                ...prev,
                                supported_providers: [...prev.supported_providers, provider]
                              }));
                            } else {
                              setFormData(prev => ({
                                ...prev,
                                supported_providers: prev.supported_providers.filter(p => p !== provider)
                              }));
                            }
                          }}
                          className="w-4 h-4"
                        />
                        <span className="capitalize">{provider.replace('_', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    推荐模型
                  </label>
                  <Textarea
                    value={formData.supported_models.join('\n')}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      supported_models: e.target.value.split('\n').filter(line => line.trim())
                    }))}
                    placeholder="每行一个模型名称"
                    rows={4}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>默认值配置</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <p className="text-sm text-gray-600">
                    为模板变量设置默认值，当用户未提供值时使用
                  </p>
                  <Textarea
                    value={JSON.stringify(formData.default_values, null, 2)}
                    onChange={(e) => {
                      try {
                        const parsed = JSON.parse(e.target.value);
                        setFormData(prev => ({ ...prev, default_values: parsed }));
                      } catch (error) {
                        // 忽略JSON解析错误
                      }
                    }}
                    placeholder='{"variable_name": "default_value"}'
                    rows={8}
                    className="font-mono text-sm"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
