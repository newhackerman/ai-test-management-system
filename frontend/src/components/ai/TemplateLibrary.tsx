/**
 * 提示词模板库
 * 提供模板浏览、搜索、管理功能
 */
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { 
  Search, 
  Plus, 
  Edit, 
  Trash2, 
  Copy, 
  Star, 
  Eye, 
  Filter,
  Grid,
  List,
  Download,
  Share,
  MoreHorizontal,
  Tag,
  Calendar,
  User,
  TrendingUp,
  Heart,
  MessageSquare,
  Globe,
  Lock,
  Users,
  GitBranch,
  History
} from 'lucide-react';
import { useToast } from '@/hooks/useToast';
import { 
  PromptTemplate, 
  TemplateListResponse,
  TemplateSearchRequest,
  promptTemplateService 
} from '@/services/prompt-template-service';
import { TemplateEditor } from './TemplateEditor';
import { TemplateVersionManager } from './TemplateVersionManager';
import { TemplateTestingPanel } from './TemplateTestingPanel';

interface TemplateLibraryProps {
  onSelectTemplate?: (template: PromptTemplate) => void;
  onEditTemplate?: (template: PromptTemplate) => void;
  showActions?: boolean;
}

type ViewMode = 'grid' | 'list';
type FilterTab = 'all' | 'my' | 'public' | 'featured';

export function TemplateLibrary({ 
  onSelectTemplate, 
  onEditTemplate, 
  showActions = true 
}: TemplateLibraryProps) {
  const { toast } = useToast();

  // 状态管理
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [showEditor, setShowEditor] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  
  // 版本管理状态
  const [showVersionManager, setShowVersionManager] = useState(false);
  const [versionManagingTemplate, setVersionManagingTemplate] = useState<PromptTemplate | null>(null);

  // 模板测试状态
  const [showTestingPanel, setShowTestingPanel] = useState(false);
  const [testingTemplate, setTestingTemplate] = useState<PromptTemplate | null>(null);
  
  // 搜索和筛选
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedVisibility, setSelectedVisibility] = useState('');
  const [sortBy, setSortBy] = useState('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // 分页
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 12;

  // 选项数据
  const [categories, setCategories] = useState<any[]>([]);
  const [visibilityOptions, setVisibilityOptions] = useState<any[]>([]);

  // 加载模板数据
  const loadTemplates = async () => {
    setLoading(true);
    try {
      const searchRequest: TemplateSearchRequest = {
        query: searchQuery || undefined,
        category: selectedCategory || undefined,
        visibility: selectedVisibility || undefined,
        is_featured: activeTab === 'featured' ? true : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page: currentPage,
        size: pageSize
      };

      let response: TemplateListResponse;
      
      if (activeTab === 'my') {
        response = await promptTemplateService.getMyTemplates({
          category: selectedCategory || undefined,
          page: currentPage,
          size: pageSize
        });
      } else {
        response = await promptTemplateService.searchTemplates(searchRequest);
      }

      setTemplates(response.templates);
      setTotalPages(response.pages);
      setTotalCount(response.total);
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '加载模板列表失败',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  // 加载选项数据
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

  // 初始化
  useEffect(() => {
    loadOptions();
  }, []);

  // 数据变化时重新加载
  useEffect(() => {
    loadTemplates();
  }, [
    activeTab, 
    searchQuery, 
    selectedCategory, 
    selectedVisibility, 
    sortBy, 
    sortOrder, 
    currentPage
  ]);

  // 搜索处理
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
  };

  // 筛选处理
  const handleFilterChange = (type: string, value: string) => {
    if (type === 'category') {
      setSelectedCategory(value);
    } else if (type === 'visibility') {
      setSelectedVisibility(value);
    }
    setCurrentPage(1);
  };

  // 排序处理
  const handleSortChange = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setCurrentPage(1);
  };

  // 创建新模板
  const handleCreateTemplate = () => {
    setEditingTemplate(null);
    setShowEditor(true);
  };

  // 编辑模板
  const handleEditTemplate = (template: PromptTemplate) => {
    setEditingTemplate(template);
    setShowEditor(true);
    onEditTemplate?.(template);
  };

  // 复制模板
  const handleCopyTemplate = async (template: PromptTemplate) => {
    try {
      const newTemplate = {
        ...template,
        name: `${template.name}_copy`,
        title: `${template.title} (副本)`,
        visibility: 'PRIVATE' as const
      };
      
      // 移除不需要的字段
      const { id, owner_id, created_at, updated_at, usage_count, rating_avg, rating_count, last_used_at, ...templateData } = newTemplate;
      
      const created = await promptTemplateService.createTemplate(templateData);
      
      toast({
        title: '复制成功',
        description: '模板已复制到您的模板库',
        variant: 'success'
      });
      
      loadTemplates();
    } catch (error: any) {
      toast({
        title: '复制失败',
        description: error.message || '复制模板失败',
        variant: 'destructive'
      });
    }
  };

  // 删除模板
  const handleDeleteTemplate = async (template: PromptTemplate) => {
    if (!confirm(`确定要删除模板 "${template.title}" 吗？此操作不可撤销。`)) {
      return;
    }

    try {
      await promptTemplateService.deleteTemplate(template.id);
      
      toast({
        title: '删除成功',
        description: '模板已成功删除',
        variant: 'success'
      });
      
      loadTemplates();
    } catch (error: any) {
      toast({
        title: '删除失败',
        description: error.message || '删除模板失败',
        variant: 'destructive'
      });
    }
  };

  // 使用模板
  const handleUseTemplate = (template: PromptTemplate) => {
    onSelectTemplate?.(template);
  };

  // 版本管理
  const handleVersionManagement = (template: PromptTemplate) => {
    setVersionManagingTemplate(template);
    setShowVersionManager(true);
  };

  // 模板测试
  const handleTestTemplate = (template: PromptTemplate) => {
    setTestingTemplate(template);
    setShowTestingPanel(true);
  };

  // 版本变更处理
  const handleVersionChange = (newVersion: PromptTemplate) => {
    loadTemplates(); // 重新加载模板列表
  };

  // 保存模板后的处理
  const handleTemplateSaved = (template: PromptTemplate) => {
    setShowEditor(false);
    setEditingTemplate(null);
    loadTemplates();
  };

  // 获取可见性图标
  const getVisibilityIcon = (visibility: string) => {
    switch (visibility) {
      case 'PUBLIC': return <Globe className="w-4 h-4" />;
      case 'TEAM': return <Users className="w-4 h-4" />;
      case 'PRIVATE': return <Lock className="w-4 h-4" />;
      default: return <Lock className="w-4 h-4" />;
    }
  };

  // 获取可见性颜色
  const getVisibilityColor = (visibility: string) => {
    switch (visibility) {
      case 'PUBLIC': return 'text-green-600';
      case 'TEAM': return 'text-blue-600';
      case 'PRIVATE': return 'text-gray-600 dark:text-gray-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  // 模板卡片组件
  const TemplateCard = ({ template }: { template: PromptTemplate }) => (
    <Card className="group hover:shadow-lg transition-shadow duration-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-semibold text-lg truncate">{template.title}</h3>
              {template.is_featured && (
                <Badge variant="default" className="bg-yellow-100 text-yellow-800">
                  <Star className="w-3 h-3 mr-1" />
                  精选
                </Badge>
              )}
              {template.is_verified && (
                <Badge variant="default" className="bg-green-100 text-green-800">
                  验证
                </Badge>
              )}
            </div>
            <p className="text-sm text-gray-600 line-clamp-2 mb-2 dark:text-gray-400">
              {template.description}
            </p>
            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <div className={`flex items-center gap-1 ${getVisibilityColor(template.visibility)}`}>
                {getVisibilityIcon(template.visibility)}
                {template.visibility}
              </div>
              <div className="flex items-center gap-1">
                <History className="w-3 h-3" />
                v{template.version}
              </div>
              <div className="flex items-center gap-1">
                <MessageSquare className="w-3 h-3" />
                {template.usage_count}
              </div>
              {template.rating_count > 0 && (
                <div className="flex items-center gap-1">
                  <Star className="w-3 h-3 fill-current text-yellow-500" />
                  {template.rating_avg.toFixed(1)}
                </div>
              )}
            </div>
          </div>
          
          {showActions && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleUseTemplate(template)}
                title="使用模板"
              >
                <Eye className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopyTemplate(template)}
                title="复制模板"
              >
                <Copy className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleEditTemplate(template)}
                title="编辑模板"
              >
                <Edit className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleVersionManagement(template)}
                title="版本管理"
              >
                <GitBranch className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleTestTemplate(template)}
                title="测试模板"
              >
                <TrendingUp className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDeleteTemplate(template)}
                title="删除模板"
                className="text-red-600 hover:text-red-700 dark:text-red-400"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-1">
            <Badge variant="outline" className="text-xs">
              {categories.find(c => c.value === template.category)?.label || template.category}
            </Badge>
            {template.tags.slice(0, 3).map((tag, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                <Tag className="w-2 h-2 mr-1" />
                {tag}
              </Badge>
            ))}
            {template.tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{template.tags.length - 3}
              </Badge>
            )}
          </div>
          
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-1">
              <User className="w-3 h-3" />
              {template.owner_id}
            </div>
            <div className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {new Date(template.updated_at).toLocaleDateString()}
            </div>
          </div>
          
          {showActions && (
            <Button 
              onClick={() => handleUseTemplate(template)}
              className="w-full"
              size="sm"
            >
              使用模板
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );

  // 列表视图组件
  const TemplateListItem = ({ template }: { template: PromptTemplate }) => (
    <Card className="group hover:shadow-md transition-shadow duration-200">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold truncate">{template.title}</h3>
                  {template.is_featured && (
                    <Badge variant="default" className="bg-yellow-100 text-yellow-800">
                      <Star className="w-3 h-3 mr-1" />
                      精选
                    </Badge>
                  )}
                  <div className={`flex items-center gap-1 ${getVisibilityColor(template.visibility)}`}>
                    {getVisibilityIcon(template.visibility)}
                  </div>
                </div>
                <p className="text-sm text-gray-600 line-clamp-1 mb-2 dark:text-gray-400">
                  {template.description}
                </p>
                <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                  <Badge variant="outline" className="text-xs">
                    {categories.find(c => c.value === template.category)?.label || template.category}
                  </Badge>
                  <div className="flex items-center gap-1">
                    <History className="w-3 h-3" />
                    v{template.version}
                  </div>
                  <div className="flex items-center gap-1">
                    <MessageSquare className="w-3 h-3" />
                    {template.usage_count} 次使用
                  </div>
                  {template.rating_count > 0 && (
                    <div className="flex items-center gap-1">
                      <Star className="w-3 h-3 fill-current text-yellow-500" />
                      {template.rating_avg.toFixed(1)}
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(template.updated_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {showActions && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleUseTemplate(template)}
              >
                使用
              </Button>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleCopyTemplate(template)}
                  title="复制"
                >
                  <Copy className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleEditTemplate(template)}
                  title="编辑"
                >
                  <Edit className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleVersionManagement(template)}
                  title="版本管理"
                >
                  <GitBranch className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDeleteTemplate(template)}
                  title="删除"
                  className="text-red-600 hover:text-red-700 dark:text-red-400"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );

  if (showEditor) {
    return (
      <TemplateEditor
        template={editingTemplate || undefined}
        mode={editingTemplate ? 'edit' : 'create'}
        onSave={handleTemplateSaved}
        onCancel={() => setShowEditor(false)}
      />
    );
  }

  if (showVersionManager && versionManagingTemplate) {
    return (
      <TemplateVersionManager
        template={versionManagingTemplate}
        onVersionChange={handleVersionChange}
        onClose={() => {
          setShowVersionManager(false);
          setVersionManagingTemplate(null);
        }}
      />
    );
  }

  if (showTestingPanel && testingTemplate) {
    return (
      <TemplateTestingPanel
        template={testingTemplate}
        onClose={() => {
          setShowTestingPanel(false);
          setTestingTemplate(null);
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">提示词模板库</h1>
          <p className="text-gray-600 dark:text-gray-400">
            浏览和管理提示词模板，提升AI对话效率
          </p>
        </div>
        
        {showActions && (
          <Button onClick={handleCreateTemplate}>
            <Plus className="w-4 h-4 mr-2" />
            创建模板
          </Button>
        )}
      </div>

      {/* 搜索和筛选 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* 搜索框 */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4 dark:text-gray-500" />
                <Input
                  placeholder="搜索模板名称、描述或标签..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            {/* 筛选器 */}
            <div className="flex items-center gap-3">
              <select
                value={selectedCategory}
                onChange={(e) => handleFilterChange('category', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm dark:border-gray-600"
              >
                <option value="">所有分类</option>
                {categories.map(category => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </select>
              
              <select
                value={selectedVisibility}
                onChange={(e) => handleFilterChange('visibility', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm dark:border-gray-600"
              >
                <option value="">所有可见性</option>
                {visibilityOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              
              <select
                value={`${sortBy}_${sortOrder}`}
                onChange={(e) => {
                  const [field, order] = e.target.value.split('_');
                  setSortBy(field);
                  setSortOrder(order as 'asc' | 'desc');
                }}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm dark:border-gray-600"
              >
                <option value="updated_at_desc">最近更新</option>
                <option value="created_at_desc">最新创建</option>
                <option value="usage_count_desc">使用最多</option>
                <option value="rating_avg_desc">评分最高</option>
                <option value="title_asc">名称 A-Z</option>
              </select>
              
              {/* 视图切换 */}
              <div className="flex items-center border border-gray-300 rounded-md dark:border-gray-600">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                  className="rounded-r-none"
                >
                  <Grid className="w-4 h-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                  className="rounded-l-none"
                >
                  <List className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 标签页 */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as FilterTab)}>
        <TabsList>
          <TabsTrigger value="all">全部模板</TabsTrigger>
          <TabsTrigger value="my">我的模板</TabsTrigger>
          <TabsTrigger value="public">公开模板</TabsTrigger>
          <TabsTrigger value="featured">精选模板</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {/* 统计信息 */}
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              共找到 {totalCount} 个模板
            </div>
            {loading && (
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin dark:border-gray-600" />
                加载中...
              </div>
            )}
          </div>

          {/* 模板列表 */}
          {templates.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <div className="text-gray-400 mb-4 dark:text-gray-500">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">暂无模板</h3>
                  <p>
                    {activeTab === 'my' 
                      ? '您还没有创建任何模板，点击"创建模板"开始吧！'
                      : '没有找到符合条件的模板，试试调整搜索条件。'
                    }
                  </p>
                </div>
                {showActions && activeTab === 'my' && (
                  <Button onClick={handleCreateTemplate}>
                    <Plus className="w-4 h-4 mr-2" />
                    创建第一个模板
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            <>
              {viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                  {templates.map(template => (
                    <TemplateCard key={template.id} template={template} />
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  {templates.map(template => (
                    <TemplateListItem key={template.id} template={template} />
                  ))}
                </div>
              )}

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-8">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                  >
                    上一页
                  </Button>
                  
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const page = i + 1;
                      return (
                        <Button
                          key={page}
                          variant={currentPage === page ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setCurrentPage(page)}
                        >
                          {page}
                        </Button>
                      );
                    })}
                  </div>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                  >
                    下一页
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}