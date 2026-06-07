// @ts-nocheck
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { 
  Share2, 
  Globe, 
  Heart, 
  Star, 
  Settings, 
  Plus,
  Search,
  TrendingUp
} from 'lucide-react';
import { TemplateShareDialog } from './TemplateShareDialog';
import { TemplateShareManager } from './TemplateShareManager';
import { TemplateShareBrowser } from './TemplateShareBrowser';

interface Template {
  id: number;
  name: string;
  title: string;
  description?: string;
  category?: string;
  tags?: string[];
}

interface TemplateShareIntegrationProps {
  template?: Template;
  mode?: 'share' | 'browse' | 'manage';
  onTemplateSelect?: (template: any) => void;
}

export function TemplateShareIntegration({ 
  template, 
  mode = 'browse',
  onTemplateSelect 
}: TemplateShareIntegrationProps) {
  const [activeTab, setActiveTab] = useState(mode);
  const [showShareDialog, setShowShareDialog] = useState(false);
  const [showManagerDialog, setShowManagerDialog] = useState(false);

  const handleShare = (shareData: any) => {
    console.log('鍒嗕韩鍒涘缓鎴愬姛:', shareData);
    setShowShareDialog(false);
  };

  const handleTemplateSelect = (selectedTemplate: any) => {
    onTemplateSelect?.(selectedTemplate);
  };

  return (
    <div className="w-full">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="browse" className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            娴忚妯℃澘
          </TabsTrigger>
          <TabsTrigger value="favorites" className="flex items-center gap-2">
            <Heart className="h-4 w-4" />
            鎴戠殑鏀惰棌
          </TabsTrigger>
          <TabsTrigger value="trending" className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            鐑棬鎺ㄨ崘
          </TabsTrigger>
        </TabsList>

        <TabsContent value="browse" className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">公开模板库</h2>
              <p className="text-muted-foreground">
                发现并使用社区分享的优质模板
              </p>
            </div>
            {template && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowManagerDialog(true)}
                >
                  <Settings className="h-4 w-4 mr-2" />
                  绠＄悊鍒嗕韩
                </Button>
                <Button onClick={() => setShowShareDialog(true)}>
                  <Share2 className="h-4 w-4 mr-2" />
                  鍒嗕韩妯℃澘
                </Button>
              </div>
            )}
          </div>

          <TemplateShareBrowser onSelectTemplate={handleTemplateSelect} />
        </TabsContent>

        <TabsContent value="favorites" className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">鎴戠殑鏀惰棌</h2>
              <p className="text-muted-foreground">
                鎮ㄦ敹钘忕殑妯℃澘鍜屽垎浜?
              </p>
            </div>
            <Button variant="outline">
              <Search className="h-4 w-4 mr-2" />
              鎼滅储鏀惰棌
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Heart className="h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground text-center">
                  鏆傛棤鏀惰棌鐨勬ā鏉?
                </p>
                <p className="text-xs text-muted-foreground text-center mt-1">
                  娴忚鍏紑妯℃澘骞舵敹钘忔偍鍠滄鐨勫唴瀹?
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="trending" className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">鐑棬鎺ㄨ崘</h2>
              <p className="text-muted-foreground">
                鏈€鍙楁杩庡拰楂樿瘎鍒嗙殑妯℃澘
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-yellow-500" />
                  鏈懆鐑棬
                </CardTitle>
                <CardDescription>
                  鏈懆浣跨敤娆℃暟鏈€澶氱殑妯℃澘
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                      <div>
                        <div className="font-medium text-sm">绀轰緥妯℃澘 {i + 1}</div>
                        <div className="text-xs text-muted-foreground">浠ｇ爜缂栫▼</div>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {100 - i * 20} 娆′娇鐢?
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-500" />
                  璇勫垎鏈€楂?
                </CardTitle>
                <CardDescription>
                  鐢ㄦ埛璇勫垎鏈€楂樼殑浼樿川妯℃澘
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                      <div>
                        <div className="font-medium text-sm">楂樿川閲忔ā鏉?{i + 1}</div>
                        <div className="text-xs text-muted-foreground">鏂囨。鍐欎綔</div>
                      </div>
                      <div className="flex items-center gap-1 text-xs">
                        <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                        {(4.8 - i * 0.1).toFixed(1)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* 鍒嗕韩瀵硅瘽妗?*/}
      {template && (
        <>
          <TemplateShareDialog
            open={showShareDialog}
            onOpenChange={setShowShareDialog}
            template={template}
            onShare={handleShare}
          />

          <TemplateShareManager
            open={showManagerDialog}
            onOpenChange={setShowManagerDialog}
            template={template}
          />
        </>
      )}
    </div>
  );
}
