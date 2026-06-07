import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BarChart3 } from 'lucide-react';

import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { PerformanceAnalysis } from '@/components/projects/PerformanceAnalysis';
import { ProjectBenchmarking } from '@/components/projects/ProjectBenchmarking';
import { TeamPerformanceDashboard } from '@/components/projects/TeamPerformanceDashboard';

interface StatisticsPageProps {
  className?: string;
}

export const Statistics: React.FC<StatisticsPageProps> = ({ className }) => {
  const { projectId = '0' } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const numericProjectId = Number(projectId);

  return (
    <div className={`space-y-6 p-6 ${className ?? ''}`}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <BarChart3 className="h-6 w-6" />
            项目统计
          </h1>
          <p className="text-sm text-muted-foreground">项目 #{projectId} 的进度、绩效和对标分析。</p>
        </div>
        <Button type="button" variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回
        </Button>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-lg">统计分析</CardTitle></CardHeader>
        <CardContent>
          <Tabs defaultValue="performance">
            <TabsList>
              <TabsTrigger value="performance">项目绩效</TabsTrigger>
              <TabsTrigger value="team">团队绩效</TabsTrigger>
              <TabsTrigger value="benchmark">项目对标</TabsTrigger>
            </TabsList>
            <TabsContent value="performance"><PerformanceAnalysis projectId={numericProjectId} /></TabsContent>
            <TabsContent value="team"><TeamPerformanceDashboard projectId={numericProjectId} /></TabsContent>
            <TabsContent value="benchmark"><ProjectBenchmarking projectId={numericProjectId} /></TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default Statistics;
