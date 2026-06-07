import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { 
  Share2, 
  Copy, 
  Eye, 
  Users, 
  Calendar, 
  BarChart3, 
  Settings, 
  Trash2,
  ExternalLink,
  Globe,
  Lock,
  Clock,
  Download
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

interface TemplateShare {
  id: number;
  template_id: number;
  share_type: 'PUBLIC' | 'TEAM' | 'PRIVATE';
  share_token: string;
  title: string;
  description?: string;
  status: 'ACTIVE' | 'EXPIRED' | 'DISABLED' | 'DELETED';
  access_count: number;
  max_access_count?: number;
  expires_at?: string;
  created_at: string;
  last_accessed_at?: string;
  allow_download: boolean;
  allow_copy: boolean;
  allow_comment: boolean;
}

interface ShareAnalytics {
  template_id: number;
  total_shares: number;
  active_shares: number;
  total_access: number;
  recent_access_trend: Record<string, number>;
  share_details: Array<{
    share_id: number;
    share_type: string;
    access_count: number;
    created_at: string;
    last_accessed_at?: string;
  }>;
}

interface TemplateShareManagerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template: {
    id: number;
    name: string;
    title: string;
  };
}

export function TemplateShareManager({
  open,
  onOpenChange,
  template
}: TemplateShareManagerProps) {
  const [shares, setShares] = useState<TemplateShare[]>([]);
  const [analytics, setAnalytics] = useState<ShareAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('shares');

  useEffect(() => {
    if (open) {
      loadShares();
      loadAnalytics();
    }
  }, [open, template.id]);

  const loadShares = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/template-sharing/my-shares?template_id=${template.id}`);
      if (response.ok) {
        const data = await response.json();
        setShares(data.shares || []);
      }
    } catch (error) {
      console.error('加载分享列表失败:', error);
      toast.error('加载分享列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadAnalytics = async () => {
    try {
      const response = await fetch(`/api/v1/template-sharing/templates/${template.id}/share-analytics`);
      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      }
    } catch (error) {
      console.error('加载分析数据失败:', error);
    }
  };

  const handleCopyShareUrl = async (shareId: number, shareToken: string) => {
    try {
      const response = await fetch(`/api/v1/template-sharing/shares/${shareId}/url`);
      if (response.ok) {
        const data = await response.json();
        await navigator.clipboard.writeText(data.share_url);
        toast.success('分享链接已复制到剪贴板');
      } else {
        toast.error('获取分享链接失败');
      }
    } catch (error) {
      console.error('复制分享链接失败:', error);
      toast.error('复制分享链接失败');
    }
  };

  const handleDeleteShare = async (shareId: number) => {
    try {
      const response = await fetch(`/api/v1/template-sharing/shares/${shareId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        toast.success('分享已删除');
        loadShares(); // 重新加载分享列表
      } else {
        toast.error('删除分享失败');
      }
    } catch (error) {
      console.error('删除分享失败:', error);
      toast.error('删除分享失败');
    }
  };

  const getShareTypeIcon = (type: string) => {
    switch (type) {
      case 'PUBLIC':
        return <Globe className="h-4 w-4" />;
      case 'TEAM':
        return <Users className="h-4 w-4" />;
      case 'PRIVATE':
        return <Lock className="h-4 w-4" />;
      default:
        return <Share2 className="h-4 w-4" />;
    }
  };

  const getShareTypeLabel = (type: string) => {
    switch (type) {
      case 'PUBLIC':
        return '公开分享';
      case 'TEAM':
        return '团队分享';
      case 'PRIVATE':
        return '私有分享';
      default:
        return '未知类型';
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'default';
      case 'EXPIRED':
        return 'secondary';
      case 'DISABLED':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return '活跃';
      case 'EXPIRED':
        return '已过期';
      case 'DISABLED':
        return '已禁用';
      case 'DELETED':
        return '已删除';
      default:
        return status;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5" />
            模板分享管理 - {template.title}
          </DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="shares">分享列表</TabsTrigger>
            <TabsTrigger value="analytics">分享统计</TabsTrigger>
          </TabsList>

          <TabsContent value="shares" className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">加载中...</div>
              </div>
            ) : shares.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-muted-foreground">暂无分享记录</div>
              </div>
            ) : (
              <div className="space-y-3">
                {shares.map((share) => (
                  <Card key={share.id}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getShareTypeIcon(share.share_type)}
                          <CardTitle className="text-base">{share.title}</CardTitle>
                          <Badge variant={getStatusBadgeVariant(share.status)}>
                            {getStatusLabel(share.status)}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleCopyShareUrl(share.id, share.share_token)}
                          >
                            <Copy className="h-4 w-4 mr-1" />
                            复制链接
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteShare(share.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-1" />
                            删除
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">分享类型</div>
                          <div className="flex items-center gap-1">
                            {getShareTypeIcon(share.share_type)}
                            {getShareTypeLabel(share.share_type)}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">访问次数</div>
                          <div className="flex items-center gap-1">
                            <Eye className="h-4 w-4" />
                            {share.access_count}
                            {share.max_access_count && ` / ${share.max_access_count}`}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">创建时间</div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            {format(new Date(share.created_at), 'yyyy-MM-dd')}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">最后访问</div>
                          <div className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            {share.last_accessed_at 
                              ? format(new Date(share.last_accessed_at), 'yyyy-MM-dd')
                              : '从未访问'
                            }
                          </div>
                        </div>
                      </div>
                      {share.description && (
                        <div className="mt-3 pt-3 border-t">
                          <div className="text-sm text-muted-foreground">{share.description}</div>
                        </div>
                      )}
                      <div className="mt-3 pt-3 border-t flex items-center gap-4 text-xs text-muted-foreground">
                        {share.allow_download && (
                          <div className="flex items-center gap-1">
                            <Download className="h-3 w-3" />
                            允许下载
                          </div>
                        )}
                        {share.allow_copy && (
                          <div className="flex items-center gap-1">
                            <Copy className="h-3 w-3" />
                            允许复制
                          </div>
                        )}
                        {share.expires_at && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            过期时间: {format(new Date(share.expires_at), 'yyyy-MM-dd HH:mm')}
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="analytics" className="space-y-4">
            {analytics ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">总分享数</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{analytics.total_shares}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">活跃分享</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{analytics.active_shares}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">总访问量</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{analytics.total_access}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">平均访问量</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {analytics.total_shares > 0 
                          ? Math.round(analytics.total_access / analytics.total_shares)
                          : 0
                        }
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5" />
                      访问趋势
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm text-muted-foreground">
                      最近30天的访问统计
                    </div>
                    <div className="mt-4 space-y-2">
                      {Object.entries(analytics.recent_access_trend)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .slice(-7) // 显示最近7天
                        .map(([date, count]) => (
                          <div key={date} className="flex items-center justify-between">
                            <span className="text-sm">{date}</span>
                            <span className="text-sm font-medium">{count} 次访问</span>
                          </div>
                        ))
                      }
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="flex items-center justify-center py-8">
                <div className="text-muted-foreground">加载统计数据中...</div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
     