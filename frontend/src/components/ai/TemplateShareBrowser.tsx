import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { 
  Search, 
  Star, 
  Eye, 
  Download, 
  Globe, 
  Users, 
  Lock,
  Calendar,
  User,
  Filter
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

interface PublicTemplate {
  id: number;
  title: string;
  description: string;
  category: string;
  tags: string[];
  rating_avg: number;
  rating_count: number;
  usage_count: number;
  created_at: string;
  author?: {
    name: string;
    avatar?: string;
  };
}

interface TemplateShareBrowserProps {
  onSelectTemplate?: (template: PublicTemplate) => void;
}

export function TemplateShareBrowser({ onSelectTemplate }: TemplateShareBrowserProps) {
  const [templates, setTemplates] = useState<PublicTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [categories] = useState([
    '通用对话',
    '代码编程', 
    '测试相关',
    '文档写作',
    '数据分析',
    '创意设计',
    '学习教育',
    '项目管理'
  ]);

  useEffect(() => {
    loadPublicTemplates();
  }, [searchQuery, selectedCategory, sortBy, sortOrder, page]);

  const loadPublicTemplates = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        size: '12',
        sort_by: sortBy,
        sort_order: sortOrder
      });

      if (searchQuery) {
        params.append('query', searchQuery);
      }
      if (selectedCategory) {
        params.append('category', selectedCategory);
      }

      const response = await fetch(`/api/v1/template-sharing/public/templates?${params}`);
      if (response.ok) {
        const data = await response.json();
        setTemplates(data.templates || []);
        setTotal(data.total || 0);
      }
    } catch (error) {
      console.error('加载公开模板失败:', error);
      toast.error('加载公开模板失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setPage(1);
  };

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category);
    setPage(1);
  };

  const handleSortChange = (newSortBy: string) => {
    setSortBy(newSortBy);
    setPage(1);
  };

  const handleUseTemplate = async (template: PublicTemplate) => {
    try {
      // 这里可以实现模板使用逻辑，比如复制到用户的模板库
      onSelectTemplate?.(template);
      toast.success('模板已添加到您的模板库');
    } catch (error) {
      console.error('使用模板失败:', error);
      toast.error('使用模板失败');
    }
  };

  const renderStars = (rating: number) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push(<Star key={i} className="h-3 w-3 fill-yellow-400 text-yellow-400" />);
      } else if (i === fullStars && hasHalfStar) {
        stars.push(<Star key={i} className="h-3 w-3 fill-yellow-400/50 text-yellow-400" />);
      } else {
        stars.push(<Star key={i} className="h-3 w-3 text-gray-300" />);
      }
    }
    return stars;
  };

  return (
    <div className="space-y-6">
      {/* 搜索和筛选 */}
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索模板..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={selectedCategory} onValueChange={handleCategoryChange}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="选择分类" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">全部分类</SelectItem>
              {categories.map((category) => (
                <SelectItem key={category} value={category}>
                  {category}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={handleSortChange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="created_at">最新</SelectItem>
              <SelectItem value="rating">评分</SelectItem>
              <SelectItem value="usage">使用量</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div>找到 {total} 个公开模板</div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            <span>按{sortBy === 'created_at' ? '创建时间' : sortBy === 'rating' ? '评分' : '使用量'}排序</span>
          </div>
        </div>
      </div>

      {/* 模板列表 */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-muted rounded w-3/4"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-3 bg-muted rounded"></div>
                  <div className="h-3 bg-muted rounded w-2/3"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-12">
          <Globe className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">暂无公开模板</h3>
          <p className="text-muted-foreground">
            {searchQuery || selectedCategory ? '尝试调整搜索条件' : '还没有用户分享公开模板'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((template) => (
            <Card key={template.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-base line-clamp-2">{template.title}</CardTitle>
                    <CardDescription className="line-clamp-2 mt-1">
                      {template.description}
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="ml-2">
                    {template.category}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 标签 */}
                {template.tags && template.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {template.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                    {template.tags.length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{template.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                )}

                {/* 统计信息 */}
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1">
                      <div className="flex items-center">
                        {renderStars(template.rating_avg || 0)}
                      </div>
                      <span className="text-xs">
                        {template.rating_avg ? template.rating_avg.toFixed(1) : '0.0'}
                      </span>
                      <span className="text-xs">({template.rating_count || 0})</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      <span className="text-xs">{template.usage_count || 0}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-xs">
                    <Calendar className="h-3 w-3" />
                    {format(new Date(template.created_at), 'MM-dd')}
                  </div>
                </div>

                {/* 作者信息 */}
                {template.author && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <User className="h-3 w-3" />
                    <span className="text-xs">{template.author.name}</span>
                  </div>
                )}

                {/* 操作按钮 */}
                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleUseTemplate(template)}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    使用模板
                  </Button>
                  <Button variant="outline" size="sm">
                    <Eye className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 分页 */}
      {total > 12 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            上一页
          </Button>
          <span className="text-sm text-muted-foreground">
            第 {page} 页，共 {Math.ceil(total / 12)} 页
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= Math.ceil(total / 12)}
            onClick={() => setPage(page + 1)}
          >
            下一页
          </Button>
        </div>
      )}
    </div>
  );
}