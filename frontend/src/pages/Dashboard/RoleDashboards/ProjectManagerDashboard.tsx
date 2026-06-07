import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  Briefcase, 
  Users, 
  Target, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle,
  Clock,
  DollarSign,
  Calendar,
  BarChart3,
  Activity,
  FileText
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart, GaugeChart } from '@/components/dashboard/Widgets/Charts';

interface ProjectMetrics {
  totalProjects: number;
  activeProjects: number;
  completedProjects: number;
  delayedProjects: number;
  teamMembers: number;
  budgetUtilization: number;
  overallProgress: number;
  riskLevel: number;
  projectHealth: Array<{
    name: string;
    health: number;
    progress: number;
  }>;
  budgetTrends: Array<{
    month: string;
    planned: number;
    actual: number;
  }>;
}

interface Project {
  id: number;
  name: string;
  status: 'active' | 'completed' | 'delayed' | 'planning';
  progress: number;
  health: 'healthy' | 'warning' | 'critical';
  budget: {
    planned: number;
    used: number;
  };
  team: number;
  deadline: string;
  manager: string;
}

interface TeamMember {
  id: number;
  name: string;
  role: string;
  workload: number;
  availability: 'available' | 'busy' | 'unavailable';
  projects: number;
}

interface Risk {
  id: number;
  project: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  probability: 'high' | 'medium' | 'low';
  status: 'open' | 'mitigated' | 'closed';
}

const ProjectManagerDashboard: React.FC = () => {
  const { user } = useAuth();
  const {
    dashboardConfig,
    widgets,
    loading,
    error,
    saveDashboardLayout,
    resetDashboard,
    addWidget,
    removeWidget,
    updateWidget
  } = useDashboard('PROJECT_MANAGER');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [projectMetrics, setProjectMetrics] = useState<ProjectMetrics>({
    totalProjects: 0,
    activeProjects: 0,
    completedProjects: 0,
    delayedProjects: 0,
    teamMembers: 0,
    budgetUtilization: 0,
    overallProgress: 0,
    riskLevel: 0,
    projectHealth: [],
    budgetTrends: []
  });

  const [projects, setProjects] = useState<Project[]>([]);
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['project_update', 'team_update', 'budget_update', 'risk_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['project_update', 'team_update', 'budget_update', 'risk_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockMetrics: ProjectMetrics = {
      totalProjects: 12,
      activeProjects: 8,
      completedProjects: 3,
      delayedProjects: 1,
      teamMembers: 45,
      budgetUtilization: 73.5,
      overallProgress: 68.2,
      riskLevel: 25.8,
      projectHealth: [
        { name: '电商平台', health: 92, progress: 85 },
        { name: '移动应用', health: 78, progress: 65 },
        { name: 'AI系统', health: 65, progress: 45 },
        { name: '数据平台', health: 88, progress: 72 }
      ],
      budgetTrends: [
        { month: '1月', planned: 500000, actual: 480000 },
        { month: '2月', planned: 520000, actual: 510000 },
        { month: '3月', planned: 480000, actual: 495000 },
        { month: '4月', planned: 550000, actual: 535000 },
        { month: '5月', planned: 600000, actual: 580000 }
      ]
    };

    setProjectMetrics(mockMetrics);

    setProjects([
      { id: 1, name: '电商平台开发', status: 'active', progress: 85, health: 'healthy', budget: { planned: 1200000, used: 980000 }, team: 12, deadline: '2024-03-15', manager: '张三' },
      { id: 2, name: '移动应用重构', status: 'active', progress: 65, health: 'warning', budget: { planned: 800000, used: 520000 }, team: 8, deadline: '2024-02-28', manager: '李四' },
      { id: 3, name: 'AI智能系统', status: 'active', progress: 45, health: 'critical', budget: { planned: 1500000, used: 675000 }, team: 15, deadline: '2024-04-30', manager: '王五' },
      { id: 4, name: '数据分析平台', status: 'active', progress: 72, health: 'healthy', budget: { planned: 900000, used: 648000 }, team: 10, deadline: '2024-03-20', manager: '赵六' },
      { id: 5, name: '用户管理系统', status: 'completed', progress: 100, health: 'healthy', budget: { planned: 600000, used: 580000 }, team: 6, deadline: '2024-01-15', manager: '钱七' }
    ]);

    setTeamMembers([
      { id: 1, name: '张三', role: '项目经理', workload: 85, availability: 'busy', projects: 2 },
      { id: 2, name: '李四', role: '前端开发', workload: 70, availability: 'available', projects: 1 },
      { id: 3, name: '王五', role: '后端开发', workload: 90, availability: 'busy', projects: 3 },
      { id: 4, name: '赵六', role: 'UI设计师', workload: 60, availability: 'available', projects: 2 },
      { id: 5, name: '钱七', role: '测试工程师', workload: 95, availability: 'unavailable', projects: 2 },
      { id: 6, name: '孙八', role: '产品经理', workload: 75, availability: 'available', projects: 1 }
    ]);

    setRisks([
      { id: 1, project: '电商平台开发', description: '第三方API集成延期', impact: 'medium', probability: 'high', status: 'open' },
      { id: 2, project: '移动应用重构', description: '关键开发人员离职', impact: 'high', probability: 'medium', status: 'open' },
      { id: 3, project: 'AI智能系统', description: '技术方案复杂度超预期', impact: 'high', probability: 'high', status: 'open' },
      { id: 4, project: '数据分析平台', description: '数据源接入困难', impact: 'medium', probability: 'medium', status: 'mitigated' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-emerald-300 to-teal-400 rounded-lg h-32"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-gray-300 rounded-lg h-24"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <Card className="w-full max-w-md">
          <CardContent className="p-6 text-center">
            <div className="text-red-500 mb-4">
              <AlertTriangle className="h-12 w-12 mx-auto" />
            </div>
            <h3 className="text-lg font-semibold mb-2">加载失败</h3>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={() => window.location.reload()}>
              重新加载
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">项目管理仪表板</h1>
            <p className="text-emerald-100">
              欢迎回来，{user?.real_name || user?.username} | 项目管理员
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{projectMetrics.activeProjects}</div>
            <div className="text-emerald-100">活跃项目</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">项目总数</p>
                <p className="text-2xl font-bold text-emerald-600">
                  {projectMetrics.totalProjects}
                </p>
              </div>
              <Briefcase className="h-8 w-8 text-emerald-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-emerald-600 border-emerald-600">
                完成: {projectMetrics.completedProjects}
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">团队成员</p>
                <p className="text-2xl font-bold text-blue-600">
                  {projectMetrics.teamMembers}
                </p>
              </div>
              <Users className="h-8 w-8 text-blue-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600">
                跨项目协作
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">预算使用率</p>
                <p className="text-2xl font-bold text-orange-600">
                  {projectMetrics.budgetUtilization}%
                </p>
              </div>
              <DollarSign className="h-8 w-8 text-orange-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                预算内
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">整体进度</p>
                <p className="text-2xl font-bold text-purple-600">
                  {projectMetrics.overallProgress}%
                </p>
              </div>
              <Target className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                按计划进行
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Project Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>项目健康度</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {projectMetrics.projectHealth.map((project, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{project.name}</span>
                    <span className="text-gray-500">健康度: {project.health}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${
                        project.health >= 80 ? 'bg-green-500' :
                        project.health >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${project.health}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>进度: {project.progress}%</span>
                    <span className={
                      project.health >= 80 ? 'text-green-600' :
                      project.health >= 60 ? 'text-yellow-600' : 'text-red-600'
                    }>
                      {project.health >= 80 ? '健康' :
                       project.health >= 60 ? '注意' : '风险'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Budget Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>预算趋势</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={projectMetrics.budgetTrends}
              config={{
                xAxisKey: 'month',
                yAxisKeys: ['planned', 'actual'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>
      </div>

      {/* Projects and Team Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Projects */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Briefcase className="h-5 w-5" />
              <span>活跃项目</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {projects.filter(p => p.status === 'active').map((project) => (
                <div key={project.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{project.name}</h4>
                    <Badge 
                      variant={
                        project.health === 'healthy' ? 'default' :
                        project.health === 'warning' ? 'secondary' : 'destructive'
                      }
                    >
                      {project.health === 'healthy' ? '健康' :
                       project.health === 'warning' ? '警告' : '风险'}
                    </Badge>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                    <div 
                      className="bg-emerald-600 h-2 rounded-full" 
                      style={{ width: `${project.progress}%` }}
                    ></div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">进度: </span>
                      <span>{project.progress}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">团队: </span>
                      <span>{project.team}人</span>
                    </div>
                    <div>
                      <span className="text-gray-500">预算: </span>
                      <span>{((project.budget.used / project.budget.planned) * 100).toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">截止: </span>
                      <span>{project.deadline}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Team Members */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Users className="h-5 w-5" />
              <span>团队成员</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {teamMembers.map((member) => (
                <div key={member.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      member.availability === 'available' ? 'bg-green-500' :
                      member.availability === 'busy' ? 'bg-yellow-500' : 'bg-red-500'
                    }`}></div>
                    <div>
                      <p className="font-medium text-sm">{member.name}</p>
                      <p className="text-xs text-gray-500">{member.role}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">工作负载: {member.workload}%</p>
                    <p className="text-xs text-gray-500">项目: {member.projects}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Risks */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5" />
            <span>项目风险</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {risks.map((risk) => (
              <div key={risk.id} className={`p-4 rounded-lg border-l-4 ${
                risk.impact === 'high' && risk.probability === 'high' 
                  ? 'bg-red-50 border-red-500' 
                  : (risk.impact === 'high' || risk.probability === 'high')
                  ? 'bg-yellow-50 border-yellow-500'
                  : 'bg-blue-50 border-blue-500'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium">{risk.description}</p>
                  <div className="flex items-center space-x-2">
                    <Badge 
                      variant={
                        risk.impact === 'high' ? 'destructive' : 
                        risk.impact === 'medium' ? 'secondary' : 'outline'
                      }
                      className="text-xs"
                    >
                      影响: {risk.impact === 'high' ? '高' : risk.impact === 'medium' ? '中' : '低'}
                    </Badge>
                    <Badge 
                      variant={
                        risk.probability === 'high' ? 'destructive' : 
                        risk.probability === 'medium' ? 'secondary' : 'outline'
                      }
                      className="text-xs"
                    >
                      概率: {risk.probability === 'high' ? '高' : risk.probability === 'medium' ? '中' : '低'}
                    </Badge>
                  </div>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">项目: {risk.project}</span>
                  <Badge 
                    variant={
                      risk.status === 'open' ? 'destructive' :
                      risk.status === 'mitigated' ? 'secondary' : 'default'
                    }
                    className="text-xs"
                  >
                    {risk.status === 'open' ? '开放' :
                     risk.status === 'mitigated' ? '已缓解' : '已关闭'}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Custom Dashboard Grid */}
      <DashboardGrid
        widgets={widgets}
        editMode={false}
        onLayoutChange={() => {}}
        onRemoveWidget={removeWidget}
        onUpdateWidget={updateWidget}
        realtimeData={realtimeData}
      />
    </div>
  );
};

export default ProjectManagerDashboard;