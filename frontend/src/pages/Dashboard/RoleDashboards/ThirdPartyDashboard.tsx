import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  Users, 
  FileText, 
  MessageCircle, 
  Calendar, 
  Clock, 
  CheckCircle,
  AlertTriangle,
  Download,
  Upload,
  Eye,
  Lock,
  Shield,
  Activity
} from 'lucide-react';
import { useAuth } from '@/stores/auth';
import { useDashboard } from '@/hooks/dashboard/useDashboard';
import { useRealtime } from '@/hooks/dashboard/useRealtime';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import { LineChart, BarChart, PieChart } from '@/components/dashboard/Widgets/Charts';

interface CollaborationMetrics {
  totalProjects: number;
  activeProjects: number;
  completedTasks: number;
  pendingTasks: number;
  slaCompliance: number;
  responseTime: number;
  satisfactionScore: number;
  deliveryRate: number;
  communicationFrequency: Array<{
    date: string;
    messages: number;
    meetings: number;
  }>;
  taskProgress: Array<{
    project: string;
    completed: number;
    total: number;
  }>;
}

interface ProjectAccess {
  id: number;
  name: string;
  role: string;
  status: 'active' | 'completed' | 'paused';
  progress: number;
  deadline: string;
  lastActivity: string;
}

interface Task {
  id: number;
  title: string;
  project: string;
  priority: 'high' | 'medium' | 'low';
  status: 'todo' | 'in_progress' | 'review' | 'completed';
  deadline: string;
  assignedBy: string;
}

interface Communication {
  id: number;
  type: 'message' | 'meeting' | 'document' | 'feedback';
  title: string;
  from: string;
  timestamp: string;
  status: 'unread' | 'read' | 'replied';
  priority: 'high' | 'medium' | 'low';
}

interface AccessRequest {
  id: number;
  type: 'document' | 'data' | 'system';
  resource: string;
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
  requestDate: string;
  approver?: string;
}

const ThirdPartyDashboard: React.FC = () => {
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
  } = useDashboard('THIRD_PARTY');

  const {
    isConnected,
    realtimeData,
    subscribe,
    unsubscribe
  } = useRealtime();

  const [collaborationMetrics, setCollaborationMetrics] = useState<CollaborationMetrics>({
    totalProjects: 0,
    activeProjects: 0,
    completedTasks: 0,
    pendingTasks: 0,
    slaCompliance: 0,
    responseTime: 0,
    satisfactionScore: 0,
    deliveryRate: 0,
    communicationFrequency: [],
    taskProgress: []
  });

  const [projectAccess, setProjectAccess] = useState<ProjectAccess[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [communications, setCommunications] = useState<Communication[]>([]);
  const [accessRequests, setAccessRequests] = useState<AccessRequest[]>([]);

  useEffect(() => {
    if (isConnected) {
      subscribe(['project_update', 'task_update', 'communication_update', 'access_update']);
    }
    
    return () => {
      if (isConnected) {
        unsubscribe(['project_update', 'task_update', 'communication_update', 'access_update']);
      }
    };
  }, [isConnected, subscribe, unsubscribe]);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const mockMetrics: CollaborationMetrics = {
      totalProjects: 5,
      activeProjects: 3,
      completedTasks: 28,
      pendingTasks: 12,
      slaCompliance: 96.5,
      responseTime: 2.3,
      satisfactionScore: 4.6,
      deliveryRate: 94.2,
      communicationFrequency: [
        { date: '周一', messages: 15, meetings: 2 },
        { date: '周二', messages: 12, meetings: 1 },
        { date: '周三', messages: 18, meetings: 3 },
        { date: '周四', messages: 14, meetings: 2 },
        { date: '周五', messages: 20, meetings: 4 },
        { date: '周六', messages: 5, meetings: 0 },
        { date: '周日', messages: 3, meetings: 0 }
      ],
      taskProgress: [
        { project: '项目A', completed: 8, total: 10 },
        { project: '项目B', completed: 12, total: 15 },
        { project: '项目C', completed: 5, total: 8 }
      ]
    };

    setCollaborationMetrics(mockMetrics);

    setProjectAccess([
      { id: 1, name: '电商平台开发', role: '外部顾问', status: 'active', progress: 75, deadline: '2024-02-15', lastActivity: '2小时前' },
      { id: 2, name: '移动应用测试', role: '测试合作伙伴', status: 'active', progress: 60, deadline: '2024-01-30', lastActivity: '1天前' },
      { id: 3, name: '数据分析项目', role: '数据顾问', status: 'active', progress: 40, deadline: '2024-03-01', lastActivity: '3小时前' },
      { id: 4, name: '安全审计', role: '安全专家', status: 'completed', progress: 100, deadline: '2024-01-10', lastActivity: '1周前' },
      { id: 5, name: '性能优化', role: '技术顾问', status: 'paused', progress: 25, deadline: '2024-02-28', lastActivity: '5天前' }
    ]);

    setTasks([
      { id: 1, title: '完成用户体验评估报告', project: '电商平台开发', priority: 'high', status: 'in_progress', deadline: '今天', assignedBy: '项目经理' },
      { id: 2, title: '提交测试用例设计', project: '移动应用测试', priority: 'high', status: 'review', deadline: '明天', assignedBy: '测试主管' },
      { id: 3, title: '数据清洗和预处理', project: '数据分析项目', priority: 'medium', status: 'todo', deadline: '本周五', assignedBy: '数据负责人' },
      { id: 4, title: '安全漏洞修复建议', project: '安全审计', priority: 'high', status: 'completed', deadline: '上周', assignedBy: '安全经理' },
      { id: 5, title: '性能基准测试', project: '性能优化', priority: 'low', status: 'todo', deadline: '下周', assignedBy: '技术负责人' }
    ]);

    setCommunications([
      { id: 1, type: 'message', title: '项目进度确认', from: '项目经理', timestamp: '30分钟前', status: 'unread', priority: 'high' },
      { id: 2, type: 'meeting', title: '周例会邀请', from: '团队协调员', timestamp: '2小时前', status: 'read', priority: 'medium' },
      { id: 3, type: 'document', title: '需求文档更新', from: '产品经理', timestamp: '4小时前', status: 'read', priority: 'medium' },
      { id: 4, type: 'feedback', title: '客户反馈收集', from: '客户代表', timestamp: '1天前', status: 'replied', priority: 'high' },
      { id: 5, type: 'message', title: '技术方案讨论', from: '技术负责人', timestamp: '2天前', status: 'read', priority: 'low' }
    ]);

    setAccessRequests([
      { id: 1, type: 'document', resource: '系统架构文档', reason: '完成技术评估', status: 'pending', requestDate: '2024-01-15' },
      { id: 2, type: 'data', resource: '用户行为数据', reason: '数据分析需要', status: 'approved', requestDate: '2024-01-14', approver: '数据保护官' },
      { id: 3, type: 'system', resource: '测试环境访问', reason: '执行集成测试', status: 'approved', requestDate: '2024-01-13', approver: '运维经理' },
      { id: 4, type: 'document', resource: '财务报表', reason: '成本分析', status: 'rejected', requestDate: '2024-01-12', approver: '财务经理' }
    ]);
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gradient-to-r from-teal-300 to-cyan-400 rounded-lg h-32"></div>
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
      <div className="bg-gradient-to-r from-teal-600 to-cyan-600 rounded-lg p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">第三方协作仪表板</h1>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{collaborationMetrics.activeProjects}</div>
            <div className="text-teal-100">活跃项目</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">SLA合规率</p>
                <p className="text-2xl font-bold text-green-600">
                  {collaborationMetrics.slaCompliance}%
                </p>
              </div>
              <Shield className="h-8 w-8 text-green-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-green-600 border-green-600">
                优秀
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">响应时间</p>
                <p className="text-2xl font-bold text-blue-600">
                  {collaborationMetrics.responseTime}h
                </p>
              </div>
              <Clock className="h-8 w-8 text-blue-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-blue-600 border-blue-600">
                快速响应
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">满意度评分</p>
                <p className="text-2xl font-bold text-purple-600">
                  {collaborationMetrics.satisfactionScore}/5
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-purple-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-purple-600 border-purple-600">
                高满意度
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">交付率</p>
                <p className="text-2xl font-bold text-orange-600">
                  {collaborationMetrics.deliveryRate}%
                </p>
              </div>
              <Activity className="h-8 w-8 text-orange-600" />
            </div>
            <div className="mt-2">
              <Badge variant="outline" className="text-orange-600 border-orange-600">
                按时交付
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Communication Frequency */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageCircle className="h-5 w-5" />
              <span>沟通频率</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <BarChart
              data={collaborationMetrics.communicationFrequency}
              config={{
                xAxisKey: 'date',
                yAxisKeys: ['messages', 'meetings'],
                showValues: true,
                showGrid: true,
                showLegend: true,
                animation: true
              }}
            />
          </CardContent>
        </Card>

        {/* Task Progress */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>任务进度</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {collaborationMetrics.taskProgress.map((project, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{project.project}</span>
                    <span className="text-gray-500">{project.completed}/{project.total}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-teal-600 h-2 rounded-full" 
                      style={{ width: `${(project.completed / project.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Projects and Tasks Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Project Access */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Users className="h-5 w-5" />
              <span>项目访问权限</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {projectAccess.map((project) => (
                <div key={project.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{project.name}</h4>
                    <Badge 
                      variant={
                        project.status === 'active' ? 'default' :
                        project.status === 'completed' ? 'secondary' : 'outline'
                      }
                    >
                      {project.status === 'active' ? '进行中' :
                       project.status === 'completed' ? '已完成' : '暂停'}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">角色: {project.role}</p>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                    <div 
                      className="bg-teal-600 h-2 rounded-full" 
                      style={{ width: `${project.progress}%` }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-sm text-gray-500">
                    <span>进度: {project.progress}%</span>
                    <span>截止: {project.deadline}</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">最后活动: {project.lastActivity}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* My Tasks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5" />
              <span>我的任务</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {tasks.map((task) => (
                <div key={task.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className={`w-3 h-3 rounded-full ${
                    task.status === 'completed' ? 'bg-green-500' :
                    task.status === 'in_progress' ? 'bg-blue-500' :
                    task.status === 'review' ? 'bg-yellow-500' : 'bg-gray-400'
                  }`}></div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{task.title}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {task.project}
                      </Badge>
                      <Badge 
                        variant={task.priority === 'high' ? 'destructive' : task.priority === 'medium' ? 'secondary' : 'outline'}
                        className="text-xs"
                      >
                        {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
                      </Badge>
                      <span className="text-xs text-gray-500">截止: {task.deadline}</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">分配人: {task.assignedBy}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Communications and Access Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Communications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageCircle className="h-5 w-5" />
              <span>沟通消息</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {communications.map((comm) => (
                <div key={comm.id} className={`p-3 border rounded-lg ${
                  comm.status === 'unread' ? 'bg-blue-50 border-blue-200' : ''
                }`}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-2">
                      {comm.type === 'message' && <MessageCircle className="h-4 w-4 text-blue-500" />}
                      {comm.type === 'meeting' && <Calendar className="h-4 w-4 text-purple-500" />}
                      {comm.type === 'document' && <FileText className="h-4 w-4 text-green-500" />}
                      {comm.type === 'feedback' && <Eye className="h-4 w-4 text-orange-500" />}
                      <p className="font-medium text-sm">{comm.title}</p>
                    </div>
                    <Badge 
                      variant={comm.priority === 'high' ? 'destructive' : comm.priority === 'medium' ? 'secondary' : 'outline'}
                      className="text-xs"
                    >
                      {comm.priority === 'high' ? '高' : comm.priority === 'medium' ? '中' : '低'}
                    </Badge>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>来自: {comm.from}</span>
                    <span>{comm.timestamp}</span>
                  </div>
                  <div className="mt-1">
                    <Badge 
                      variant={comm.status === 'unread' ? 'default' : 'outline'}
                      className="text-xs"
                    >
                      {comm.status === 'unread' ? '未读' : comm.status === 'read' ? '已读' : '已回复'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Access Requests */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Lock className="h-5 w-5" />
              <span>访问申请</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {accessRequests.map((request) => (
                <div key={request.id} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {request.type === 'document' && <FileText className="h-4 w-4 text-blue-500" />}
                      {request.type === 'data' && <Download className="h-4 w-4 text-green-500" />}
                      {request.type === 'system' && <Lock className="h-4 w-4 text-purple-500" />}
                      <p className="font-medium text-sm">{request.resource}</p>
                    </div>
                    <Badge 
                      variant={
                        request.status === 'approved' ? 'default' :
                        request.status === 'pending' ? 'secondary' : 'destructive'
                      }
                      className="text-xs"
                    >
                      {request.status === 'approved' ? '已批准' :
                       request.status === 'pending' ? '待审批' : '已拒绝'}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-600 mb-1">申请原因: {request.reason}</p>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>申请日期: {request.requestDate}</span>
                    {request.approver && <span>审批人: {request.approver}</span>}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

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

export default ThirdPartyDashboard;
